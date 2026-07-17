"""数据预处理：文档加载、清洗、分块、Metadata 注入。

Chunk 策略（参考建议.md 第三节）：
- chunk_size  = 500
- chunk_overlap = 100
- 按句子切分，避免在句子中间断开
- 每段 chunk 自动附带：来源、疾病分类、发布时间、作者、标签 等 metadata
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document, TextNode

from app.config import settings
from app.utils import logger

# 文档级别的元数据字段（每篇文档必带，便于检索时过滤）
DOC_META_KEYS = ("source", "category", "author", "update_time", "keywords", "url")


def _normalize_doc_metadata(doc: Document) -> Document:
    """清洗 / 补全文档级 metadata。"""
    meta = dict(doc.metadata or {})
    # 默认值
    meta.setdefault("source", doc.metadata.get("file_name", "未知来源"))
    meta.setdefault("category", "未分类")
    meta.setdefault("author", "")
    meta.setdefault("update_time", "")
    meta.setdefault("keywords", [])
    meta.setdefault("url", "")
    # 文件名固定
    if "file_name" not in meta and doc.metadata.get("file_path"):
        meta["file_name"] = Path(doc.metadata["file_path"]).name
    doc.metadata = meta
    return doc


def load_documents(input_dir: str | Path, glob: str = "**/*") -> list[Document]:
    """从目录加载文档（支持 .pdf / .txt / .md / .docx / .html）。"""
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"数据目录不存在: {input_dir}")

    reader = SimpleDirectoryReader(
        input_dir=str(input_dir),
        recursive=True,
        required_exts=[".pdf", ".txt", ".md", ".docx", ".html"],
        file_metadata=lambda fp: {
            "file_name": Path(fp).name,
            "file_path": str(fp),
        },
    )
    docs = reader.load_data()
    docs = [_normalize_doc_metadata(d) for d in docs]
    logger.info(f"从 {input_dir} 加载 {len(docs)} 篇文档")
    return docs


def split_documents(
    docs: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TextNode]:
    """把 Document 切成 TextNode，并把文档级 metadata 透传到每个 chunk。"""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        paragraph_separator="\n\n",
    )
    nodes: list[TextNode] = splitter.get_nodes_from_documents(docs, show_progress=True)
    logger.info(f"分块完成：{len(docs)} 篇文档 → {len(nodes)} 个 chunk "
                f"(size={chunk_size}, overlap={chunk_overlap})")
    return nodes


def enrich_node_metadata(
    node: BaseNode,
    extra: dict[str, Any] | None = None,
) -> BaseNode:
    """给 chunk 节点追加 metadata（chunk_id / 块序号等）。"""
    meta = dict(node.metadata or {})
    # 透传文档级 metadata
    for k in DOC_META_KEYS:
        if k not in meta and k in (extra or {}):
            meta[k] = extra[k]
    if extra:
        for k, v in extra.items():
            meta.setdefault(k, v)
    # chunk 自身的元数据
    if "chunk_id" not in meta:
        from app.utils import gen_id
        meta["chunk_id"] = gen_id("chunk")
    node.metadata = meta
    return node


def build_nodes_from_dir(input_dir: str | Path) -> list[TextNode]:
    """一键式：加载 + 分块 + 元数据补全。"""
    docs = load_documents(input_dir)
    nodes = split_documents(docs)
    nodes = [enrich_node_metadata(n) for n in nodes]
    return nodes
