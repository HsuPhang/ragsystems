"""系统配置接口：前端动态获取全局配置、导航菜单、最近会话等。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import GenericResponse
from app.db import ChatSession, get_db

router = APIRouter(prefix="/api/system", tags=["系统配置"])


@router.get("/config", response_model=GenericResponse)
def system_config() -> GenericResponse:
    """返回前端所需的全局配置。"""
    return GenericResponse(data={
        "appName": "医疗科普 RAG",
        "userName": "医生",
        "shortcutText": "Ctrl+Shift+O",
        "searchPlaceholder": "输入您的问题",
        "extensionLabel": "DeepSeek-V4-Flash",
        "welcomeMessage": "医生，接下来想查点什么？",
        "navItems": [
            {"label": "知识库", "icon": "circle.grid.2x2.svg", "route": "/collections"},
        ],
        "sections": [
            {
                "title": "笔记本",
                "items": [
                    {"label": "新建笔记", "icon": "pencil.and.outline.svg", "route": "/notes/new"},
                ],
            }
        ],
    })


@router.get("/sessions", response_model=GenericResponse)
def recent_sessions(
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20,
) -> GenericResponse:
    """返回最近聊天会话列表，用于侧边栏「最近」区域。"""
    rows = (
        db.query(ChatSession)
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
