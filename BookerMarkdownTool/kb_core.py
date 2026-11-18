# -*- coding: utf-8 -*-
"""kb-index / kb-query 无 CLI 依赖的核心组件：分词、倒排/BM25、切块、向量、混合检索、索引读写。"""

from __future__ import annotations

import fnmatch
import gzip
import hashlib
import json
import math
import os
import pickle
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

import jieba
import numpy as np

from .kb_models import ChunkMeta, FileEntry, IndexManifest
from .util import asset, json_dump_model, md5

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_MIN_CHUNK_LEN = 30
DEFAULT_EXCLUDES = (".git", "node_modules", "index")
SENTENCE_END = "。！？；\n"


def _is_all_punct(tok: str) -> bool:
    if not tok:
        return False
    return all(unicodedata.category(ch).startswith("P") or ch.isspace() for ch in tok)


class Tokenizer:
    """jieba 分词器。进程内单例复用（首次载入词典约 0.3-0.8 s），不要跨进程传 jieba 对象。"""

    def __init__(self, mode: str = "search",
                 stopwords: Optional[Iterable[str]] = None,
                 user_dicts: Optional[Sequence[str]] = None):
        jieba.setLogLevel(20)  # 屏蔽 "Building prefix dict" 日志
        for p in user_dicts or []:
            jieba.load_userdict(p)
        self.mode = mode
        self.stopwords = set(stopwords or [])
        self.user_dicts = list(user_dicts or [])

    @classmethod
    def load_stopwords(cls, path: Optional[str] = None) -> set:
        if path is None:
            path = asset("kb_stopwords_zh.txt")
        stopwords: set = set()
        if path and os.path.isfile(path):
            with open(path, encoding="utf8") as f:
                for line in f:
                    w = line.strip()
                    if w and not w.startswith("#"):
                        stopwords.add(w)
        return stopwords

    @property
    def version(self) -> str:
        return f"jieba-{jieba.__version__}-{self.mode}"

    def tokenize(self, text: str) -> List[str]:
        if self.mode == "search":
            toks = jieba.lcut_for_search(text)
        else:
            toks = jieba.lcut(text)
        res: List[str] = []
        for t in toks:
            t = t.strip()
            if not t:
                continue
            if _is_all_punct(t):
                continue
            if self.stopwords and t in self.stopwords:
                continue
            res.append(t.lower())
        return res


