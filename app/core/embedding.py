"""Embedding 模块：加载 BAAI/bge-m3（推荐）或 bge-large-zh-v1.5。

BGE-m3 特性：
- 支持中文、英文、长文本（最大 8192 token）
- 输出维度 1024
- MTEB 中文榜单表现 SOTA

注意：模型加载较重，使用惰性导入（非 @lru_cache 包装），避免启动时卡住。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.embeddings import BaseEmbedding

from app.config import settings
from app.utils import logger

_embed_model: "BaseEmbedding | None" = None


def get_embed_model() -> "BaseEmbedding":
    """单例 Embedding 模型（惰性加载，首次调用较慢）。"""
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    logger.info(f"加载 Embedding 模型: {settings.EMBEDDING_MODEL_PATH} "
                f"(device={settings.EMBEDDING_DEVICE})")
    _embed_model = HuggingFaceEmbedding(
        model_name=settings.EMBEDDING_MODEL_PATH,
        device=settings.EMBEDDING_DEVICE,
        embed_batch_size=8,
        max_length=512,
        normalize=True,
    )
    logger.info("Embedding 模型加载完成")
    return _embed_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """对文本列表生成向量（用于离线构建索引）。"""
    model = get_embed_model()
    return model.get_text_embedding_batch(texts)


def embed_query(text: str) -> list[float]:
    """对单条 query 生成向量。"""
    model_name = settings.EMBEDDING_MODEL_PATH.lower()
    if "bge-m3" in model_name:
        text_to_encode = text
    elif "zh" in model_name:
        try:
            from llama_index.embeddings.huggingface.utils import format_query
            text_to_encode = format_query(text, settings.EMBEDDING_MODEL_PATH)
        except ImportError:
            text_to_encode = text
    else:
        text_to_encode = text

    model = get_embed_model()
    return model.get_query_embedding(text_to_encode)
