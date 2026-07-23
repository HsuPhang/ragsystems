"""Embedding 模块：支持本地 BGE 模型和远程 text-embedding API。

支持两种模式：
- local: 使用本地 BGE 模型（bge-small-zh-v1.5 / bge-large-zh-v1.5）
- api: 使用 OpenAI 兼容的 text-embedding API

BGE 模型特性：
- bge-small-zh-v1.5: 中文专用，输出维度 512，轻量快速
- bge-large-zh-v1.5: 中文专用，输出维度 1024，效果更好

text-embedding API 特性：
- text-embedding-3-small: 输出维度 1536，支持多语言
- text-embedding-3-large: 输出维度 3072，效果更好

注意：模型加载较重，使用惰性导入，避免启动时卡住。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.embeddings import BaseEmbedding

from app.config import settings
from app.utils import detect_device, logger

_embed_model: "BaseEmbedding | None" = None


def get_embed_model() -> "BaseEmbedding":
    """单例 Embedding 模型（惰性加载，首次调用较慢）。"""
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    embed_type = settings.EMBEDDING_TYPE.lower()

    if embed_type == "api":
        logger.info(f"使用远程 Embedding API: {settings.TEXT_EMBEDDING_MODEL}")
        logger.info(f"API Base URL: {settings.OPENAI_BASE_URL}")
        from llama_index.embeddings.openai import OpenAIEmbedding

        _embed_model = OpenAIEmbedding(
            model=settings.TEXT_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            embed_batch_size=8,
        )
        logger.info("远程 Embedding API 配置完成")

    else:
        device = detect_device(settings.EMBEDDING_DEVICE)
        logger.info(f"加载本地 Embedding 模型: {settings.EMBEDDING_MODEL_PATH} "
                    f"(device={device})")
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        _embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL_PATH,
            device=device,
            embed_batch_size=8,
            max_length=512,
            normalize=True,
        )
        logger.info("本地 Embedding 模型加载完成")

    return _embed_model


def embed_query(text: str) -> list[float]:
    """对单条 query 生成向量。"""
    embed_type = settings.EMBEDDING_TYPE.lower()

    if embed_type == "api":
        model = get_embed_model()
        return model.get_query_embedding(text)

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