class BM25Index:
    """倒排索引 + BM25 打分（k1=1.5, b=0.75 可配）。

    IDF(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
    score(q,d) = Sum_{t in q n d} IDF(t) * tf(t,d)*(k1+1) / (tf(t,d) + k1*(1-b+b*dl/avgdl))
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.postings: Dict[str, List[List[int]]] = {}   # term -> [[chunk_id, tf], ...]
        self.df: Dict[str, int] = {}
        self.dl: Dict[int, int] = {}                     # chunk_id -> doc length
        self.N = 0
        self.avgdl = 0.0

    def add_document(self, chunk_id: int, tokens: Sequence[str]) -> None:
        self.dl[chunk_id] = len(tokens)
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        for t, tf in freq.items():
            self.postings.setdefault(t, []).append([chunk_id, tf])
            self.df[t] = self.df.get(t, 0) + 1

    def finish(self) -> None:
        self.N = len(self.dl)
        self.avgdl = (sum(self.dl.values()) / self.N) if self.N else 0.0

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5))

    def topk(self, query_tokens: Sequence[str], topk: int) -> List[Tuple[int, float]]:
        if self.N == 0 or topk <= 0:
            return []
        scores: Dict[int, float] = {}
        avgdl = max(self.avgdl, 1.0)
        for t in dict.fromkeys(query_tokens):  # 去重，保序
            idf = self.idf(t)
            for chunk_id, tf in self.postings.get(t, []):
                dl = self.dl.get(chunk_id, int(avgdl))
                denom = tf + self.k1 * (1 - self.b + self.b * dl / avgdl)
                scores[chunk_id] = scores.get(chunk_id, 0.0) + \
                    idf * tf * (self.k1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:topk]


# ── 索引目录读写 ────────────────────────────────────────────────────────


class IndexStore:
    """索引目录的持久化访问。默认目录 ./ .kb-index/ 。"""

    def __init__(self, index_dir: str | Path):
        self.dir = Path(index_dir)

    # -- manifest --
    def manifest_path(self) -> Path:
        return self.dir / "manifest.json"

    def exists(self) -> bool:
        return self.manifest_path().is_file()

    def load_manifest(self) -> IndexManifest:
        return IndexManifest.model_validate_json(self.manifest_path().read_text(encoding="utf8"))

    def save_manifest(self, manifest: IndexManifest) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path().write_text(
            manifest.model_dump_json(indent=2, ensure_ascii=False), encoding="utf8")

    # -- chunks --
    def load_chunks(self) -> List[ChunkMeta]:
        path = self.dir / "chunks.jsonl"
        chunks: List[ChunkMeta] = []
        with open(path, encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(ChunkMeta.model_validate_json(line))
        return chunks

    def save_chunks(self, chunks: Sequence[ChunkMeta]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "chunks.jsonl", "w", encoding="utf8") as f:
            for c in chunks:
                f.write(c.model_dump_json(ensure_ascii=False) + "\n")

    # -- inverted index --
    def load_inverted(self) -> Dict[str, List[List[int]]]:
        gz = self.dir / "inverted.jsonl.gz"
        pkl = self.dir / "inverted.pkl"
        if pkl.is_file() and (not gz.is_file()
                              or pkl.stat().st_mtime >= gz.stat().st_mtime):
            with open(pkl, "rb") as f:
                return pickle.load(f)
        postings: Dict[str, List[List[int]]] = {}
        with gzip.open(gz, "rt", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                postings[obj["term"]] = [[int(c), int(tf)] for c, tf in obj["postings"]]
        return postings

    def save_inverted(self, postings: Dict[str, List[List[int]]]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(self.dir / "inverted.jsonl.gz", "wt", encoding="utf8") as f:
            for term in sorted(postings):
                f.write(json_dump_model({"term": term, "postings": postings[term]}) + "\n")
        with open(self.dir / "inverted.pkl", "wb") as f:
            pickle.dump(postings, f)

    # -- bm25 stats --
    def load_bm25_stats(self) -> dict:
        path = self.dir / "bm25_stats.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf8"))

    def save_bm25_stats(self, stats: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "bm25_stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf8")

    # -- vectors --
    def load_vectors(self) -> Optional[np.ndarray]:
        path = self.dir / "vectors.npy"
        if not path.is_file():
            return None
        return np.load(path)

    def save_vectors(self, vectors: np.ndarray) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        np.save(self.dir / "vectors.npy", vectors)

    # -- file hashes --
    def load_file_hashes(self) -> Dict[str, FileEntry]:
        path = self.dir / "file_hashes.json"
        if not path.is_file():
            return {}
        raw = json.loads(path.read_text(encoding="utf8"))
        return {k: FileEntry(**v) for k, v in raw.items()}

    def save_file_hashes(self, files: Dict[str, FileEntry]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "file_hashes.json").write_text(
            json_dump_model({k: v.model_dump() for k, v in files.items()}),
            encoding="utf8",
        )


# ── 切块 ──────────────────────────────────────────────────────────────


class ChunkSplitter:
    RE_FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})\S*$")
    RE_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE,
                 chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
                 min_chunk_len: int = DEFAULT_MIN_CHUNK_LEN,
                 keep_code: bool = False,
                 excludes: Optional[Sequence[str]] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_len = min_chunk_len
        self.keep_code = keep_code
        self.excludes = list(DEFAULT_EXCLUDES) + list(excludes or [])

    def excluded(self, rel_path: str) -> bool:
        parts = Path(rel_path).parts
        for pat in self.excludes:
            for part in parts:
                if fnmatch.fnmatch(part, pat):
                    return True
        return False

    def split(self, text: str, path: str) -> List[dict]:
        """把单个 md 文本切成分块，返回 {heading_path, start_line, end_line, text}。"""
        lines = text.split("\n")
        sections: List[Tuple[List[str], List[Tuple[int, int, str, bool]]]] = []
        cur_path: List[str] = []
        cur_blocks: List[Tuple[int, int, str, bool]] = []

        def flush() -> None:
            nonlocal cur_blocks
            if cur_blocks:
                sections.append((list(cur_path), cur_blocks))
                cur_blocks = []

        i, n = 0, len(lines)
        in_code = False
        while i < n:
            ln = i + 1
            l = lines[i]
            if self.RE_FENCE.match(l):
                if in_code:
                    in_code = False
                    i += 1
                    continue
                j = i
                while j + 1 < n and not self.RE_FENCE.match(lines[j + 1]):
                    j += 1
                if j + 1 < n:
                    j += 1  # 包含结束栅栏
                if self.keep_code:
                    cur_blocks.append((ln, j + 1, "\n".join(lines[i:j + 1]), True))
                i = j + 1
                continue
            if not in_code:
                m = self.RE_HEADING.match(l)
                if m:
                    flush()
                    level = len(m.group(1))
                    cur_path = cur_path[:level - 1] + [m.group(2).strip()]
                    i += 1
                    continue
                if l.strip():
                    cur_blocks.append((ln, ln, l, False))
            else:
                if self.keep_code:
                    cur_blocks.append((ln, ln, l, True))
            i += 1
        flush()

        chunks: List[dict] = []
        for heading_path, blocks in sections:
            chunks.extend(self._pack_section(heading_path, blocks))
        return chunks

    # -- 内部：段内按句子打包 --
    def _sentence_units(self, text: str) -> List[Tuple[str, int, int]]:
        units: List[Tuple[str, int, int]] = []
        cur: List[str] = []
        start = 0
        for i, ch in enumerate(text):
            if not cur:
                start = i
            cur.append(ch)
            if ch in SENTENCE_END:
                units.append(("".join(cur), start, i + 1))
                cur = []
        if cur:
            t = "".join(cur)
            units.append((t, start, len(text)))
        return [(t, s, e) for t, s, e in units if t.strip()]

    def _group_units(self, units: Sequence[Tuple[str, int, int]]) -> List[List[Tuple[str, int, int]]]:
        groups: List[List[Tuple[str, int, int]]] = []
        cur: List[Tuple[str, int, int]] = []
        cur_len = 0
        for u in units:
            t = u[0]
            add = len(t)
            if cur and cur_len + add > self.chunk_size:
                groups.append(cur)
                cur = [u]
                cur_len = add
            else:
                cur.append(u)
                cur_len += add
            if cur_len > self.chunk_size and len(cur) == 1:
                # 单句过长：按 chunk_size 硬切
                t, s, e = u
                pieces = []
                for i in range(0, len(t), self.chunk_size):
                    piece = t[i:i + self.chunk_size]
                    pieces.append((piece, s + i, s + i + len(piece)))
                groups.extend([[p] for p in pieces])
                cur = []
                cur_len = 0
        if cur:
            groups.append(cur)
        return groups

    def _span_to_lines(self, cstart: int, cend: int,
                       offsets: Sequence[Tuple[int, int, int, int]]) -> Tuple[int, int]:
        s_line = e_line = None
        for cs, ce, s, e in offsets:
            if s_line is None and cs <= cstart < ce:
                s_line = s
            if cs < cend <= ce:
                e_line = e
        if s_line is None:
            s_line = offsets[0][2]
        if e_line is None:
            e_line = offsets[-1][3]
        return s_line, e_line

    def _pack_section(self, heading_path: List[str],
                      blocks: Sequence[Tuple[int, int, str, bool]]) -> List[dict]:
        if not blocks:
            return []
        offsets: List[Tuple[int, int, int, int]] = []  # (char_start, char_end, start_line, end_line)
        pos = 0
        for s, e, t, _is_code in blocks:
            offsets.append((pos, pos + len(t), s, e))
            pos += len(t) + 1
        text = "\n".join(t for _, _, t, _ in blocks)
        groups = self._group_units(self._sentence_units(text))
        res: List[dict] = []
        for gi, group in enumerate(groups):
            cstart = group[0][1]
            cend = group[-1][2]
            chunk_text = "".join(u[0] for u in group)
            if gi > 0 and self.chunk_overlap > 0:
                prev_text = "".join(u[0] for u in groups[gi - 1])
                chunk_text = prev_text[-self.chunk_overlap:] + chunk_text
            if len(chunk_text) < self.min_chunk_len:
                continue
            s_line, e_line = self._span_to_lines(cstart, cend, offsets)
            res.append({
                "heading_path": list(heading_path),
                "start_line": s_line,
                "end_line": e_line,
                "text": chunk_text,
            })
        return res


# ── 向量层 ─────────────────────────────────────────────────────────────


class Encoder(Protocol):
    name: str
    dim: int

    def encode(self, texts: List[str], batch_size: int = 64,
               show_progress: bool = False) -> np.ndarray:
        ...


class STEncoder:
    """基于 sentence-transformers 的编码器（sentence_transformers 惰性导入）。"""

    def __init__(self, model_name_or_path: str, device: Optional[str] = None):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name_or_path, device=device)
        self.name = model_name_or_path
        self.dim = self.model.get_sentence_embedding_dimension()
        try:
            import torch  # CPU 场景建议限制线程，避免与读文件线程争抢
            if device in (None, "cpu"):
                torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
        except ImportError:
            pass

    def encode(self, texts: List[str], batch_size: int = 64,
               show_progress: bool = False) -> np.ndarray:
        return self.model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=show_progress)


class FakeEncoder:
    """测试用确定性编码器：md5 hash -> 固定维度归一化向量。"""

    def __init__(self, dim: int = 16):
        self.name = "fake"
        self.dim = dim

    def encode(self, texts: List[str], batch_size: int = 64,
               show_progress: bool = False) -> np.ndarray:
        vecs = []
        for t in texts:
            h = hashlib.md5(t.encode("utf8")).digest()
            v = np.frombuffer(h, dtype=np.uint8)[:self.dim].astype(np.float32)
            norm = float(np.linalg.norm(v))
            if norm > 0:
                v = v / norm
            vecs.append(v)
        return np.stack(vecs)


class VectorStore:
    """向量库：rows L2 归一化后，内积即余弦。直接矩阵乘，不引入索引结构。"""

    def __init__(self, vectors: Optional[np.ndarray]):
        self.vectors = vectors  # float32 [N, D]

    def search(self, q_vec: np.ndarray, topk: int) -> List[Tuple[int, float]]:
        if self.vectors is None or len(self.vectors) == 0 or topk <= 0:
            return []
        sims = self.vectors @ q_vec
        n = min(topk, len(sims))
        idx = np.argpartition(-sims, n - 1)[:n]
        idx = idx[np.argsort(-sims[idx])]
        return [(int(i), float(sims[i])) for i in idx]


# ── 混合检索 ───────────────────────────────────────────────────────────


class HybridRetriever:
    def __init__(self, bm25: BM25Index, vector_store: Optional[VectorStore],
                 chunks: Sequence[ChunkMeta], mode: str = "hybrid",
                 fuse: str = "rrf", rrf_k: int = 60, alpha: float = 0.5,
                 candidate_n: int = 0):
        self.bm25 = bm25
        self.vector_store = vector_store
        self.chunks_by_id = {c.chunk_id: c for c in chunks}
        self.mode = mode
        self.fuse = fuse
        self.rrf_k = rrf_k
        self.alpha = alpha
        self.candidate_n = candidate_n

    def retrieve(self, query: str, tokenizer: Tokenizer, topk: int,
                 encoder: Optional[Encoder] = None,
                 snippet_len: int = 200) -> List[QueryHit]:
        from .kb_models import QueryHit

        q_tokens = tokenizer.tokenize(query)
        cand = self.candidate_n or max(topk * 5, 50)

        bm25_ranked: List[Tuple[int, float]] = []
        vec_ranked: List[Tuple[int, float]] = []
        if self.mode in ("bm25", "hybrid"):
            bm25_ranked = self.bm25.topk(q_tokens, cand)
        if self.mode in ("vec", "hybrid"):
            if self.vector_store is None:
                raise RuntimeError("该索引未包含向量层（建索引时使用了 --no-emb）。"
                                   "请用 --mode bm25，或带 --emb 重建索引。")
            if encoder is None:
                raise RuntimeError("向量检索需要编码器")
            q_vec = encoder.encode([query])[0]
            vec_ranked = self.vector_store.search(q_vec, cand)

        fused, ranks_map, raw_map = self._fuse(bm25_ranked, vec_ranked)

        hits: List[QueryHit] = []
        for cid, score in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:topk]:
            chunk = self.chunks_by_id.get(cid)
            if chunk is None:
                continue
            hits.append(QueryHit(
                chunk_id=cid,
                path=chunk.path,
                heading_path=chunk.heading_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                snippet=make_snippet(chunk.text, q_tokens, snippet_len),
                bm25_score=raw_map["bm25"].get(cid),
                vec_score=raw_map["vec"].get(cid),
                fused_score=float(score),
                ranks={k: v for k, v in ranks_map[cid].items() if v is not None},
            ))
        return hits

    def _fuse(self, bm25_ranked: List[Tuple[int, float]],
              vec_ranked: List[Tuple[int, float]]):
        bm25_map = dict(bm25_ranked)
        vec_map = dict(vec_ranked)
        ranks_b = {cid: i + 1 for i, (cid, _) in enumerate(bm25_ranked)}
        ranks_v = {cid: i + 1 for i, (cid, _) in enumerate(vec_ranked)}
        cids = set(ranks_b) | set(ranks_v)
        fused: Dict[int, float] = {}
        ranks_map: Dict[int, Dict[str, Optional[int]]] = {}
        for cid in cids:
            rb = ranks_b.get(cid)
            rv = ranks_v.get(cid)
            ranks_map[cid] = {"bm25": rb, "vec": rv}
            total = 0.0
            if rb is not None:
                total += 1.0 / (self.rrf_k + rb)
            if rv is not None:
                total += 1.0 / (self.rrf_k + rv)
            fused[cid] = total
        if self.fuse == "weight":
            b_vals = list(bm25_map.values())
            v_vals = list(vec_map.values())
            b_min, b_max = (min(b_vals), max(b_vals)) if b_vals else (0.0, 0.0)
            v_min, v_max = (min(v_vals), max(v_vals)) if v_vals else (0.0, 0.0)

            def norm(v: float, mn: float, mx: float) -> float:
                return 0.0 if mx == mn else (v - mn) / (mx - mn)

            for cid in cids:
                nb = norm(bm25_map[cid], b_min, b_max) if cid in bm25_map else 0.0
                nv = norm(vec_map[cid], v_min, v_max) if cid in vec_map else 0.0
                fused[cid] = self.alpha * nb + (1 - self.alpha) * nv
        return fused, ranks_map, {"bm25": bm25_map, "vec": vec_map}


def make_snippet(text: str, tokens: Sequence[str], length: int) -> str:
    text = text.replace("\n", " ")
    idx = -1
    for t in tokens:
        j = text.find(t)
        if j >= 0:
            idx = j
            break
    if idx < 0:
        s = text[:length]
    else:
        s = text[max(0, idx - length // 2): min(len(text), idx + length // 2)]
    if len(s) > length:
        s = s[:length]
    return s
