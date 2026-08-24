"""健康中国 (health.china.com.cn) 健康科普爬虫。

数据源：中国网-健康中国频道
- 健康科普 /node_1017657.html  — 医学科普、疾病预防、健康生活
- 健康资讯 /node_1017656.html  — 医疗政策、行业动态
- 中医养生 /node_1017659.html  — 中医药科普
- 营养健康 /node_1017664.html  — 膳食营养

注意：该站仅支持 HTTP（HTTPS 会重定向到 HTTP）。
输出：data/raw/healthchina/<栏目>/<文章>.txt
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

# 注意：必须使用 http://，该站 HTTPS 不可用
BASE = "http://health.china.com.cn"

SECTIONS = [
    {
        "name": "健康科普",
        "list_url": "/node_1017657.html",
        "max_pages": 10,
        "max_articles": 100,
    },
    {
        "name": "健康资讯",
        "list_url": "/node_1017656.html",
        "max_pages": 10,
        "max_articles": 100,
    },
    {
        "name": "中医养生",
        "list_url": "/node_1017659.html",
        "max_pages": 10,
        "max_articles": 100,
    },
    {
        "name": "营养健康",
        "list_url": "/node_1017664.html",
        "max_pages": 10,
        "max_articles": 100,
    },
]

OUT_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw" / "healthchina"

# 文章 URL 模式: /2026-06/15/content_43447865.shtml
ARTICLE_PATTERN = re.compile(r"/(20\d{2}-\d{2})/\d{2}/content_\d+\.s?html?")


def _fetch_with_http(url: str, **kwargs) -> str | None:
    """用 HTTP 协议抓取（该站仅支持 HTTP）。"""
    # 确保使用 http://
    http_url = url.replace("https://", "http://", 1)
    return fetch(http_url, **kwargs)


def discover_article_links(section_url: str, max_pages: int) -> list[str]:
    """遍历栏目列表页，收集文章链接。"""
    all_links: set[str] = set()
    base_list = urljoin(BASE, section_url)

    for page_idx in range(max_pages):
        if page_idx == 0:
            url = base_list
        else:
            # 格式: /node_1017657_1.html, /node_1017657_2.html ...
            url = re.sub(
                r"(node_\d+)\.html",
                rf"\g<1>_{page_idx}.html",
                base_list,
            )

        html = _fetch_with_http(url)
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

        if found == 0 and page_idx > 0:
            break

        polite_sleep(1.0)

    return list(all_links)


def fetch_article(url: str, out_dir: Path, section_name: str) -> dict | None:
    """抓取单篇文章并写入文件。"""
    html = _fetch_with_http(url)
    if not html:
        # 尝试用 https
        html = fetch(url.replace("http://", "https://", 1))
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    # 标题（og:title → 文章专用选择器 → h1 → <title>，避免误抓栏目名/导航词）
    title = extract_title(soup)
    # 移除标题尾部已知站点名标记
    title = re.sub(r"\s*[-—|_]\s*(健康中国|中国网).*$", "", title).strip()

    # 发布时间
    publish_date = ""
    for cls in ("time", "date", "publish", "info", "source"):
        el = soup.find(class_=cls)
        if el:
            m = re.search(r"(\d{4})[-年.](\d{1,2})[-月.](\d{1,2})", el.get_text())
            if m:
                publish_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                break
    if not publish_date:
        # 从 URL 提取 /2026-06/15/content_xxx
        um = re.search(r"/(20\d{2})-(\d{2})/(\d{2})/", url)
        if um:
            publish_date = f"{um.group(1)}-{um.group(2)}-{um.group(3)}"

    # 正文
    body = extract_main_text(html)
    if len(body) < 100:
        return None

    # 保存
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = url_to_filename(url, "txt")
    header = (
        f"标题: {title}\n"
        f"来源: 健康中国-中国网\n"
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
    for article_url in article_links[: section["max_articles"]]:
        info = fetch_article(article_url, out_dir, name)
        if info:
            total += 1
            print(f"  ✔ {info['title'][:40]} ({info['length']}字)")
        else:
            print(f"  ✗ 跳过: {article_url}")
        polite_sleep(1.2)

    print(f"  ✔ {name} 完成：共 {total} 篇文章")
    return total


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    print("=" * 50)
    print("健康中国 (health.china.com.cn) 爬虫")
    print("=" * 50)
    print("注意：该站仅支持 HTTP 协议")

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
