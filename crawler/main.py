"""统一爬虫入口：依次运行所有可用的官方医疗科普爬虫。

运行方式：
  python crawler/main.py              # 运行所有爬虫
  python crawler/main.py --dry-run    # 仅打印将要运行的爬虫，不实际执行
  python crawler/main.py chinacdc     # 只运行指定的爬虫

支持的爬虫：
  chinacdc   中国疾病预防控制中心 — 健康提示、健康科普
  cma        中华医学会 — 科普与健康
  healthchina 健康中国(中国网) — 健康科普、健康资讯、中医养生、营养健康
  nhc        国家卫生健康委员会 (⚠️ 当前被 WAF 拦截，无法运行)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils import setup_logger
from crawler.utils import polite_sleep

# 爬虫注册表：name -> (module_path, description, available)
CRAWLERS = {
    "chinacdc": {
        "module": "crawler.chinacdc",
        "description": "中国疾病预防控制中心 — 健康提示、健康科普",
        "available": True,
    },
    "cma": {
        "module": "crawler.cma",
        "description": "中华医学会 — 科普与健康",
        "available": True,
    },
    "healthchina": {
        "module": "crawler.healthchina",
        "description": "健康中国(中国网) — 健康科普、资讯、中医养生",
        "available": True,
    },
    "nhc": {
        "module": "crawler.nhc",
        "description": "国家卫生健康委员会 (WAF 拦截，需浏览器自动化)",
        "available": False,  # WAF blocked
    },
}


def run_crawler(name: str) -> bool:
    """运行单个爬虫。"""
    info = CRAWLERS.get(name)
    if not info:
        print(f"[FAIL] 未知爬虫: {name}，可用爬虫: {', '.join(CRAWLERS.keys())}")
        return False

    if not info["available"]:
        print(f"  [SKIP] {name}: {info['description']}")
        return False

    print(f"\n{'=' * 60}")
    print(f">> 运行爬虫: {name} - {info['description']}")
    print(f"{'=' * 60}")

    try:
        import importlib

        mod = importlib.import_module(info["module"])
        mod.main()
        return True
    except Exception as e:
        print(f"  [FAIL] {name} 运行失败: {e}")
        return False


def dry_run(crawler_names: list[str] | None = None) -> None:
    """仅打印将要运行的爬虫列表。"""
    names = crawler_names or list(CRAWLERS.keys())
    print(f"\n{'=' * 60}")
    print("Dry-run 模式 — 以下爬虫将被运行：")
    print(f"{'=' * 60}")
    for name in names:
        info = CRAWLERS.get(name)
        if not info:
            print(f"  [WARN] 未知爬虫: {name}")
            continue
        status = "[OK]" if info["available"] else "[SKIP]"
        print(f"  {status} {name:12s} - {info['description']}")
    print()


def main() -> None:
    setup_logger()

    args = sys.argv[1:]

    # 如果指定了爬虫名，只运行指定的
    specified = [a for a in args if a in CRAWLERS]

    if "--dry-run" in args:
        dry_run(specified if specified else None)
        return

    if specified:
        crawler_names = specified
    else:
        crawler_names = list(CRAWLERS.keys())

    print("=" * 60)
    print(f"  医疗科普 RAG — 官方数据爬虫")
    print(f"  共 {len(crawler_names)} 个爬虫任务")
    print("=" * 60)

    success = 0
    failed = 0
    skipped = 0

    try:
        for name in crawler_names:
            polite_sleep(1.0)  # 爬虫间间隔
            result = run_crawler(name)
            if result:
                success += 1
            elif CRAWLERS.get(name, {}).get("available", True) is False:
                skipped += 1
            else:
                failed += 1
    except KeyboardInterrupt:
        print("\n\n[!] 用户中断，正在退出...")
        return

    print(f"\n  全部完成！成功: {success}, 失败: {failed}, 跳过: {skipped}")
    print(f"  数据目录: {Path(__file__).resolve().parent.parent / 'data' / 'raw'}")
    print(f"{'=' * 60}")
    print(f"\n提示: 运行 `python scripts/build_index.py` 将抓取的数据索引到知识库")


if __name__ == "__main__":
    main()
