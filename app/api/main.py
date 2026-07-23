"""FastAPI 应用入口。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, chat, knowledge, system
from app.api.schemas import GenericResponse
from app.config import settings
from app.utils import logger, setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    logger.info("===== Medical RAG 启动 =====")
    yield
    logger.info("===== Medical RAG 关闭 =====")


app = FastAPI(
    title="医疗科普知识库 RAG 系统",
    description=(
        "基于 Python + LlamaIndex + Chroma + DeepSeek 的医疗科普问答系统。"
        "支持：Top-K 检索 + BGE Rerank + 防幻觉拒答 + 引用来源 + 管理员知识库管理。"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（仅允许前端调试域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.get("/", response_model=GenericResponse)
def root() -> GenericResponse:
    return GenericResponse(
        data={
            "name": "医疗科普知识库 RAG 系统",
            "version": "0.1.0",
            "docs": "/docs",
        }
    )


@app.get("/health", response_model=GenericResponse)
def health() -> GenericResponse:
    return GenericResponse(data={"status": "ok"})


app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(knowledge.router)
app.include_router(system.router)

uploads_dir = settings.resolve("UPLOAD_DIR")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
