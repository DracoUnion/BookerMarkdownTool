# -*- coding: utf-8 -*-
"""kb-core 单元测试：分词、BM25 手算、RRF、向量检索、FakeEncoder。"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from BookerMarkdownTool.kb_core import (BM25Index, ChunkSplitter, FakeEncoder,
                                        HybridRetriever, Tokenizer, VectorStore,
                                        make_snippet)
from BookerMarkdownTool.kb_models import ChunkMeta


def test_tokenize_search_contains_expected_words():
    toks = Tokenizer(mode="search").tokenize("知识库检索增强")
    assert "知识" in toks
    assert "检索" in toks
    assert "增强" in toks


def test_tokenize_cut_differs_from_search():
    text = "知识库检索增强生成技术"
    search = Tokenizer(mode="search").tokenize(text)
    cut = Tokenizer(mode="cut").tokenize(text)
    assert set(cut) != set(search)


def test_stopwords_removed():
    toks = Tokenizer(mode="search", stopwords={"的", "了", "在"}).tokenize("我的书在桌子上了")
    assert "的" not in toks
    assert "了" not in toks
    assert "在" not in toks


def test_tokenizer_version():
    import jieba
    assert Tokenizer("search").version == f"jieba-{jieba.__version__}-search"
    assert Tokenizer("cut").version != Tokenizer("search").version


def test_bm25_hand_calculated():
    # 手算 BM25：N=2, avgdl=2.5
    # doc0 = [apple, banana, apple], doc1 = [apple, orange]
    bm25 = BM25Index(k1=1.5, b=0.75)
    bm25.add_document(0, ["apple", "banana", "apple"])
    bm25.add_document(1, ["apple", "orange"])
    bm25.finish()
    ranked = bm25.topk(["apple", "banana"], 10)
    assert [cid for cid, _ in ranked] == [0, 1]
    scores = dict(ranked)
    # 手算 BM25：N=2, avgdl=2.5, df(apple)=2, df(banana)=1
    # doc0 = [apple x2, banana], doc1 = [apple]
    assert abs(scores[0] - 0.8806) < 0.001, scores
    assert abs(scores[1] - 0.2004) < 0.001, scores


def test_rrf_order():
    bm25 = BM25Index()
    bm25.finish()
    retriever = HybridRetriever(bm25, None, [], mode="hybrid", fuse="rrf", rrf_k=60)
    bm25_ranked = [(3, 1.0), (1, 0.9), (2, 0.8)]
    vec_ranked = [(1, 1.0), (2, 0.9), (3, 0.8)]
    fused, ranks_map, _raw = retriever._fuse(bm25_ranked, vec_ranked)
    order = [cid for cid, _ in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))]
    assert order == [1, 3, 2], order
    assert ranks_map[1] == {"bm25": 2, "vec": 1}
    assert ranks_map[3] == {"bm25": 1, "vec": 3}


def test_weight_fuse():
    bm25 = BM25Index()
    bm25.finish()
    retriever = HybridRetriever(bm25, None, [], mode="hybrid", fuse="weight", alpha=0.5)
    bm25_ranked = [(1, 10.0), (2, 0.0)]
    vec_ranked = [(2, 10.0), (1, 0.0)]
    fused, _, _ = retriever._fuse(bm25_ranked, vec_ranked)
    # min-max 归一化后两路各自 1.0/0.5，alpha=0.5 -> 1 和 2 平局，按 cid 升序
    order = [cid for cid, _ in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))]
    assert order == [1, 2], order


def test_fake_encoder_search():
    enc = FakeEncoder(dim=8)
    texts = ["hello world", "goodbye moon", "hello"]
    vecs = enc.encode(texts)
    assert vecs.shape == (3, 8)
    vs = VectorStore(vecs)
    q = enc.encode(["hello"])[0]
    ranked = vs.search(q, 3)
    assert ranked[0][0] == 2  # 完全相同的文本向量相似度最高
    assert ranked[0][1] == pytest.approx(1.0)


def test_make_snippet():
    s = make_snippet("a b 知识库检查 c d", ["知识库"], 10)
    assert "知识库" in s
    assert len(s) <= 10


def test_chunk_splitter_heading_path():
    text = "# 标题一\n\n正文段落一，用来测试切块长度。\n\n## 子标题\n\n正文段落二内容。\n"
    chunks = ChunkSplitter(chunk_size=40, chunk_overlap=5, min_chunk_len=5).split(text, "x.md")
    assert chunks
    assert chunks[0]["heading_path"] == ["标题一"]
    assert any("子标题" in c["heading_path"] for c in chunks)


def test_chunk_splitter_drops_code_by_default():
    text = "# 标题\n\n普通文字。\n\n```python\nprint('code block')\n```\n"
    chunks = ChunkSplitter(chunk_size=100, min_chunk_len=5).split(text, "x.md")
    joined = "\n".join(c["text"] for c in chunks)
    assert "print" not in joined


def test_chunk_splitter_keeps_code():
    text = "# 标题\n\n```python\nprint('code')\n```\n"
    chunks = ChunkSplitter(chunk_size=100, min_chunk_len=5, keep_code=True).split(text, "x.md")
    joined = "\n".join(c["text"] for c in chunks)
    assert "print" in joined


def test_meta_round_trip():
    m = ChunkMeta(chunk_id=0, path="a.md", heading_path=["H"], start_line=1, end_line=2,
                  text="hi", n_tokens=1, md5="x")
    m2 = ChunkMeta.model_validate_json(m.model_dump_json())
    assert m2 == m


def test_vec_retrieve_with_fake_encoder():
    enc = FakeEncoder(dim=8)
    texts = ["hello world", "goodbye moon", "hello"]
    vecs = enc.encode(texts)
    chunks = [
        ChunkMeta(chunk_id=i, path="a.md", heading_path=["H"], start_line=i + 1, end_line=i + 1,
                  text=t, n_tokens=3, md5="x")
        for i, t in enumerate(texts)
    ]
    vs = VectorStore(vecs)
    bm25 = BM25Index()
    for c in chunks:
        bm25.add_document(c.chunk_id, c.text.split())
    bm25.finish()

    retriever = HybridRetriever(bm25, vs, chunks, mode="vec", fuse="rrf")
    hits = retriever.retrieve("hello", Tokenizer(), 5, encoder=enc)
    assert len(hits) == 3
    assert hits[0].chunk_id == 2  # 完全相同的文本余弦相似度最高
    assert hits[0].vec_score == pytest.approx(1.0)
    assert all(h.vec_score is not None and h.bm25_score is None for h in hits)
    assert all("vec" in h.ranks and "bm25" not in h.ranks for h in hits)

    retriever = HybridRetriever(bm25, vs, chunks, mode="hybrid", fuse="rrf")
    hits = retriever.retrieve("hello", Tokenizer(), 5, encoder=enc)
    assert len(hits) == 3
    assert all("vec" in h.ranks for h in hits)
    assert any("bm25" in h.ranks for h in hits)
    assert all(h.fused_score is not None for h in hits)
