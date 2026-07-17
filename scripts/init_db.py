"""初始化 MySQL：建库 + 建表 + 默认管理员。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.auth import hash_password
from app.config import settings
from app.db import Admin, create_database_if_not_exists, init_db, session_scope
from app.utils import setup_logger


def main() -> None:
    setup_logger()
    print("▶ 创建数据库（若不存在）…")
    create_database_if_not_exists()
    print("▶ 创建表结构…")
    init_db()
    print("▶ 创建默认管理员…")
    with session_scope() as s:
        if not s.query(Admin).filter(Admin.username == settings.ADMIN_USERNAME).first():
            s.add(Admin(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
            ))
            print(f"  已创建默认管理员: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
        else:
            print(f"  管理员 {settings.ADMIN_USERNAME} 已存在，跳过")
    print("✔ MySQL 初始化完成")


if __name__ == "__main__":
    main()
