"""重排序层：BAAI/bge-reranker-large 二次重排。

为什么需要 Reranker：
- Embedding 检索速度快但粒度粗（语义近似）
- Cross-Encoder Reranker 精确但慢
- 工程实践：Embedding Top10 → Rerank Top5 给 LLM

注意：模型加载较重，惰性加载，避免启动时卡住。
"""
from __future__ import annotations


from app.config import settings
from app.core.retriever import RetrievalResult
from app.utils import logger

_reranker = None


def get_reranker():
    """单例重排序模型（惰性加载）。"""
    global _reranker
    if _reranker is not None:
        return _reranker

    from sentence_transformers import CrossEncoder

    logger.info(f"加载 Reranker 模型: {settings.RERANKER_MODEL_PATH}")
    _reranker = CrossEncoder(
        settings.RERANKER_MODEL_PATH,
        device=settings.RERANKER_DEVICE,
        max_length=512,
    )
    logger.info("Reranker 模型加载完成")
    return _reranker


def rerank(
    query: str,
    result: RetrievalResult,
    top_n: int | None = None,
) -> RetrievalResult:
    """对 RetrievalResult 中的 nodes 重新打分并截断到 top_n。"""
    if result.rejected or not result.nodes:
        return result
    top_n = top_n or settings.RERANK_TOP_N

    model = get_reranker()
    pairs = [(query, n.node.get_content()[:1024]) for n in result.nodes]
    scores = model.predict(pairs, show_progress_bar=False)

    # 按 reranker 分数降序
    ranked = sorted(
        zip(result.nodes, scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )[:top_n]

    from llama_index.core.schema import NodeWithScore
    new_nodes = [
        NodeWithScore(node=n.node, score=float(s))
        for n, s in ranked
    ]
    result.nodes = new_nodes
    result.top_score = new_nodes[0].score if new_nodes else 0.0
    logger.info(f"Rerank 完成: {len(pairs)} -> {len(new_nodes)}")
    return result
