# -*- coding: utf-8 -*-
"""kb-index / kb-query 端到端 CLI 测试：临时语料 -> kb-index --no-emb -> kb-query --json。"""

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from BookerMarkdownTool.kb_index import kb_index_hdl
from BookerMarkdownTool.kb_query import kb_query_hdl
from BookerMarkdownTool.kb_models import QueryResult

ROOT = Path(__file__).resolve().parents[1]


def write_corpus(src: Path) -> None:
    (src / "a.md").write_text(
        "# 人工智能\n\n人工智能（AI）是计算机科学的一个分支。\n\n"
        "## 机器学习\n\n机器学习让计算机从数据中学习，无需显式编程。\n",
        encoding="utf8",
    )
    (src / "b.md").write_text(
        "# 混合检索\n\n混合检索结合了 BM25 倒排与向量召回，经 RRF 融合排序。\n",
        encoding="utf8",
    )
    (src / "c.md").write_text(
        "# 无关文档\n\n这篇文档里没有检索词。\n", encoding="utf8",
    )


def index_args(tmp_path, **overrides):
    base = dict(
        src=[str(tmp_path / "src")],
        index_dir=str(tmp_path / ".kb-index"),
        chunk_size=800,
        chunk_overlap=100,
        min_chunk_len=30,
        keep_code=False,
        exclude=None,
        tokenizer="search",
        stopwords=None,
        no_stopwords=True,
        user_dict=None,
        emb=None,
        no_emb=True,
        emb_batch_size=64,
        device="auto",
        workers=2,
        incremental=True,
        rebuild=False,
        prune=True,
        stats=False,
        verbose=False,
    )
    base.update(overrides)
    return Namespace(**base)


def query_args(tmp_path, **overrides):
    base = dict(
        query="混合检索",
        index_dir=str(tmp_path / ".kb-index"),
        topk=10,
        mode="bm25",
        fuse="rrf",
        rrf_k=60,
        alpha=0.5,
        candidate_n=0,
        emb=None,
        device="auto",
        emb_batch_size=64,
        context=0,
        snippet_len=200,
        json=True,
        answer=False,
        verbose=False,
        tokenizer="search",
        stopwords=None,
        no_stopwords=True,
        user_dict=None,
    )
    base.update(overrides)
    return Namespace(**base)


def run_md_tool(*args):
    r = subprocess.run(
        [sys.executable, "-m", "BookerMarkdownTool", *args],
        cwd=str(ROOT), capture_output=True, timeout=180,
    )
    r.stdout = r.stdout.decode("utf8", errors="replace")
    r.stderr = r.stderr.decode("utf8", errors="replace")
    return r


