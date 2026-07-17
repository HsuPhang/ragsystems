"""问答引擎：整合 retriever + reranker + prompt + LLM。

完整流程：
    用户 query
       ↓
    ① Embedding 检索 (Top-K=10)
       ↓
    ② 相似度阈值过滤（防幻觉）
       ↓
    ③ Reranker 重排 (Top-N=5)
       ↓
    ④ 构造 Prompt (含引用)
       ↓
    ⑤ LLM 生成
       ↓
    ⑥ 返回 {answer, sources, top_score}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llama_index.core.llms import ChatMessage

from app.config import settings
from app.core.llm import chat as llm_chat
from app.core.prompt import SYSTEM_PROMPT, build_user_prompt
from app.core.reranker import rerank
from app.core.retriever import RetrievalResult, retrieve
from app.utils import logger


@dataclass
class QAResult:
    """最终问答结果。"""
    answer: str
    sources: list[dict] = field(default_factory=list)   # 引用来源列表
    top_score: float = 0.0
    used_rerank: bool = True
    rejected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "top_score": round(self.top_score, 4),
            "used_rerank": self.used_rerank,
            "rejected": self.rejected,
        }


def _build_sources(nodes) -> list[dict]:
    """从检索结果构造可序列化的引用来源。"""
    sources = []
    seen = set()
    for i, n in enumerate(nodes, 1):
        meta = n.node.metadata or {}
        key = (meta.get("source", ""), meta.get("chunk_id", ""))
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "index": i,
            "source": meta.get("source", "未知"),
            "category": meta.get("category", ""),
            "author": meta.get("author", ""),
            "update_time": meta.get("update_time", ""),
            "url": meta.get("url", ""),
            "chunk_id": meta.get("chunk_id", ""),
            "score": round(float(n.score or 0), 4),
            "preview": (n.node.get_content() or "")[:160],
        })
    return sources


def _format_contexts(nodes) -> list[dict]:
    """构造给 Prompt 用的上下文。"""
    return [
        {
            "text": n.node.get_content(),
            "metadata": n.node.metadata or {},
            "score": float(n.score or 0),
        }
        for n in nodes
    ]


def answer(
    query: str,
    use_rerank: bool = False,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
) -> QAResult:
    """主入口：接收 query，返回 QAResult。"""
    if not query or not query.strip():
        return QAResult(answer="问题不能为空")

    # ① Top-K 检索
    result: RetrievalResult = retrieve(query, top_k=top_k, filters=filters)

    # ② 防幻觉拒答
    if result.rejected:
        return QAResult(
            answer=result.reject_reason
            or "抱歉，知识库中暂未收录与该问题相关的内容，建议您咨询专业医生。",
            rejected=True,
            top_score=result.top_score,
        )

    # ③ Reranker 重排
    if use_rerank:
        try:
            result = rerank(query, result)
        except Exception as e:
            logger.warning(f"Reranker 重排失败，已跳过: {e}")
            # 保持原始检索结果继续执行

    # ④ 构造 Prompt
    contexts = _format_contexts(result.nodes)
    user_prompt = build_user_prompt(query, contexts)

    # ⑤ LLM 生成
    try:
        answer_text = llm_chat([
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ])
    except Exception as e:
        logger.exception("LLM 调用失败")
        return QAResult(
            answer=f"抱歉，模型服务暂时不可用：{e}",
            sources=_build_sources(result.nodes),
            top_score=result.top_score,
            used_rerank=use_rerank,
        )

    # ⑥ 返回
    return QAResult(
        answer=answer_text,
        sources=_build_sources(result.nodes),
        top_score=result.top_score,
        used_rerank=use_rerank,
    )
