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

import re

from dataclasses import dataclass, field
from typing import Any

from llama_index.core.llms import ChatMessage

from app.config import settings
from app.core.llm import chat as llm_chat
from app.core.prompt import (
    SYSTEM_PROMPT_BASE,
    build_system_prompt,
    build_user_prompt,
    detect_emergency,
    is_non_medical,
)
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
            "title": meta.get("title", ""),
            "source": meta.get("source", "未知"),
            "category": meta.get("category", ""),
            "author": meta.get("author", ""),
            "update_time": meta.get("update_time", ""),
            "publish_date": meta.get("publish_date", "") or meta.get("update_time", ""),
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


def _append_source_list(answer_text: str, sources: list[dict]) -> str:
    """在回答末尾追加格式化的来源列表：以文章标题为主，附来源·分类·日期，标题做成可点击链接。

    使用 [1][2] 角标编号，便于正文中用 [1] 形式引用对应资料。
    """
    if not answer_text or not sources:
        return answer_text

    valid_sources = []
    seen_urls = set()
    for s in sources:
        url = s.get("url", "")
        if url and url not in ("-", "") and url not in seen_urls:
            seen_urls.add(url)
            valid_sources.append({
                "title": s.get("title", ""),
                "source": s.get("source", "未知"),
                "url": url,
                "category": s.get("category", ""),
                "publish_date": s.get("publish_date", ""),
            })

    if not valid_sources:
        return answer_text

    lines = ["\n\n---\n", "**参考来源：**"]
    for i, s in enumerate(valid_sources, 1):
        title = s["title"].strip() or "未知标题"
        # 标题做成可点击链接
        head = f"[{i}] 《[{title}]({s['url']})》"
        meta_parts = [s["source"]]
        if s.get("category"):
            meta_parts.append(s["category"])
        if s.get("publish_date") and s["publish_date"] not in ("未知", ""):
            meta_parts.append(s["publish_date"])
        lines.append(f"{head} · {' · '.join(meta_parts)}")

    return answer_text + "\n".join(lines)


def answer(
    query: str,
    use_rerank: bool = False,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    conversation_history: list[dict] | None = None,
    model: str | None = None,
    user_profile: dict | None = None,
) -> QAResult:
    """主入口：接收 query，返回 QAResult。
    
    Args:
        query: 用户问题
        use_rerank: 是否使用 reranker 重排
        top_k: 检索数量
        filters: 过滤条件
        conversation_history: 历史对话（用于多轮追问）
        model: 模型选择
        user_profile: 用户长期画像（健康背景），用于个性化科普，缓解多轮割裂
    
    TODO: 当前为同步调用，等待 LLM 完整响应后一次性返回。
          后续应实现 async generator 流式输出（stream_answer），
          使前端能够逐 token 展示，减少用户等待感。
    """
    if not query or not query.strip():
        return QAResult(answer="问题不能为空")

    # 紧急情况检测（优先处理）
    if detect_emergency(query):
        return QAResult(
            answer="【紧急提示】您描述的症状可能属于紧急情况，请立即拨打 120 急救电话或前往最近的医院急诊科就诊！切勿延误！",
            rejected=True,
        )
    
    # 非医疗问题检测
    if is_non_medical(query):
        return QAResult(
            answer="抱歉，我是医疗科普助手，仅能回答与医学、健康、疾病预防相关的问题。您的问题超出我的专业范围，请咨询相关领域的专家。",
            rejected=True,
        )

    # ① Top-K 检索
    result: RetrievalResult = retrieve(query, top_k=top_k, filters=filters)

    # ② 防幻觉拒答（极低相关度）
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

    # ④ 构造 Prompt
    contexts = _format_contexts(result.nodes)
    system_prompt = build_system_prompt(query)
    user_prompt = build_user_prompt(query, contexts, conversation_history, user_profile)

    # ⑤ LLM 生成
    try:
        answer_text = llm_chat([
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ], model=model)
    except Exception as e:
        logger.exception("LLM 调用失败")
        return QAResult(
            answer=f"抱歉，模型服务暂时不可用：{e}",
            sources=_build_sources(result.nodes),
            top_score=result.top_score,
            used_rerank=use_rerank,
        )

    # ⑥ 返回（参考来源由程序追加，不让 LLM 自己编）
    sources = _build_sources(result.nodes)
    answer_text = _append_source_list(answer_text, sources)

    return QAResult(
        answer=answer_text,
        sources=sources,
        top_score=result.top_score,
        used_rerank=use_rerank,
    )
