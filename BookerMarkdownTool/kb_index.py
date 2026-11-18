# -*- coding: utf-8 -*-
"""kb-index 子命令：扫描 Markdown 语料，切块后用 jieba 建倒排 + BM25，用 sentence-transformers
建本地向量库，落盘到可增量更新的索引目录。"""

from __future__ import annotations

import argparse
import datetime
import fnmatch
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .kb_core import (BM25Index, ChunkSplitter, DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE,
                      DEFAULT_EXCLUDES, DEFAULT_MIN_CHUNK_LEN, IndexStore, STEncoder, Tokenizer,
                      VectorStore)
from .kb_models import ChunkMeta, FileEntry, IndexManifest
from .util import md5, safe_rmdir


def _resolve_emb_model(args) -> Optional[str]:
    if getattr(args, "no_emb", False):
        return None
    emb = getattr(args, "emb", None)
    if emb:
        return emb
    print("错误：未指定 embedding 模型。请用全局参数 --emb <模型名或本地路径>，"
          "或加 --no-emb 仅建 BM25 索引。", file=sys.stderr)
    return None


def _map_device(device: str) -> Optional[str]:
    return None if device == "auto" else device


def _excluded(name: str, excludes: List[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in excludes)


def _chunked(seq: Sequence, size: int) -> Iterable:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


class KbIndexOrchestrator:
    def __init__(self, args):
        self.args = args
        self.index_dir = Path(getattr(args, "index_dir", ".kb-index"))
        self.chunk_size = int(getattr(args, "chunk_size", DEFAULT_CHUNK_SIZE))
        self.chunk_overlap = int(getattr(args, "chunk_overlap", DEFAULT_CHUNK_OVERLAP))
        self.min_chunk_len = int(getattr(args, "min_chunk_len", DEFAULT_MIN_CHUNK_LEN))
        self.keep_code = bool(getattr(args, "keep_code", False))
        self.excludes = list(DEFAULT_EXCLUDES) + list(getattr(args, "exclude", None) or [])
        self.tokenizer_mode = getattr(args, "tokenizer", "search")
        self.stopwords_path = getattr(args, "stopwords", None)
        self.no_stopwords = bool(getattr(args, "no_stopwords", False))
        self.user_dicts = list(getattr(args, "user_dict", None) or [])
        self.emb_batch_size = int(getattr(args, "emb_batch_size", 64))
        self.device = _map_device(getattr(args, "device", "auto"))
        self.workers = int(getattr(args, "workers", os.cpu_count() or 2))
        self.incremental = bool(getattr(args, "incremental", True))
        self.rebuild = bool(getattr(args, "rebuild", False))
        self.prune = bool(getattr(args, "prune", True))
        self.stats = bool(getattr(args, "stats", False))
        self.verbose = bool(getattr(args, "verbose", False))

    # ── 公开流程 ──────────────────────────────────────────────────────

    def run(self) -> None:
        args = self.args
        if self.rebuild:
            safe_rmdir(self.index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        stopwords = set() if self.no_stopwords else Tokenizer.load_stopwords(self.stopwords_path)
        tokenizer = Tokenizer(mode=self.tokenizer_mode, stopwords=stopwords,
                              user_dicts=self.user_dicts)
        splitter = ChunkSplitter(chunk_size=self.chunk_size,
                                 chunk_overlap=self.chunk_overlap,
                                 min_chunk_len=self.min_chunk_len,
                                 keep_code=self.keep_code,
                                 excludes=self.excludes)

        store = IndexStore(self.index_dir)
        manifest = None
        if (not self.rebuild) and self.incremental and store.exists():
            try:
                manifest = store.load_manifest()
            except Exception as exc:  # 旧索引损坏：走全量重建
                print(f"警告：读取旧索引失败：{exc}，将全量重建。", file=sys.stderr)
                manifest = None
        if manifest is not None:
            if int(manifest.format_version) != 1:
                print(f"错误：索引格式版本 {manifest.format_version} 不受支持，请用 --rebuild 重建。",
                      file=sys.stderr)
                return
            if (manifest.tokenizer_version
                    and manifest.tokenizer_version != tokenizer.version):
                print(f"错误：分词器版本与索引不一致（索引 {manifest.tokenizer_version}，"
                      f"当前 {tokenizer.version}），请用 --rebuild 重建。", file=sys.stderr)
                return

        # ── 扫描源文件 ────────────────────────────────────────────────
        srcs: List[str] = list(getattr(args, "src", None)
                               or getattr(args, "SRC", [])
                               or [])
        files = self._scan_files(srcs, splitter.excludes)
        file_infos: Dict[str, dict] = {}

        def read_one(fp_rel: Tuple[Path, str]) -> Tuple[str, dict]:
            fp, rel = fp_rel
            data = fp.read_bytes()
            text = data.decode("utf8", errors="replace")
            return rel, {
                "abs": fp,
                "md5": md5(text),
                "mtime": fp.stat().st_mtime,
                "text": text,
            }

        if self.workers > 1 and files:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                for rel, info in pool.map(read_one, files):
                    file_infos[rel] = info
        else:
            for fp_rel in files:
                rel, info = read_one(fp_rel)
                file_infos[rel] = info

        old_files = manifest.files if manifest else {}
        changed = [rel for rel, info in file_infos.items()
                   if old_files.get(rel) is None or old_files[rel].md5 != info["md5"]]
        deleted = [rel for rel in old_files if rel not in file_infos]

        if not changed and not deleted and manifest is not None:
            print("0 文件更新，索引无变化。")
            if self.stats or self.verbose:
                self._print_stats(store, [], 0.0, None)
            return

        # ── 切块 + 分词（仅变更/新增文件） ────────────────────────────
        old_chunks = store.load_chunks() if manifest else []
        old_by_path: Dict[str, List[ChunkMeta]] = {}
        for c in old_chunks:
            old_by_path.setdefault(c.path, []).append(c)

        new_specs: List[Tuple[str, dict, List[str]]] = []
        for rel in sorted(file_infos):
            entry = old_files.get(rel)
            if entry is not None and entry.md5 == file_infos[rel]["md5"]:
                continue
            for ch in splitter.split(file_infos[rel]["text"], rel):
                tokens = tokenizer.tokenize(ch["text"])
                new_specs.append((rel, ch, tokens))

        # ── 合并旧块与新块，重新分配连续 chunk_id ─────────────────────
        final: List[Tuple[ChunkMeta, Optional[List[str]]]] = []
        old_id_of_new: Dict[int, Optional[int]] = {}
        next_id = 0
        for rel in sorted(file_infos):
            entry = old_files.get(rel)
            info = file_infos[rel]
            if entry is not None and entry.md5 == info["md5"]:
                for c in old_by_path.get(rel, []):
                    nc = ChunkMeta(chunk_id=next_id, path=c.path,
                                   heading_path=c.heading_path,
                                   start_line=c.start_line, end_line=c.end_line,
                                   text=c.text, n_tokens=c.n_tokens, md5=c.md5)
                    final.append((nc, None))
                    old_id_of_new[next_id] = c.chunk_id
                    next_id += 1
            else:
                for spec_rel, ch, tokens in [s for s in new_specs if s[0] == rel]:
                    cm = ChunkMeta(chunk_id=next_id, path=rel,
                                   heading_path=ch["heading_path"],
                                   start_line=ch["start_line"], end_line=ch["end_line"],
                                   text=ch["text"], n_tokens=len(tokens),
                                   md5=md5(ch["text"]))
                    final.append((cm, tokens))
                    old_id_of_new[next_id] = None
                    next_id += 1

        file_entries: Dict[str, FileEntry] = {}
        for rel in sorted(file_infos):
            ids = [cm.chunk_id for cm, _ in final if cm.path == rel]
            file_entries[rel] = FileEntry(md5=file_infos[rel]["md5"],
                                          mtime=file_infos[rel]["mtime"],
                                          chunk_ids=ids)

        # ── BM25 倒排 ─────────────────────────────────────────────────
        bm25 = BM25Index()
        for cm, tokens in final:
            toks = tokens if tokens is not None else tokenizer.tokenize(cm.text)
            bm25.add_document(cm.chunk_id, toks)
        bm25.finish()

        # ── 向量（可选） ──────────────────────────────────────────────
        emb_model = _resolve_emb_model(args)
        if emb_model is None and not getattr(args, "no_emb", False):
            # _resolve_emb_model 已把错误打印到 stderr
            raise SystemExit(2)
        vectors: Optional[np.ndarray] = None
        encode_sec = 0.0
        if emb_model is not None:
            t0 = time.time()
            old_vectors = store.load_vectors() if manifest else None
            encoder = STEncoder(emb_model, device=self.device)
            reuse = (manifest is not None
                     and manifest.emb_model == emb_model
                     and old_vectors is not None
                     and len(old_vectors) == len(old_chunks))
            rows: List[Optional[np.ndarray]] = [None] * len(final)
            to_encode: List[int] = []
            if reuse:
                for i, (cm, _) in enumerate(final):
                    oid = old_id_of_new[i]
                    if oid is not None:
                        rows[i] = old_vectors[oid]
                    else:
                        to_encode.append(i)
            else:
                to_encode = list(range(len(final)))
            for batch in _chunked(to_encode, self.emb_batch_size):
                texts = [final[i][0].text for i in batch]
                vecs = encoder.encode(texts, batch_size=self.emb_batch_size,
                                      show_progress=self.verbose)
                for i, v in zip(batch, vecs):
                    rows[i] = v
            vectors = np.stack([r for r in rows if r is not None]).astype(np.float32)
            encode_sec = time.time() - t0

        # ── 落盘 ──────────────────────────────────────────────────────
        final_chunks = [cm for cm, _ in final]
        store.save_chunks(final_chunks)
        store.save_inverted(bm25.postings)
        store.save_bm25_stats({
            "N": bm25.N,
            "avgdl": bm25.avgdl,
            "df": bm25.df,
            "postings_offsets": {t: i for i, t in enumerate(sorted(bm25.postings))},
        })
        if vectors is not None:
            store.save_vectors(vectors)
        store.save_file_hashes(file_entries)

        src_root = os.path.abspath(srcs[0]) if srcs else str(self.index_dir)
        manifest = IndexManifest(
            format_version=1,
            tokenizer_version=tokenizer.version,
            emb_model=emb_model,
            emb_dim=int(vectors.shape[1]) if vectors is not None else None,
            created_at=datetime.datetime.now().isoformat(),
            src_root=src_root,
            n_chunks=len(final_chunks),
            files=file_entries,
        )
        store.save_manifest(manifest)

        if self.stats or self.verbose:
            self._print_stats(store, final_chunks, encode_sec, vectors)

    # ── 私有工具 ─────────────────────────────────────────────────────

    @staticmethod
    def _scan_files(srcs: List[str], excludes: List[str]) -> List[Tuple[Path, str]]:
        found: List[Tuple[Path, str]] = []
        for src in srcs:
            p = Path(src)
            if p.is_file():
                if p.suffix.lower() == ".md":
                    found.append((p, p.name))
            elif p.is_dir():
                for root, dirs, fnames in os.walk(p):
                    root_p = Path(root)
                    dirs[:] = [d for d in dirs if not _excluded(d, excludes)]
                    for fn in fnames:
                        if fn.lower().endswith(".md"):
                            fp = root_p / fn
                            found.append((fp, fp.relative_to(p).as_posix()))
        return found

    @staticmethod
    def _print_stats(store: IndexStore, chunks: Sequence[ChunkMeta],
                     encode_sec: float, vectors: Optional[np.ndarray]) -> None:
        disk = sum(f.stat().st_size for f in store.dir.rglob("*") if f.is_file()) \
            if store.dir.is_dir() else 0
        n_terms = 0
        try:
            n_terms = len(store.load_inverted())
        except Exception:
            pass
        print(f"索引目录：{store.dir}")
        print(f"分块数：{len(chunks)}  词项数：{n_terms}")
        if vectors is not None:
            print(f"向量：{vectors.shape[0]}x{vectors.shape[1]}  "
                  f"device=auto  编码耗时：{encode_sec:.2f}s")
        print(f"磁盘占用：{disk} 字节")


def kb_index_hdl(args) -> None:
    KbIndexOrchestrator(args).run()


def reg_subparser(subparsers) -> None:
    p = subparsers.add_parser(
        "kb-index",
        help="构建知识库倒排与向量索引",
        description="扫描 Markdown 语料，切块后用 jieba 建倒排 + BM25，"
                    "用 sentence-transformers 编码建本地向量库，落盘到可增量更新的索引目录。",
    )
    p.add_argument("SRC", nargs="+", help="Markdown 文件或目录（可多个）")
    p.add_argument("--index-dir", default=".kb-index", help="索引目录（默认 ./.kb-index）")
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                   help="分块最大字符数（默认 800）")
    p.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP,
                   help="分块滑动重叠字符数（默认 100）")
    p.add_argument("--min-chunk-len", type=int, default=DEFAULT_MIN_CHUNK_LEN,
                   help="小于此长度的分块丢弃（默认 30）")
    p.add_argument("--keep-code", action="store_true", help="保留纯代码块（默认丢弃）")
    p.add_argument("--exclude", action="append", default=None,
                   help="额外排除 glob（可重复，默认排除 .git/ node_modules/ index/）")
    p.add_argument("--tokenizer", choices=["search", "cut"], default="search",
                   help="jieba 分词模式：search 精细模式 / cut 精确模式（默认 search）")
    p.add_argument("--stopwords", help="自定义停用词表路径（默认内置 kb_stopwords_zh.txt）")
    p.add_argument("--no-stopwords", action="store_true", help="不使用停用词表")
    p.add_argument("--user-dict", action="append", default=None, help="jieba 用户词典（可重复）")
    p.add_argument("--emb", default=argparse.SUPPRESS,
                   help="Embedding 模型名或本地路径（全局参数，置于子命令前后均可）")
    p.add_argument("--no-emb", action="store_true", help="只建倒排 + BM25，不向量化")
    p.add_argument("--emb-batch-size", type=int, default=64, help="向量编码批大小（默认 64）")
    p.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto",
                   help="向量编码设备（默认 auto）")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 2,
                   help="读文件/切块并行数（默认 cpu_count）")
    p.add_argument("--incremental", action="store_true", default=True,
                   help="启用增量更新（按 md5 跳过未变文件，默认开启）")
    p.add_argument("--rebuild", action="store_true", help="清空索引目录后全量重建")
    p.add_argument("--prune", action="store_true", default=True,
                   help="删除已消失文件的分块（默认开启）")
    p.add_argument("--no-prune", action="store_false", dest="prune",
                   help="不删除已消失文件的分块")
    p.add_argument("--stats", action="store_true", help="输出索引统计信息")
    p.add_argument("-v", "--verbose", action="store_true", help="详细日志")
    p.set_defaults(func=kb_index_hdl)
