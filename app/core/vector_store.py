"""向量知识库层：Chroma 持久化与管理。

Chroma 职责（与 MySQL 分离）：
- 存储 chunk 文本、embedding、metadata
- 支持余弦相似度检索 + metadata 过滤
- 持久化到磁盘，重启不丢
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext, VectorStoreIndex

from app.config import settings
from app.utils import logger

# 单一集合名，医疗科普场景
COLLECTION_NAME = "medical_knowledge"


@lru_cache(maxsize=1)
def get_chroma_client():
    """单例 Chroma 客户端（持久化模式）。"""
    persist_dir = settings.resolve("CHROMA_PERSIST_DIR")
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
    )
    logger.info(f"Chroma 客户端已连接: {persist_dir}")
    return client


def get_vector_store() -> ChromaVectorStore:
    """获取 LlamaIndex 封装的 ChromaVectorStore。"""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # 余弦相似度
    )
    return ChromaVectorStore(chroma_collection=collection)


def get_storage_context() -> StorageContext:
    return StorageContext.from_defaults(vector_store=get_vector_store())


def add_nodes(nodes: list[BaseNode], embed_model=None) -> list[str]:
    """把 nodes 写入向量库，返回生成的 ID 列表。"""
    from app.core.embedding import get_embed_model
    embed_model = embed_model or get_embed_model()

    storage = get_storage_context()
    index = VectorStoreIndex(
        nodes=[],
        storage_context=storage,
        embed_model=embed_model,
    )

    before_count = count()
    ids = index.insert_nodes(nodes, show_progress=True)
    after_count = count()
    inserted_count = after_count - before_count

    if ids is not None:
        logger.info(f"已写入 {len(ids)} 条 chunk 到 Chroma (collection={COLLECTION_NAME})")
        return ids
    else:
        logger.info(f"已写入 {inserted_count} 条 chunk 到 Chroma (collection={COLLECTION_NAME})")
        return []


def get_index() -> VectorStoreIndex:
    """从已存在的向量库加载索引（不重新构建）。"""
    from app.core.embedding import get_embed_model

    storage = get_storage_context()
    return VectorStoreIndex.from_vector_store(
        vector_store=storage.vector_store,
        embed_model=get_embed_model(),
    )


def delete_by_doc_id(doc_id: str) -> int:
    """按 doc_id 删除所有 chunk（管理员删除文档时使用）。"""
    client = get_chroma_client()
    collection = client.get_collection(COLLECTION_NAME)
    # chunk_id 形如 chunk_xxxxxx，我们用 doc_id 作为 metadata 字段
    res = collection.get(where={"doc_id": doc_id})
    ids = res.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    logger.info(f"已删除 doc_id={doc_id} 的 {len(ids)} 个 chunk")
    return len(ids)


def reset_collection() -> None:
    """清空集合（仅调试用）。"""
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.warning(f"已重置 collection: {COLLECTION_NAME}")
    except Exception as e:
        logger.warning(f"重置 collection 失败: {COLLECTION_NAME}, 错误: {e}")


def count() -> int:
    """返回当前向量库中 chunk 数量。"""
    client = get_chroma_client()
    try:
        col = client.get_collection(COLLECTION_NAME)
        return col.count()
    except Exception:
        return 0
