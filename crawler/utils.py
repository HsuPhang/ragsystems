"""爬虫通用工具：HTTP 客户端、HTML 解析、限速。"""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.nhc.gov.cn/",
}

_WS_RE = re.compile(r"\s+")


def fetch(url: str, timeout: float = 20.0, retries: int = 3) -> str | None:
    """带重试的 GET。"""
    for i in range(retries):
        try:
            with httpx.Client(
                headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True
            ) as cli:
                r = cli.get(url)
                r.raise_for_status()
                # 卫健委部分页 GBK，需要按编码尝试
                for enc in (r.encoding, "utf-8", "gbk", "gb2312"):
                    if not enc:
                        continue
                    try:
                        html = r.content.decode(enc, errors="ignore")
                        if "�" not in html and "ä¸" not in html:
                            return html
                    except LookupError:
                        continue
                return r.text
        except Exception as e:
            print(f"  [retry {i+1}/{retries}] {url}: {e}")
            time.sleep(2 + i)
    return None


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def normalize_space(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def url_to_filename(url: str, ext: str = "txt") -> str:
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", url)[:40].strip("_") or "page"
    return f"{safe}_{h}.{ext}"


def polite_sleep(seconds: float = 1.5) -> None:
    time.sleep(seconds)


def extract_main_text(html: str) -> str:
    """从 HTML 抽取正文（粗略版：找最大文本块）。"""
    soup = parse_html(html)
    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav"]):
        tag.decompose()

    # 优先尝试文章正文容器
    candidates = [
        soup.find(id="js_content"),
        soup.find(class_="article-content"),
        soup.find(class_="content"),
        soup.find(class_="TRS_Editor"),
        soup.find(id="article-content"),
        soup.find("article"),
        soup.find("main"),
    ]
    container = next((c for c in candidates if c), None)
    if container is None:
        container = soup.body or soup

    paras = [p.get_text(" ", strip=True) for p in container.find_all(["p", "div", "span"])]
    text = "\n".join(p for p in paras if len(p) >= 8)
    text = normalize_space(text)
    return text
