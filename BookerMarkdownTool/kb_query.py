# -*- coding: utf-8 -*-
"""kb-query 子命令：加载已建索引，执行 BM25 / 向量 / RRF 混合检索，支持人类可读与 --json 输出。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np

from . import util
from .kb_core import BM25Index, Encoder, HybridRetriever, IndexStore, STEncoder, Tokenizer, VectorStore
from .kb_index_pmt import KB_ANSWER_PMT
from .kb_models import QueryHit, QueryResult
from .openai import OpenAIClient


class KbQueryOrchestrator:
    def __init__(self, args):
        self.args = args
        self.index_dir = Path(getattr(args, "index_dir", ".kb-index"))
        self.tokenizer_mode = getattr(args, "tokenizer", "search")
        self.stopwords_path = getattr(args, "stopwords", None)
        self.no_stopwords = bool(getattr(args, "no_stopwords", False))
        self.user_dicts = list(getattr(args, "user_dict", None) or [])
        self.device = None if getattr(args, "device", "auto") == "auto" else getattr(args, "device")
        self.emb_batch_size = int(getattr(args, "emb_batch_size", 64))

    # ── 公开流程 ──────────────────────────────────────────────────────

    def run(self) -> QueryResult:
        args = self.args
        query = (getattr(args, "query", None) or getattr(args, "QUERY", None) or "")
        mode = getattr(args, "mode", "hybrid")

        result = QueryResult(query=query, mode=mode, emb_model=None, hits=[])

        store = IndexStore(self.index_dir)
        if not store.exists():
            print(f"未找到索引：{self.index_dir}。请先运行 kb-index。", file=sys.stderr)
            self._output(result, args)
            return result

        manifest = store.load_manifest()
        if int(manifest.format_version) != 1:
            print(f"错误：索引格式版本 {manifest.format_version} 不受支持，请用 --rebuild 重建。",
                  file=sys.stderr)
            self._output(result, args)
            return result

        stopwords = set() if self.no_stopwords else Tokenizer.load_stopwords(self.stopwords_path)
        tokenizer = Tokenizer(mode=self.tokenizer_mode, stopwords=stopwords,
                              user_dicts=self.user_dicts)
        if manifest.tokenizer_version and manifest.tokenizer_version != tokenizer.version:
            print(f"错误：分词器版本与索引不一致（索引 {manifest.tokenizer_version}，"
                  f"当前 {tokenizer.version}），请重建索引。", file=sys.stderr)
            self._output(result, args)
            return result

        chunks = store.load_chunks()
        bm25 = self._load_bm25(store, chunks)

        need_vec = mode in ("vec", "hybrid")
        vector_store: Optional[VectorStore] = None
        encoder: Optional[Encoder] = None
        emb_model_used: Optional[str] = manifest.emb_model

        if need_vec:
            if manifest.emb_model is None:
                print("该索引未包含向量层（建索引时使用了 --no-emb）。"
                      "请用 --mode bm25，或带 --emb 重建索引。", file=sys.stderr)
                self._output(result, args)
                return result
            emb = getattr(args, "emb", None)
            if emb is None:
                emb = getattr(args, "emb", None)  # 全局 --emb 的默认值已写入 args
            if emb != manifest.emb_model:
                print(f"索引使用的 embedding 模型为 {manifest.emb_model}，当前 --emb 为 {emb}；"
                      f"请改用相同模型或 --rebuild 重建索引。", file=sys.stderr)
                self._output(result, args)
                return result
            vec_path = self.index_dir / "vectors.npy"
            if not vec_path.is_file():
                print("该索引未包含向量层（建索引时使用了 --no-emb）。"
                      "请用 --mode bm25，或带 --emb 重建索引。", file=sys.stderr)
                self._output(result, args)
                return result
            vectors = np.load(vec_path)
            encoder = STEncoder(emb, device=self.device)
            vector_store = VectorStore(vectors)
            emb_model_used = emb

        retriever = HybridRetriever(
            bm25, vector_store, chunks,
            mode=mode,
            fuse=getattr(args, "fuse", "rrf"),
            rrf_k=int(getattr(args, "rrf_k", 60)),
            alpha=float(getattr(args, "alpha", 0.5)),
            candidate_n=int(getattr(args, "candidate_n", 0)),
        )
        hits = retriever.retrieve(
            query, tokenizer,
            topk=int(getattr(args, "topk", 10)),
            encoder=encoder,
            snippet_len=int(getattr(args, "snippet_len", 200)),
        )
        result.hits = hits
        result.emb_model = emb_model_used

        if getattr(args, "answer", False) and hits:
            result.answer = self._answer(args, query, hits)

        self._output(result, args)
        return result

    # ── 私有工具 ─────────────────────────────────────────────────────

    def _load_bm25(self, store: IndexStore, chunks: List) -> BM25Index:
        postings = store.load_inverted()
        stats = store.load_bm25_stats()
        bm25 = BM25Index()
        bm25.postings = {t: [[int(c), int(tf)] for c, tf in plist]
                         for t, plist in postings.items()}
        bm25.df = {t: int(n) for t, n in stats.get("df", {}).items()}
        bm25.N = int(stats.get("N", 0)) or len(chunks)
        bm25.avgdl = float(stats.get("avgdl", 0.0))
        bm25.dl = {c.chunk_id: int(c.n_tokens) for c in chunks}
        if bm25.avgdl <= 0 and bm25.dl:
            bm25.avgdl = sum(bm25.dl.values()) / len(bm25.dl)
        return bm25

    def _answer(self, args, query: str, hits: List[QueryHit]) -> str:
        context_lines = []
        for h in hits:
            heading = " › ".join(h.heading_path)
            context_lines.append(
                f"{h.path} L{h.start_line}-{h.end_line} [{heading}]\n{h.snippet}")
        context = "\n\n".join(context_lines)
        prompt = util.render_prompt(KB_ANSWER_PMT, query=query, context=context)
        llm = OpenAIClient.from_args(args)
        return llm.call_llm_retry(
            prompt, args.model,
            retry=getattr(args, "retry", 10),
            temp=getattr(args, "temp", 1),
            top_p=getattr(args, "top_p", None),
            frequency_penalty=getattr(args, "frequency_penalty", None),
            presence_penalty=getattr(args, "presence_penalty", None),
            max_tokens=getattr(args, "max_tokens", None),
            extra_body=getattr(args, "extra_body", None),
            parse_output=util.ext_cont_block,
        )

    def _output(self, result: QueryResult, args) -> None:
        if getattr(args, "json", False):
            print(util.json_dump_model(result))
            return

        if not result.hits:
            print("未找到匹配结果。")
            return

        for i, h in enumerate(result.hits, 1):
            if h.bm25_score is not None:
                route = f"BM25({h.ranks.get('bm25', '-')})"
            else:
                route = "BM25(-)"
            if h.vec_score is not None:
                route += f" Vec({h.ranks.get('vec', '-')})"
            else:
                route += " Vec(-)"
            print(f"[{i}] {h.fused_score:.4f}  {h.path} › {' › '.join(h.heading_path)}  "
                  f"L{h.start_line}-{h.end_line}")
            print(f"    {route}  {h.snippet}")

        if result.answer:
            print(f"\n[回答]\n{result.answer}")

        if getattr(args, "context", 0) > 0:
            self._print_context(result.hits, int(args.context))

    def _print_context(self, hits: List[QueryHit], context: int) -> None:
        for h in hits:
            fp = Path(h.path)
            if not fp.is_absolute():
                fp = Path.cwd() / h.path
            if not fp.is_file():
                continue
            lines = fp.read_text(encoding="utf8", errors="replace").splitlines()
            start = max(1, h.start_line - context)
            end = min(len(lines), h.end_line + context)
            print(f"\n-- {h.path} L{start}-{end} --")
            for ln in range(start, end + 1):
                print(f"{ln:4d}\t{lines[ln - 1]}")


def kb_query_hdl(args) -> QueryResult:
    return KbQueryOrchestrator(args).run()


def reg_subparser(subparsers) -> None:
    p = subparsers.add_parser(
        "kb-query",
        help="在已建索引上执行 BM25 / 向量 / 混合检索",
        description="对已建索引执行 BM25 / 向量 / RRF 混合检索，支持人类可读与 --json 输出。",
    )
    p.add_argument("QUERY", nargs="?", help="查询文本")
    p.add_argument("-q", "--query", help="查询文本（与位置参数 QUERY 二选一）")
    p.add_argument("--index-dir", default=".kb-index", help="索引目录（默认 ./.kb-index）")
    p.add_argument("-n", "--topk", type=int, default=10, help="返回命中数（默认 10）")
    p.add_argument("--mode", choices=["bm25", "vec", "hybrid"], default="hybrid",
                   help="检索模式（默认 hybrid）")
    p.add_argument("--fuse", choices=["rrf", "weight"], default="rrf",
                   help="融合方式：rrf 或 weight（默认 rrf）")
    p.add_argument("--rrf-k", type=int, default=60, help="RRF 平滑常数 k（默认 60）")
    p.add_argument("--alpha", type=float, default=0.5, help="weight 融合中 BM25 权重（默认 0.5）")
    p.add_argument("--candidate-n", type=int, default=0,
                   help="单路召回数（0 = 自动 max(topk*5, 50)）")
    p.add_argument("--emb", default=argparse.SUPPRESS,
                   help="Embedding 模型名或本地路径（全局参数，与 manifest.emb_model 不一致则报错）")
    p.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto",
                   help="向量编码设备（默认 auto）")
    p.add_argument("--emb-batch-size", type=int, default=64, help="向量编码批大小（默认 64）")
    p.add_argument("--context", type=int, default=0,
                   help="输出命中块前后各 N 行原文（默认 0 不输出）")
    p.add_argument("--snippet-len", type=int, default=200, help="摘要长度（默认 200）")
    p.add_argument("--json", action="store_true", help="stdout 仅输出 JSON，日志走 stderr")
    p.add_argument("--answer", action="store_true", help="(P2) 基于检索结果生成 LLM 回答")
    p.add_argument("-v", "--verbose", action="store_true", help="详细日志")
    p.set_defaults(func=kb_query_hdl)
