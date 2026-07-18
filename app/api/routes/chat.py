"""聊天接口：/api/chat  登录用户方可使用。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin
from app.api.schemas import ChatRequest, ChatResponse, GenericResponse
from app.core.engine import answer as engine_answer
from app.db import Admin, ChatMessage, ChatSession, get_db
from app.utils import gen_id, logger

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    """处理一次问答请求，并落库。"""
    # 1. 会话
    session_id = req.session_id or gen_id("sess")
    if not db.query(ChatSession).filter(ChatSession.session_id == session_id).first():
        sess = ChatSession(
            session_id=session_id,
            user_id=admin.id,
            title=req.query[:30] + ("…" if len(req.query) > 30 else ""),
        )
        db.add(sess)
        db.flush()

    # 2. 调问答引擎
    filters = {"category": req.category} if req.category else None
    result = engine_answer(
        query=req.query,
        use_rerank=req.use_rerank,
        top_k=req.top_k,
        filters=filters,
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
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> GenericResponse:
    """获取当前用户的某次会话历史。"""
    sess = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == admin.id,
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
