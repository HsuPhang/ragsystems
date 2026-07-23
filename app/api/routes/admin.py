"""管理员接口：登录、统计、用户/日志查看。"""
from __future__ import annotations

import os
import shutil
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import create_token, get_current_admin, hash_password, verify_password
from app.api.schemas import (
    GenericResponse,
    LoginRequest,
    StatsResponse,
)
from app.config import settings
from app.core.vector_store import count as chroma_count
from app.db import Admin, ChatMessage, ChatSession, Document, SystemLog, get_db
from app.utils import logger

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def _get_avatar_url(avatar_path: str) -> str:
    if not avatar_path:
        return ""
    return f"/uploads/avatar/{avatar_path}"


def _ensure_avatar_dir() -> str:
    avatar_dir = settings.resolve("AVATAR_DIR")
    avatar_dir.mkdir(parents=True, exist_ok=True)
    return str(avatar_dir)


router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.post("/register", response_model=GenericResponse)
def register(req: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> GenericResponse:
    if db.query(Admin).count() > 0:
        raise HTTPException(
            status_code=403,
            detail="系统已存在管理员，请联系管理员添加账号",
        )

    if len(req.username) < 2 or len(req.username) > 20:
        raise HTTPException(status_code=400, detail="用户名长度需在2-20字符之间")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="密码长度不能少于8位")

    admin = Admin(
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(admin)
    db.commit()

    token = create_token({"sub": admin.username, "role": "admin"})
    return GenericResponse(data={
        "access_token": token,
        "token_type": "bearer",
        "username": admin.username,
        "avatar": "",
    })


@router.post("/login", response_model=GenericResponse)
def login(req: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> GenericResponse:
    if not db.query(Admin).filter(Admin.username == settings.ADMIN_USERNAME).first():
        db.add(Admin(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        ))
        db.commit()
        logger.info(f"已自动创建默认管理员: {settings.ADMIN_USERNAME}")

    admin = db.query(Admin).filter(Admin.username == req.username).first()
    if not admin or not verify_password(req.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token({"sub": admin.username, "role": "admin"})
    return GenericResponse(data={
        "access_token": token,
        "token_type": "bearer",
        "username": admin.username,
        "avatar": _get_avatar_url(admin.avatar),
    })


@router.get("/me", response_model=GenericResponse)
def me(admin: Annotated[Admin, Depends(get_current_admin)]) -> GenericResponse:
    return GenericResponse(data={"username": admin.username, "avatar": _get_avatar_url(admin.avatar)})


@router.post("/avatar", response_model=GenericResponse)
def upload_avatar(
    admin: Annotated[Admin, Depends(get_current_admin)],
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
):
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型，支持: {', '.join(ALLOWED_EXTENSIONS)}")

    content = file.file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过2MB")

    avatar_dir = _ensure_avatar_dir()
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    new_path = os.path.join(avatar_dir, new_filename)

    if admin.avatar:
        old_path = os.path.join(avatar_dir, admin.avatar)
        if os.path.exists(old_path):
            os.remove(old_path)

    with open(new_path, "wb") as f:
        f.write(content)

    admin.avatar = new_filename
    db.commit()

    return GenericResponse(data={"avatar": _get_avatar_url(new_filename)})


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
