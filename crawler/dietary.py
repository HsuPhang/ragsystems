"""国家膳食指南 / 营养膳食数据爬虫。

数据源：
- 中国营养学会 cnsoc.org 公开科普文章
- 卫健委发布的居民膳食指南相关页面

输出：data/raw/dietary/<分类>/<文章>.txt
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
    extract_title,
    fetch,
    normalize_space,
    polite_sleep,
    save_text,
    url_to_filename,
)

ENTRY_URLS = [
    # 中国营养学会 - 科普园地
    "https://www.cnsoc.org/populization/",
    "https://www.cnsoc.org/populization/index.html",
    # 卫健委 - 国民营养计划
    "https://www.nhc.gov.cn/sps/list.shtml",
]

OUT_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw" / "dietary"
MAX_PER_ENTRY = 25


def _entry_to_category_name(entry_url: str) -> str:
    """从入口 URL 提取可读的类别名称。"""
    if "cnsoc.org" in entry_url:
        return "中国营养学会"
    elif "nhc.gov.cn" in entry_url:
        return "国家卫生健康委员会"
    return entry_url


def discover_links_cnsoc(entry_url: str) -> list[str]:
    """cnsoc.org 特定链接发现逻辑。"""
    html = fetch(entry_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.select("a[href]"):
        href = str(a.get("href", ""))
        text = normalize_space(a.get_text())
        if text and len(text) >= 4 and re.search(r"\.html?$", href):
            if href.startswith("http"):
                links.add(href)
            elif href.startswith("/"):
                base = re.match(r"(https?://[^/]+)", entry_url)
                if base:
                    links.add(base.group(1) + href)
    return list(links)


def discover_links_nhc(entry_url: str) -> list[str]:
    """nhc.gov.cn 特定链接发现逻辑。"""
    html = fetch(entry_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.select("a[href]"):
        href = str(a.get("href", ""))
        if re.search(r"/\d{8}/[a-z0-9]+\.shtml", href):
            if href.startswith("http"):
                links.add(href)
            elif href.startswith("/"):
                links.add("https://www.nhc.gov.cn" + href)
    return list(links)


def discover_links(entry_url: str) -> list[str]:
    """根据站点分发到专用的链接发现函数。"""
    if "cnsoc.org" in entry_url:
        return discover_links_cnsoc(entry_url)
    elif "nhc.gov.cn" in entry_url:
        return discover_links_nhc(entry_url)
    return []


def fetch_article(url: str, out_dir: Path, category: str) -> dict | None:
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    title = extract_title(soup)

    pub = ""
    pnode = soup.find(class_="time") or soup.find(class_="date") or soup.find(class_="publish")
    if pnode:
        m = re.search(r"(\d{4})[-年.](\d{1,2})[-月.](\d{1,2})", pnode.get_text())
        if m:
            pub = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    body = extract_main_text(html)
    if len(body) < 100:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    fname = url_to_filename(url, "txt")
    header = (
        f"标题: {title}\n"
        f"来源: {category}\n"
        f"URL: {url}\n"
        f"发布时间: {pub or '未知'}\n"
        f"分类: 膳食营养\n"
        f"抓取时间: {datetime.now().isoformat(timespec='seconds')}\n"
        f"\n{'-' * 40}\n\n"
    )
    save_text(out_dir / fname, header + body)
    return {"title": title, "url": url, "length": len(body)}


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    grand = 0
    for entry in ENTRY_URLS:
        print(f"▶ 入口: {entry}")
        try:
            links = discover_links(entry)
        except Exception as e:
            print(f"  ✗ {e}")
            continue
        print(f"  发现 {len(links)} 个候选链接")
        sub = re.search(r"://[^/]+/([^/]+)/?", entry)
        sub_name = sub.group(1) if sub else "misc"
        out_dir = OUT_ROOT / sub_name
        for url in links[:MAX_PER_ENTRY]:
            try:
                info = fetch_article(url, out_dir, category=_entry_to_category_name(entry))
                if info:
                    grand += 1
                    print(f"  ✔ {info['title'][:30]} ({info['length']}字)")
            except Exception as e:
                print(f"  ✗ {url}: {e}")
            polite_sleep(1.0)
        polite_sleep(2.0)
    print(f"\n✔ 共抓取 {grand} 篇膳食营养文章 → {OUT_ROOT}")


if __name__ == "__main__":
    main()