def test_e2e_bm25_json(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    write_corpus(src)
    kb_index_hdl(index_args(tmp_path))
    capsys.readouterr()  # 清掉索引构建的输出

    res = kb_query_hdl(query_args(tmp_path))
    out = capsys.readouterr().out
    data = json.loads(out)
    model = QueryResult.model_validate(data)
    assert model.query == "混合检索"
    assert model.mode == "bm25"
    assert model.hits, data
    assert any(h["path"].endswith("b.md") for h in data["hits"])
    assert all(set(h) >= {"chunk_id", "path", "fused_score", "ranks"} for h in data["hits"])


def test_json_stdout_only_json(tmp_path, capsys):
    src = tmp_path / "src"; src.mkdir()
    write_corpus(src)
    kb_index_hdl(index_args(tmp_path))
    capsys.readouterr()
    kb_query_hdl(query_args(tmp_path))
    out, err = capsys.readouterr()
    json.loads(out)  # 可解析
    assert out.strip().startswith("{")
    # 非 JSON 输出不应进入 stdout


def test_mode_vec_rejected_without_vectors(tmp_path, capsys):
    src = tmp_path / "src"; src.mkdir()
    write_corpus(src)
    kb_index_hdl(index_args(tmp_path))
    capsys.readouterr()
    res = kb_query_hdl(query_args(tmp_path, mode="vec"))
    out = capsys.readouterr()
    assert "未包含向量层" in out.err
    assert res.hits == []


def test_human_output(tmp_path, capsys):
    src = tmp_path / "src"; src.mkdir()
    write_corpus(src)
    kb_index_hdl(index_args(tmp_path))
    capsys.readouterr()
    res = kb_query_hdl(query_args(tmp_path, json=False))
    out = capsys.readouterr().out
    assert "›" in out
    assert "[1]" in out
    assert "b.md" in out


def test_incremental_update(tmp_path, capsys):
    src = tmp_path / "src"; src.mkdir()
    (src / "a.md").write_text(
        "# A\n\n第一版内容，这是一段用于测试增量索引的较长文本段落，字数足够通过最小长度过滤。\n",
        encoding="utf8",
    )
    idx = tmp_path / ".kb-index"
    kb_index_hdl(index_args(tmp_path, src=[str(src)], index_dir=str(idx)))
    capsys.readouterr()
    n1 = json.loads((idx / "manifest.json").read_text(encoding="utf8"))["n_chunks"]
    assert n1 >= 1

    # 修改 a.md：增量仅重建其块
    (src / "a.md").write_text(
        "# A\n\n第二版内容，更长一些的文本段落，用来验证增量重建后块数正确且只重建变更文件。\n",
        encoding="utf8",
    )
    kb_index_hdl(index_args(tmp_path, src=[str(src)], index_dir=str(idx)))
    capsys.readouterr()
    manifest = json.loads((idx / "manifest.json").read_text(encoding="utf8"))
    n2 = manifest["n_chunks"]
    assert manifest["files"]["a.md"]["chunk_ids"]
    chunks = (idx / "chunks.jsonl").read_text(encoding="utf8").strip().split("\n")
    assert len(chunks) == n2

    # 新增 b.md：块数增加
    (src / "b.md").write_text(
        "# B\n\n新增文档 b，这是一段用于测试增量新增文件后块数增加的较长文本段落。\n",
        encoding="utf8",
    )
    kb_index_hdl(index_args(tmp_path, src=[str(src)], index_dir=str(idx)))
    capsys.readouterr()
    manifest = json.loads((idx / "manifest.json").read_text(encoding="utf8"))
    n3 = manifest["n_chunks"]
    assert n3 > n2
    assert set(manifest["files"]) == {"a.md", "b.md"}
    chunks = (idx / "chunks.jsonl").read_text(encoding="utf8").strip().split("\n")
    assert len(chunks) == n3


def test_rebuild_equals_delete_rebuild(tmp_path, capsys):
    src = tmp_path / "src"; src.mkdir()
    write_corpus(src)
    idx = tmp_path / ".kb-index"
    kb_index_hdl(index_args(tmp_path, src=[str(src)], index_dir=str(idx)))
    chunks1 = (idx / "chunks.jsonl").read_bytes()

    # 删除索引目录后全量重建，结果应一致
    import shutil
    shutil.rmtree(idx)
    kb_index_hdl(index_args(tmp_path, src=[str(src)], index_dir=str(idx), rebuild=True))
    chunks2 = (idx / "chunks.jsonl").read_bytes()
    assert chunks1 == chunks2


def test_emb_position_before_and_after(tmp_path, capsys):
    src = tmp_path / "src"; src.mkdir()
    write_corpus(src)
    for cmd in (
        ["--emb", "bogus-model", "kb-index", str(src), "--no-emb",
         "--index-dir", str(tmp_path / "idx1")],
        ["kb-index", str(src), "--emb", "bogus-model", "--no-emb",
         "--index-dir", str(tmp_path / "idx2")],
    ):
        r = run_md_tool(*cmd)
        assert r.returncode == 0, r.stderr
    assert (tmp_path / "idx1" / "manifest.json").is_file()
    assert (tmp_path / "idx2" / "manifest.json").is_file()


def test_no_torch_runtime(monkeypatch, tmp_path, capsys):
    import importlib
    import BookerMarkdownTool.kb_index as ki
    import BookerMarkdownTool.kb_query as kq

    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    importlib.reload(ki)
    importlib.reload(kq)

    assert "sentence_transformers" not in sys.modules
    assert "torch" not in sys.modules

    src = tmp_path / "src"; src.mkdir()
    write_corpus(src)
    ki.kb_index_hdl(index_args(tmp_path, rebuild=True))
    capsys.readouterr()
    res = kq.kb_query_hdl(query_args(tmp_path, mode="bm25"))
    assert res.hits


def test_emb_missing_errors(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "a.md").write_text(
        "# A\n\n内容足够长以通过最小长度过滤的测试文档。\n", encoding="utf8",
    )
    r = run_md_tool("--emb", "", "kb-index", str(src),
                    "--index-dir", str(tmp_path / "idx"))
    assert r.returncode != 0
    assert "未指定 embedding 模型" in r.stderr
