"""从 data/raw 目录构建 Chroma 索引。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.preprocess import build_nodes_from_dir
from app.core.vector_store import add_nodes, reset_collection
from app.utils import setup_logger


def main() -> None:
    setup_logger()
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    if not raw_dir.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f"!! 数据目录为空: {raw_dir}，请先放入文档")
        return

    print(f">> 从 {raw_dir} 加载并分块...")
    nodes = build_nodes_from_dir(raw_dir)
    if not nodes:
        print("!! 无可用 chunk，索引未更新")
        return

    print(">> 重置 Chroma collection...")
    reset_collection()

    print(f">> 写入 Chroma（{settings.CHROMA_PERSIST_DIR}）...")
    add_nodes(nodes)
    print(f">> 完成：{len(nodes)} 个 chunk 已索引")


if __name__ == "__main__":
    main()
