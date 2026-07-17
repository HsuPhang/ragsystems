"""全局配置：从 .env 加载，使用 pydantic-settings 强类型校验。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """系统全局配置。"""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===== LLM =====
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # ===== Embedding =====
    EMBEDDING_MODEL_PATH: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIM: int = 1024

    # ===== Reranker =====
    RERANKER_MODEL_PATH: str = "BAAI/bge-reranker-large"
    RERANKER_DEVICE: str = "cpu"
    RERANK_TOP_N: int = 5

    # ===== Retrieval =====
    RETRIEVAL_TOP_K: int = 10
    SIMILARITY_THRESHOLD: float = 0.6

    # ===== Chunk =====
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    # ===== MySQL =====
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DB: str = "medical_rag"

    # ===== Admin =====
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    JWT_SECRET: str = "please-change-me-in-production"
    JWT_EXPIRE_MINUTES: int = 720

    # ===== Storage =====
    CHROMA_PERSIST_DIR: str = "./storage/chroma"
    UPLOAD_DIR: str = "./storage/uploads"
    LOG_DIR: str = "./logs"

    # ===== App =====
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ===== 派生属性 =====
    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    def resolve(self, key: str) -> Path:
        """把相对路径配置解析为绝对路径。"""
        p = Path(getattr(self, key))
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
