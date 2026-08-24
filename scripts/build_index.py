"""从 data/raw 目录构建 Chroma 索引 + 注册文档到 MySQL。

流程：
1. 遍历 data/raw/ 下的所有 .txt 文件，解析元数据头
2. 注册/更新每条文档到 MySQL documents 表
3. 加载、分块
4. 将解析出的元数据（来源/URL/分类）注入到每个 Chroma chunk
5. 剥离 chunk 正文中的冗余元数据头
6. 写入 Chroma
7. 更新 documents 表的 chunk_count
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.preprocess import build_nodes_from_dir
from app.core.vector_store import add_nodes, count, reset_collection
from app.db import Document, session_scope
from app.utils import gen_id, setup_logger


# TXT 文件的元数据头格式（爬虫生成）：
# 标题: xxx
# 来源: xxx
# URL: xxx
# 发布时间: xxxx-xx-xx
# 分类: xxx
# 抓取时间: xxxx-xx-xxTxx:xx:xx
HEADER_PATTERN = re.compile(
    r"标题:\s*(?P<title>.+)\n"
    r"来源:\s*(?P<source>.+)\n"
    r"URL:\s*(?P<url>.+)\n"
    r"发布时间:\s*(?P<update_time>.+)\n"
    r"分类:\s*(?P<category>.+)\n"
)

# 匹配完整元数据头（含抓取时间 + 分隔线），用于剥离 chunk 正文
HEADER_STRIP_PATTERN = re.compile(
    r"标题:.*\r?\n"
    r"来源:.*\r?\n"
    r"URL:.*\r?\n"
    r"发布时间:.*\r?\n"
    r"分类:.*\r?\n"
    r"(?:抓取时间:.*\r?\n)?"
    r"\r?\n?"
    r"-{10,}\s*",
    re.MULTILINE,
)


def parse_txt_header(file_path: Path) -> dict | None:
    """解析 TXT 文件的元数据头。"""
    try:
        content = file_path.read_text("utf-8", errors="ignore")[:2000]
    except Exception:
        return None

    m = HEADER_PATTERN.search(content)
    if not m:
        return None

    return {
        "title": m.group("title").strip(),
        "source": m.group("source").strip(),
        "url": m.group("url").strip(),
        "update_time": m.group("update_time").strip(),
        "category": m.group("category").strip(),
    }


def register_documents(raw_dir: Path) -> dict[str, Path]:
    """将所有 .txt 文件注册到 MySQL documents 表。"""
    txt_files = sorted(raw_dir.rglob("*.txt"))
    if not txt_files:
        print("!! 未找到 .txt 文件")
        return {}

    try:
        with session_scope() as db:
            registered: dict[str, Path] = {}
            total = 0

            for fp in txt_files:
                meta = parse_txt_header(fp)
                if not meta:
                    print(f"  [WARN] 无法解析头信息: {fp.relative_to(raw_dir)}")
                    continue

                # 用 URL + 文件大小作为唯一标识
                doc_id = gen_id("doc")  # 或 hashlib
                file_size = fp.stat().st_size

                # 检查是否已存在（按来源+标题去重）
                existing = (
                    db.query(Document)
                    .filter(
                        Document.source == meta["source"],
                        Document.title == meta["title"],
                    )
                    .first()
                )

                if existing:
                    doc_id = existing.doc_id
                    # 更新文件路径和大小
                    existing.file_path = str(fp)
                    existing.file_size = file_size
                    db.flush()
                    print(f"  [UPDATE] {meta['title'][:40]}")
                else:
                    doc = Document(
                        doc_id=doc_id,
                        title=meta["title"],
                        source=meta["source"],
                        category=meta["category"],
                        author=meta["source"],
                        file_path=str(fp),
                        file_type="txt",
                        file_size=file_size,
                        chunk_count=0,
                        keywords=[],
                        status="active",
                    )
                    db.add(doc)
                    db.flush()
                    total += 1
                    print(f"  [NEW] {meta['title'][:40]}")

                registered[doc_id] = fp

            print(f">> 文档注册完成：新增 {total}，总计 {len(registered)} 篇")
            return registered

    except Exception as e:
        print(f"!! 注册文档失败: {e}")
        return {}


def enrich_nodes_metadata(nodes: list) -> list:
    """将 parse_txt_header 解析出的元数据注入到每个 node 上，并剥离正文中的元数据头。"""
    # 缓存：file_path → parsed_meta，避免对同文件的不同 chunk 重复解析
    meta_cache: dict[str, dict | None] = {}

    for node in nodes:
        fp = node.metadata.get("file_path", "")
        if not fp:
            continue

        fp_resolved = str(Path(fp).resolve())
        if fp_resolved not in meta_cache:
            meta_cache[fp_resolved] = parse_txt_header(Path(fp))

        meta = meta_cache[fp_resolved]
        if meta:
            # 注入解析出的元数据（含标题，供检索结果展示与引用链路使用）
            node.metadata["title"] = meta["title"]
            node.metadata["source"] = meta["source"]
            node.metadata["url"] = meta["url"]
            node.metadata["category"] = meta["category"]
            node.metadata["update_time"] = meta["update_time"]
            # 发布时间统一命名（与 update_time 同值，便于上层按 publish_date 取用）
            node.metadata["publish_date"] = meta["update_time"]
            # 同时设置 author 为来源（与 MySQL 注册保持一致）
            node.metadata.setdefault("author", meta["source"])

            # 剥离 chunk 正文中的元数据头
            text = node.get_content()
            if text:
                cleaned = HEADER_STRIP_PATTERN.sub("", text, count=1).strip()
                if cleaned:
                    node.set_content(cleaned)

    return nodes


def update_chunk_counts(registered: dict[str, Path], nodes: list) -> None:
    """根据 chunk 数量更新 documents 表的 chunk_count。"""
    if not nodes:
        return

    # 预先构建 {resolved_path: doc_id} 映射，避免 O(N*M) 嵌套循环
    resolved_registered = {str(Path(p).resolve()): doc_id for doc_id, p in registered.items()}
    chunk_counts: dict[str, int] = {}
    for node in nodes:
        file_path = node.metadata.get("file_path", "")
        if not file_path:
            continue
        doc_id = resolved_registered.get(str(Path(file_path).resolve()))
        if doc_id:
            chunk_counts[doc_id] = chunk_counts.get(doc_id, 0) + 1

    try:
        with session_scope() as db:
            for doc_id, count in chunk_counts.items():
                doc = db.query(Document).filter(Document.doc_id == doc_id).first()
                if doc:
                    doc.chunk_count = count

        print(f">> 更新 {len(chunk_counts)} 篇文档的 chunk_count")
    except Exception as e:
        print(f"!! 更新 chunk_count 失败: {e}")


def main(rebuild: bool = False) -> None:
    setup_logger()
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    if not raw_dir.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f"!! 数据目录为空: {raw_dir}，请先运行爬虫")
        return

    # 第一步：注册文档到 MySQL
    print("=" * 50)
    print("第一步：注册文档到 MySQL")
    print("=" * 50)
    registered = register_documents(raw_dir)
    if not registered:
        print("!! 无文档可注册，跳过索引")
        return

    # 第二步：构建 Chroma 索引
    print(f"\n{'=' * 50}")
    print("第二步：构建 Chroma 索引")
    print(f"{'=' * 50}")
    print(f">> 从 {raw_dir} 加载并分块...")
    nodes = build_nodes_from_dir(raw_dir)
    if not nodes:
        print("!! 无可用 chunk，索引未更新")
        return

    # 第二步半：将文件元数据头解析并注入到 Chroma 节点，剥离正文中的冗余元数据头
    print(f"\n{'=' * 50}")
    print("第二步半：注入元数据到 Chroma 节点")
    print(f"{'=' * 50}")
    nodes = enrich_nodes_metadata(nodes)
    print(f">> 已为 {len(nodes)} 个 chunk 注入来源/URL/分类等元数据")

    # 检查现有索引数量，决定全量重建或增量更新
    existing_count = count()
    if rebuild:
        print(f">> --rebuild 模式：清空现有 {existing_count} 个 chunk 后全量重建")
        reset_collection()
    elif existing_count > 0:
        print(f">> 检测到现有索引 {existing_count} 个 chunk，执行增量更新")
    else:
        print(">> 初始化新的 Chroma collection...")
        reset_collection()

    print(f">> 写入 Chroma（{settings.CHROMA_PERSIST_DIR}）...")
    add_nodes(nodes)
    print(f">> 完成：{len(nodes)} 个 chunk 已索引")

    # 第三步：更新 chunk_count
    print(f"\n{'=' * 50}")
    print("第三步：更新文档 chunk 计数")
    print(f"{'=' * 50}")
    if registered:
        update_chunk_counts(registered, nodes)

    print(f"\n{'=' * 50}")
    print("[OK] 全部完成！")
    print(f"  - {len(registered)} 篇文档已注册到 MySQL")
    print(f"  - {len(nodes)} 个 chunk 已索引到 Chroma")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="构建 Chroma 索引 + 注册文档到 MySQL")
    parser.add_argument(
        "--rebuild", action="store_true",
        help="全量重建：先清空 collection 再导入（metadata 改动后需用此重建）",
    )
    args = parser.parse_args()
    main(rebuild=args.rebuild)
