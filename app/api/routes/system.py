"""系统配置接口：前端动态获取全局配置、导航菜单、最近会话等。"""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import decode_token, get_current_admin_or_none, oauth2_scheme
from app.api.schemas import GenericResponse
from app.db import Admin, ChatSession, SystemConfig, User, get_db

router = APIRouter(prefix="/api/system", tags=["系统配置"])


def _get_db_config(db: Session) -> dict:
    """从 system_config 表中读取配置字典。"""
    rows = db.query(SystemConfig).all()
    return {r.key: r.value for r in rows}


def _guess_user_name(token: str | None) -> str | None:
    """如果提供了有效的 JWT，返回用户名，否则返回 None。"""
    if not token:
        return None
    payload = decode_token(token)
    if payload and "sub" in payload:
        return payload["sub"]
    return None


def _parse_json_config(db_cfg: dict, key: str, default: Any = None) -> Any:
    """从 DB 配置中读取 JSON 值，解析失败时返回默认值。"""
    val = db_cfg.get(key)
    if val is None:
        return default
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default
    return val


@router.get("/config", response_model=GenericResponse)
def system_config(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> GenericResponse:
    """返回前端所需的全局配置（动态读取 DB + JWT 上下文）。"""
    db_cfg = _get_db_config(db)
    user_name = _guess_user_name(token) or db_cfg.get("default_user_name", "医生")
    app_name = db_cfg.get("app_name", "知康")

    nav_items = _parse_json_config(db_cfg, "nav_items") or [
        {"label": "探索", "icon": "circle.grid.2x2.svg", "route": "/collections"},
    ]
    sections = _parse_json_config(db_cfg, "sections") or [
        {
            "title": "笔记本",
            "items": [
                {"label": "新建笔记", "icon": "pencil.and.outline.svg", "route": "/notes/new"},
            ],
        }
    ]

    return GenericResponse(data={
        "appName": app_name,
        "userName": user_name,
        "shortcutText": db_cfg.get("shortcut_text", "Ctrl+Shift+O"),
        "searchPlaceholder": db_cfg.get("search_placeholder", "输入您的问题"),
        "extensionLabel": db_cfg.get("extension_label", "DeepSeek-V4-Flash"),
        "welcomeMessage": f"{user_name}，接下来想查点什么？",
        "navItems": nav_items,
        "sections": sections,
    })


@router.get("/sessions", response_model=GenericResponse)
def recent_sessions(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20,
) -> GenericResponse:
    """返回当前登录用户的最近聊天会话列表。未登录返回空列表。"""
    owner_id = None
    owner_type = None
    if token:
        payload = decode_token(token)
        if payload and "sub" in payload:
            role = payload.get("role")
            if role == "user":
                user = db.query(User).filter(User.username == payload["sub"]).first()
                if user:
                    owner_id = user.id
                    owner_type = "user"
            elif role == "admin":
                admin = db.query(Admin).filter(Admin.username == payload["sub"]).first()
                if admin:
                    owner_id = admin.id
                    owner_type = "admin"

    if owner_id is None:
        return GenericResponse(data=[])

    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == owner_id, ChatSession.user_type == owner_type)
        .order_by(ChatSession.created_at.desc())
        .limit(min(limit, 50))
        .all()
    )
    items = [
        {
            "id": s.session_id,
            "title": s.title,
            "created_at": s.created_at.isoformat(timespec="seconds"),
        }
        for s in rows
    ]
    return GenericResponse(data=items)
