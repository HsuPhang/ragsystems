"""Pydantic Schemas：API 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ===== 聊天 =====

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = None
    use_rerank: bool = True
    top_k: int | None = None
    category: str | None = None  # 按分类过滤


class SourceItem(BaseModel):
    index: int
    source: str
    category: str = ""
    author: str = ""
    update_time: str = ""
    url: str = ""
    chunk_id: str = ""
    score: float
    preview: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = []
    top_score: float
    used_rerank: bool
    rejected: bool
    session_id: str


# ===== 管理员登录 =====

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# ===== 文档管理 =====

class DocumentItem(BaseModel):
    id: int
    doc_id: str
    title: str
    source: str
    category: str
    author: str
    file_type: str
    file_size: int
    chunk_count: int
    keywords: list[str] = []
    status: str
    created_at: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentItem]


class DocumentUpdateRequest(BaseModel):
    title: str | None = None
    source: str | None = None
    category: str | None = None
    author: str | None = None
    keywords: list[str] | None = None


# ===== 统计 =====

class StatsResponse(BaseModel):
    document_total: int
    chunk_total: int
    chat_session_total: int
    chat_message_total: int
    admin_total: int


# ===== 通用 =====

class GenericResponse(BaseModel):
    success: bool = True
    message: str = "ok"
    data: Any | None = None
