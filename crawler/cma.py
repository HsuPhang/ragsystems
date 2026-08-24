"""中华医学会 (cma.org.cn) 科普文章爬虫。

数据源：
- 科普与健康栏目 /col/col12/  — 面向公众的医学科普文章
- 其他科普子栏目

输出：data/raw/cma/<栏目>/<文章>.txt
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup

from crawler.utils import (
    extract_main_text,
    extract_title,
    fetch,
    normalize_space,
    polite_sleep,
    save_text,
    url_to_filename,
)

BASE = "https://www.cma.org.cn"

# 栏目配置：栏目名、URL 后缀、最大页数、每页最多文章数
SECTIONS = [
    {
        "name": "科普与健康",
        "list_url": "/col/col12/index.html",
        "max_pages": 20,
        "max_articles": 200,
    },
]

OUT_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw" / "cma"

# 文章 URL 模式: /art/2026/4/21/art_32_60602.html
ARTICLE_PATTERN = re.compile(r"/art/(20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html)")


def discover_article_links(list_url: str, max_pages: int) -> list[str]:
    """遍历栏目列表页（含分页），收集文章链接。"""
    all_links: set[str] = set()

    for page_idx in range(max_pages):
        if page_idx == 0:
            url = urljoin(BASE, list_url)
        else:
            # 分页格式: index.html -> index_1.html -> index_2.html
            # 若该页不存在，fetch 返回 None 即终止翻页
            page_url = re.sub(r"index(_\d+)?\.html", f"index_{page_idx}.html", list_url)
            url = urljoin(BASE, page_url)

        html = fetch(url)
        if not html:
            if page_idx > 0:
                break
            continue

        soup = BeautifulSoup(html, "lxml")
        found = 0
        for a in soup.find_all("a", href=True):
            href = str(a.get("href", ""))
            m = ARTICLE_PATTERN.search(href)
            if m:
                full_url = urljoin(BASE, m.group(0))
                if full_url not in all_links:
                    all_links.add(full_url)
                    found += 1

        if found == 0:
            if page_idx > 0:
                break  # 后续页无文章则退出

        polite_sleep(1.0)

    return list(all_links)


def fetch_article(url: str, out_dir: Path, section_name: str) -> dict | None:
    """抓取单篇文章并写入文件。"""
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    # 标题（og:title → 文章专用选择器 → h1 → <title>，避免误抓栏目名/导航词）
    title = extract_title(soup)

    # 发布时间
    publish_date = ""
    # CMA 页面常用 class
    for cls in ("time", "date", "publish", "info", "source"):
        el = soup.find(class_=cls)
        if el:
            m = re.search(r"(\d{4})[-年.](\d{1,2})[-月.](\d{1,2})", el.get_text())
            if m:
                publish_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                break

    if not publish_date:
        # 从 URL 提取日期
        um = re.search(r"/art/(20\d{2})/(\d{1,2})/(\d{1,2})/", url)
        if um:
            publish_date = f"{um.group(1)}-{int(um.group(2)):02d}-{int(um.group(3)):02d}"

    # 正文
    body = extract_main_text(html)
    if len(body) < 100:
        return None

    # 保存
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = url_to_filename(url, "txt")
    header = (
        f"标题: {title}\n"
        f"来源: 中华医学会\n"
        f"URL: {url}\n"
        f"发布时间: {publish_date or '未知'}\n"
        f"分类: {section_name}\n"
        f"抓取时间: {datetime.now().isoformat(timespec='seconds')}\n"
        f"\n{'-' * 40}\n\n"
    )
    save_text(out_dir / fname, header + body)

    return {
        "title": title,
        "url": url,
        "publish_date": publish_date,
        "length": len(body),
    }


def crawl_section(section: dict) -> int:
    """爬取一个栏目。"""
    name = section["name"]
    print(f"\n▶ 【{name}】 {section['list_url']}")

    article_links = discover_article_links(
        section["list_url"], section["max_pages"]
    )
    print(f"  发现 {len(article_links)} 篇文章链接")

    out_dir = OUT_ROOT / section["name"]
    total = 0
    for url in article_links[: section["max_articles"]]:
        info = fetch_article(url, out_dir, name)
        if info:
            total += 1
            print(f"  ✔ {info['title'][:40]} ({info['length']}字)")
        else:
            print(f"  ✗ 跳过: {url}")
        polite_sleep(1.2)

    print(f"  ✔ {name} 完成：共 {total} 篇文章")
    return total


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    print("=" * 50)
    print("中华医学会 科普文章爬虫")
    print("=" * 50)

    grand = 0
    for section in SECTIONS:
        try:
            grand += crawl_section(section)
        except Exception as e:
            print(f"  ✗ {section['name']} 爬取出错: {e}")
        polite_sleep(2.0)

    print(f"\n{'=' * 50}")
    print(f"✔ 全部完成！共抓取 {grand} 篇文章 → {OUT_ROOT}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
