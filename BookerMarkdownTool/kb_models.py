# -*- coding: utf-8 -*-
"""kb-index / kb-query 子命令的 Pydantic 数据模型。"""

from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class ChunkMeta(BaseModel):
    chunk_id: int = Field(..., description="分块全局唯一 ID，与 chunks.jsonl 行序对齐")
    path: str = Field(..., description="相对 --src 的源文件路径")
    heading_path: List[str] = Field(..., description="该分块所属的标题路径，由浅入深")
    start_line: int = Field(..., description="分块在源文件中的起始行号（1-based）")
    end_line: int = Field(..., description="分块在源文件中的结束行号（1-based）")
    text: str = Field(..., description="分块文本内容")
    n_tokens: int = Field(..., description="jieba 分词后（去停用词）的 token 数，即 BM25 的 dl")
    md5: str = Field(..., description="分块文本的 md5")


class FileEntry(BaseModel):
    md5: str = Field(..., description="源文件内容 md5，用于增量 diff")
    mtime: float = Field(..., description="源文件修改时间戳")
    chunk_ids: List[int] = Field(..., description="该文件产生的分块 ID 列表")


class IndexManifest(BaseModel):
    format_version: int = Field(1, description="索引目录格式版本，不匹配时提示 --rebuild")
    tokenizer_version: str = Field(..., description="分词器版本标识 f\"jieba-{jieba.__version__}-{mode}\"")
    emb_model: Optional[str] = Field(None, description="向量化使用的 embedding 模型名或本地路径")
    emb_dim: Optional[int] = Field(None, description="向量维度")
    emb_normalized: bool = Field(True, description="向量是否已 L2 归一化")
    created_at: str = Field(..., description="索引创建/最后更新时间")
    src_root: str = Field(..., description="索引源文件根目录")
    n_chunks: int = Field(..., description="分块总数")
    files: Dict[str, FileEntry] = Field(..., description="源文件条目，path -> FileEntry")


class QueryHit(BaseModel):
    chunk_id: int = Field(..., description="命中分块 ID")
    path: str = Field(..., description="分块所属源文件路径")
    heading_path: List[str] = Field(..., description="标题路径")
    start_line: int = Field(..., description="起始行号")
    end_line: int = Field(..., description="结束行号")
    snippet: str = Field(..., description="摘要文本")
    bm25_score: Optional[float] = Field(None, description="BM25 原始得分")
    vec_score: Optional[float] = Field(None, description="向量原始得分（余弦/内积）")
    fused_score: float = Field(..., description="融合后得分")
    ranks: Dict[str, int] = Field(..., description="各路排名，如 {\"bm25\": 3, \"vec\": 11}")


class QueryResult(BaseModel):
    query: str = Field(..., description="原始查询文本")
    mode: str = Field(..., description="检索模式 bm25/vec/hybrid")
    emb_model: Optional[str] = Field(None, description="查询向量化所用 embedding 模型")
    hits: List[QueryHit] = Field(..., description="命中分块列表，已按 fused_score 降序排列")
    answer: Optional[str] = Field(None, description="--answer 开启时的 LLM 生成回答")
