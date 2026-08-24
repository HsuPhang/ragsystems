"""国家卫生健康委员会 (nhc.gov.cn) 科普文章爬虫。

[重要提示]
   NHC 网站目前部署了 WAF（Web 应用防火墙），对大部分路径返回 HTTP 412，
   普通 HTTP 请求（含 httpx、cloudscraper）无法绕过。
   如需爬取 NHC 数据，建议使用 Selenium/Playwright 等浏览器自动化工具，
   或通过 NHC 官方提供的 RSS/API 接口获取。

爬取目标（当 WAF 可用时）：
- 科普知识栏目
- 健康知识 / 卫生科普 / 公众健康等子栏目

输出：data/raw/nhc/<分类>/<文章>.txt
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

# 卫健委科普相关栏目入口（按公开页面整理）
ENTRY_URLS = [
    # 健康知识
    "https://www.nhc.gov.cn/wjw/jkp/list.shtml",
    "https://www.nhc.gov.cn/qjjks/list.shtml",
    # 公众健康
    "https://www.nhc.gov.cn/zhjc/list.shtml",
]

OUT_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw" / "nhc"

# 单个栏目最多抓取的页数（防失控）
MAX_PAGES_PER_ENTRY = 5
# 每个入口最多抓取文章数
MAX_ARTICLES_PER_ENTRY = 30


def discover_article_links(
    entry_url: str, max_pages: int = MAX_PAGES_PER_ENTRY
) -> list[str]:
    """在列表页发现文章链接（支持分页）。"""
    all_links: set[str] = set()

    for page in range(max_pages):
        if page == 0:
            url = entry_url
        else:
            # 分页格式: list.shtml → list_2.shtml, list_3.shtml ...
            url = re.sub(r"(\.[^.]+)$", f"_{page + 1}\\1", entry_url)

        html = fetch(url)
        if not html:
            if page > 0:
                break
            continue

        soup = BeautifulSoup(html, "lxml")
        found = 0
        for a in soup.select("a[href]"):
            href = str(a.get("href", ""))
            if not href:
                continue
            # 卫健委文章 URL 通常形如 /wjw/jkp/yyyymmdd/xxx.shtml
            if re.search(r"/\d{8}/[a-z0-9]+\.shtml", href):
                if href.startswith("http"):
                    if href not in all_links:
                        all_links.add(href)
                        found += 1
                elif href.startswith("/"):
                    full = urljoin(entry_url, href)
                    if full not in all_links:
                        all_links.add(full)
                        found += 1

        if found == 0:
            print(f"  第 {page+1} 页无更多文章，停止翻页")
            break

        polite_sleep(1.0)

    return list(all_links)


def fetch_article(url: str, out_dir: Path) -> dict | None:
    """抓取单篇文章并落盘。"""
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    # 标题（og:title → 文章专用选择器 → h1 → <title>，避免误抓栏目名/导航词）
    title = extract_title(soup)

    # 发布时间（粗略）
    publish_date = ""
    pub = soup.find(class_="time") or soup.find(class_="date")
    if pub:
        m = re.search(r"(\d{4})[-年.](\d{1,2})[-月.](\d{1,2})", pub.get_text())
        if m:
            publish_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 正文
    body = extract_main_text(html)
    if len(body) < 80:
        return None

    # 保存
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = url_to_filename(url, "txt")
    header = (
        f"标题: {title}\n"
        f"来源: 国家卫生健康委员会\n"
        f"URL: {url}\n"
        f"发布时间: {publish_date or '未知'}\n"
        f"分类: 健康科普\n"
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


def crawl_one_entry(entry_url: str) -> int:
    print(f"▶ 入口: {entry_url}")
    name = re.search(r"\.gov\.cn/([^/]+)/", entry_url)
    sub = name.group(1) if name else "misc"
    out_dir = OUT_ROOT / sub

    total = 0
    article_links = discover_article_links(entry_url)
    print(f"  发现 {len(article_links)} 篇文章链接")

    for url in article_links[:MAX_ARTICLES_PER_ENTRY]:
        info = fetch_article(url, out_dir)
        if info:
            total += 1
            print(f"  ✔ {info['title'][:30]}  ({info['length']}字)")
        polite_sleep(1.0)
    return total


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    grand = 0
    for entry in ENTRY_URLS:
        try:
            grand += crawl_one_entry(entry)
        except Exception as e:
            print(f"✗ {entry}: {e}")
        polite_sleep(2.0)
    print(f"\n✔ 共抓取 {grand} 篇卫健委文章 → {OUT_ROOT}")


if __name__ == "__main__":
    main()
