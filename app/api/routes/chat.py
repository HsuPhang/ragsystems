"""聊天接口：/api/chat  登录用户方可使用。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.schemas import ChatRequest, ChatResponse, GenericResponse
from app.core.engine import answer as engine_answer
from app.core.memory import extract_user_profile
from app.db import ChatMessage, ChatSession, User, UserProfile, get_db
from app.utils import gen_id, logger

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    """处理一次问答请求，并落库。"""
    # 1. 会话
    session_id = req.session_id or gen_id("sess")
    if not db.query(ChatSession).filter(ChatSession.session_id == session_id).first():
        sess = ChatSession(
            session_id=session_id,
            user_id=user.id,
            user_type="user",
            title=req.query[:30] + ("…" if len(req.query) > 30 else ""),
        )
        db.add(sess)
        db.flush()

    # 2. 获取历史对话（用于多轮对话）
    conversation_history = []
    if session_id:
        history_rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(20)
            .all()
        )
        conversation_history = [
            {"role": r.role, "content": r.content}
            for r in history_rows
        ]

    # 3. 调问答引擎
    filters = {"category": req.category} if req.category else None
    # 将前端显示名映射为 API 模型名
    model_map = {
        "DeepSeek-V4-Flash": "deepseek-v4-flash",
        "DeepSeek-V4-Pro": "deepseek-v4-pro",
    }
    model = model_map.get(req.model) if req.model else None

    # 查询用户长期画像（用于个性化科普，缓解多轮割裂）
    user_profile_data = None
    profile_row = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user.id)
        .first()
    )
    if profile_row and profile_row.profile_data:
        user_profile_data = profile_row.profile_data

    result = engine_answer(
        query=req.query,
        use_rerank=req.use_rerank,
        top_k=req.top_k,
        filters=filters,
        conversation_history=conversation_history,
        model=model,
        user_profile=user_profile_data,
    )

    # 3. 落库
    db.add(ChatMessage(
        session_id=session_id,
        role="user",
        content=req.query,
    ))
    db.add(ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result.answer,
        sources=result.sources if result.sources else [],
        top_score=result.top_score,
        rejected=1 if result.rejected else 0,
    ))
    db.commit()

    logger.info(f"chat session={session_id} rejected={result.rejected} "
                f"top_score={result.top_score:.3f}")

    # 异步更新用户画像（不阻塞主流程）
    try:
        if not result.rejected:
            full_history = conversation_history + [
                {"role": "user", "content": req.query},
            ]
            extract_user_profile(full_history, user.id, db)
    except Exception as e:
        logger.warning(f"用户画像提取失败（不影响回答）: {e}")

    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        top_score=result.top_score,
        used_rerank=result.used_rerank,
        rejected=result.rejected,
        session_id=session_id,
    )


@router.get("/history/{session_id}", response_model=GenericResponse)
def history(
    session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GenericResponse:
    """获取当前用户的某次会话历史。"""
    sess = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == user.id,
    ).first()
    if not sess:
        return GenericResponse(data=[])
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    items = [
        {
            "role": r.role,
            "content": r.content,
            "sources": r.sources or [],
            "top_score": r.top_score,
            "rejected": bool(r.rejected),
            "created_at": r.created_at.isoformat(timespec="seconds"),
        }
        for r in rows
    ]
    return GenericResponse(data=items)
