"""管理员接口：登录、统计、用户/日志查看。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import create_token, get_current_admin, verify_password
from app.api.schemas import (
    GenericResponse,
    LoginRequest,
    LoginResponse,
    StatsResponse,
)
from app.config import settings
from app.core.vector_store import count as chroma_count
from app.db import Admin, ChatMessage, ChatSession, Document, SystemLog, get_db

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    """管理员登录（首次使用 .env 中的默认账号自动建账号）。"""
    # 1. 自动初始化默认管理员（首次启动时）
    if not db.query(Admin).filter(Admin.username == settings.ADMIN_USERNAME).first():
        from app.api.auth import hash_password
        db.add(Admin(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        ))
        db.commit()
        logger_msg = f"已自动创建默认管理员: {settings.ADMIN_USERNAME}"
        print(logger_msg)

    admin = db.query(Admin).filter(Admin.username == req.username).first()
    if not admin or not verify_password(req.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token({"sub": admin.username, "role": "admin"})
    return LoginResponse(access_token=token, username=admin.username)


@router.get("/me", response_model=GenericResponse)
def me(admin: Annotated[Admin, Depends(get_current_admin)]) -> GenericResponse:
    return GenericResponse(data={"username": admin.username})


@router.get("/stats", response_model=StatsResponse)
def stats(
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> StatsResponse:
    return StatsResponse(
        document_total=db.query(Document).filter(Document.status == "active").count(),
        chunk_total=chroma_count(),
        chat_session_total=db.query(ChatSession).count(),
        chat_message_total=db.query(ChatMessage).count(),
        admin_total=db.query(Admin).count(),
    )


@router.get("/logs", response_model=GenericResponse)
def logs(
    admin: Annotated[Admin, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 100,
):
    rows = (
        db.query(SystemLog)
        .order_by(SystemLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    items = [
        {
            "id": r.id,
            "level": r.level,
            "module": r.module,
            "action": r.action,
            "message": r.message,
            "operator": r.operator,
            "created_at": r.created_at.isoformat(timespec="seconds"),
        }
        for r in rows
    ]
    return GenericResponse(data=items)
