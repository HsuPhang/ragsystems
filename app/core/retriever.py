"""检索层：Top-K 召回 + 相似度阈值过滤（防幻觉核心）。

设计：
- Top-K = 10（默认）
- 相似度阈值 = 0.6（settings.SIMILARITY_THRESHOLD）
- 相关度不足（top_score < threshold）→ 直接程序拒答，不让 LLM 基于通用知识发挥（防幻觉）
- 无检索结果 → 直接拒答
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llama_index.core.schema import NodeWithScore, QueryBundle

from app.config import settings
from app.core.embedding import embed_query
from app.core.vector_store import get_index
from app.utils import logger


@dataclass
class RetrievalResult:
    """检索结果封装。"""
    nodes: list[NodeWithScore] = field(default_factory=list)
    rejected: bool = False           # 是否被阈值拒绝（相关度不足）
    reject_reason: str = ""          # 拒答原因
    top_score: float = 0.0           # 最高分（用于前端展示）


def retrieve(
    query: str,
    top_k: int | None = None,
    similarity_threshold: float | None = None,
    filters: dict[str, Any] | None = None,
) -> RetrievalResult:
    """执行 Top-K 检索 + 相似度阈值过滤。"""
    top_k = top_k or settings.RETRIEVAL_TOP_K
    threshold = similarity_threshold if similarity_threshold is not None else settings.SIMILARITY_THRESHOLD

    index = get_index()
    retriever = index.as_retriever(
        similarity_top_k=top_k,
        filters=filters,
    )
    bundle = QueryBundle(query_str=query, embedding=embed_query(query))
    raw_nodes: list[NodeWithScore] = retriever.retrieve(bundle)

    if not raw_nodes:
        return RetrievalResult(rejected=True, reject_reason="知识库暂无相关资料，请先导入文档")

    top_score = raw_nodes[0].get_score() or 0.0

    # cosine 距离转相似度：similarity = 1 - distance
    # LlamaIndex + chromadb cosine 模式下 score 已经是相似度（0~1）
    if top_score < threshold:
        # 相关度不足以支撑回答：直接程序拒答，不让 LLM 基于通用知识发挥（防幻觉）
        logger.info(f"拒答(相关度不足): top_score={top_score:.3f} < threshold={threshold}")
        return RetrievalResult(
            nodes=raw_nodes,
            rejected=True,
            reject_reason="知识库中未找到与该问题直接相关的资料，暂时无法基于知识库回答。",
            top_score=top_score,
        )

    logger.info(f"检索 query='{query[:30]}...' 返回 {len(raw_nodes)} 条 "
                f"top_score={top_score:.3f}")
    return RetrievalResult(
        nodes=raw_nodes,
        rejected=False,
        top_score=top_score,
    )
