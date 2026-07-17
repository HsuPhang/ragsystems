"""项目入口：python main.py  启动 FastAPI 服务。

使用 uvicorn 编程式启动，等价于：
    uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

from app.config import settings
from app.utils import setup_logger


def main() -> None:
    setup_logger()
    uvicorn.run(
        "app.api:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
