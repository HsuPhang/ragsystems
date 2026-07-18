"""中国疾病预防控制中心 (chinacdc.cn) 健康科普爬虫。

数据源：
- 健康提示 /jkts/ — 疾病预防、健康风险提示、疫苗接种等
- 健康科普 /jkkp/ — 健康科普知识（部分内容依赖 JS 渲染）

输出：data/raw/chinacdc/<栏目>/<文章>.txt
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup

from crawler.utils import (
    extract_main_text,
    fetch,
    normalize_space,
    polite_sleep,
    save_text,
    url_to_filename,
)

BASE = "https://www.chinacdc.cn"

# 栏目配置：URL 后缀、最大页数、每页最多文章数
SECTIONS = [
    {
        "name": "健康提示",
        "list_url": "/jkts/",
        "max_pages": 10,
        "max_articles": 100,
    },
    {
        "name": "健康科普",
        "list_url": "/jkkp/",
        "max_pages": 5,
        "max_articles": 50,
    },
]

OUT_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw" / "chinacdc"

# 日期模式: ./202607/t20260711_1838083.html
ARTICLE_PATTERN = re.compile(r"\./(20\d{2})/t(\d{8})_\d+\.html")


def discover_article_links(list_url: str, max_pages: int) -> list[str]:
    """遍历列表页（含分页），收集所有文章链接。"""
    all_links: set[str] = set()

    for page_idx in range(max_pages):
        if page_idx == 0:
            url = f"{BASE}{list_url}"
        else:
            # 分页格式: index_1.html, index_2.html ...
            url = f"{BASE}{list_url}index_{page_idx}.html"

        html = fetch(url)
        if not html:
            if page_idx > 0:
                break  # 后续页不存在则退出
            continue

        soup = BeautifulSoup(html, "lxml")
        found = 0
        for a in soup.find_all("a", href=True):
            href = str(a.get("href", ""))
            m = ARTICLE_PATTERN.search(href)
            if m:
                # 解析相对路径
                article_url = f"{BASE}{list_url}{m.group(0).removeprefix('./')}"
                if article_url not in all_links:
                    all_links.add(article_url)
                    found += 1

        if found == 0:
            print(f"  第 {page_idx+1} 页无文章链接，停止翻页")
            break  # 该页无文章，不再翻页

        polite_sleep(1.0)

    return list(all_links)


def fetch_article(url: str, out_dir: Path, section_name: str) -> dict | None:
    """抓取单篇文章并写入文件。"""
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    # 标题
    title = ""
    for tag in ("h1", "h2", "h3"):
        el = soup.find(tag)
        if el and len(el.get_text(strip=True)) > 4:
            title = normalize_space(el.get_text())
            break
    if not title:
        title = normalize_space(soup.title.get_text() if soup.title else "")

    # 发布日期（从 URL 中提取 t20260711 格式）
    publish_date = ""
    um = re.search(r"t(\d{4})(\d{2})(\d{2})_", url)
    if um:
        publish_date = f"{um.group(1)}-{um.group(2)}-{um.group(3)}"

    # 正文
    body = extract_main_text(html)
    # 过滤太短的内容
    if len(body) < 100:
        return None

    # 保存
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = url_to_filename(url, "txt")
    header = (
        f"标题: {title}\n"
        f"来源: 中国疾病预防控制中心\n"
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
    print("中国疾病预防控制中心 健康科普爬虫")
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
