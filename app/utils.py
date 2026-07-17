"""通用工具：日志、哈希、ID生成。"""
from __future__ import annotations

import hashlib
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import settings


def setup_logger() -> None:
    """初始化 loguru 日志：控制台 + 文件双输出。"""
    settings.resolve("LOG_DIR").mkdir(parents=True, exist_ok=True)
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stdout, format=log_format, level="INFO")
    logger.add(
        settings.resolve("LOG_DIR") / "app_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="100 MB",
        retention="14 days",
        encoding="utf-8",
    )


def gen_id(prefix: str = "") -> str:
    """生成唯一 ID（可选前缀，便于从 ID 识别对象类型）。"""
    raw = uuid.uuid4().hex
    return f"{prefix}_{raw}" if prefix else raw


def text_hash(text: str) -> str:
    """对文本计算 SHA1，用于 chunk / 文档去重。"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """文本规范化：合并空白、去除首尾空白。"""
    if not text:
        return ""
    return _WS_RE.sub(" ", text).strip()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = ["logger", "setup_logger", "gen_id", "text_hash", "normalize_text", "now_iso"]
