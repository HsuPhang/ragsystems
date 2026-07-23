"""通用工具：日志、哈希、ID生成、设备检测。"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from loguru import logger

from app.config import settings


def detect_device(preferred_device: str = "") -> str:
    """自动检测可用设备（CUDA / MPS / CPU）。

    优先级：
    1. 用户显式指定的设备（如 "cuda:0", "mps", "cpu", "gpu"）
    2. CUDA（NVIDIA GPU）
    3. MPS（Apple Silicon GPU）
    4. CPU（兜底）

    Args:
        preferred_device: 用户指定的设备，为空则自动检测

    Returns:
        检测到的设备字符串（如 "cuda", "mps", "cpu"）
    """
    if preferred_device and preferred_device.lower() != "auto":
        device_map = {
            "gpu": "cuda",
            "nvidia": "cuda",
        }
        return device_map.get(preferred_device.lower(), preferred_device)

    try:
        import torch

        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"检测到 CUDA 设备: {device_count} 个, 第1个: {device_name}")
            return "cuda"
    except ImportError:
        pass

    try:
        import torch

        if torch.backends.mps.is_available():
            logger.info("检测到 MPS 设备 (Apple Silicon)")
            return "mps"
    except (ImportError, AttributeError):
        pass

    logger.info("未检测到 GPU 设备，使用 CPU")
    return "cpu"


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


__all__ = ["logger", "setup_logger", "gen_id", "detect_device"]
