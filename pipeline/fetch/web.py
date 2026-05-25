"""公版书库抓取：Project Gutenberg → Internet Archive → Wikisource (中文)。

策略:
1. Gutendex API (https://gutendex.com) 按书名搜索 Gutenberg
2. 找不到 → 询问 Internet Archive (advancedsearch.php，过滤 mediatype:texts，prefer plain text)
3. 找不到 → 询问 Wikisource zh (中文经典)
4. 都没有 → 抛 LookupError，由调用方决定是否走 fallback
"""

from __future__ import annotations

import urllib.parse
import urllib.request
import json
import re
from typing import Any


USER_AGENT = "book2mindmap/0.1 (educational; contact: local user)"
TIMEOUT = 30


class NotFoundInPublicDomain(LookupError):
    """所有公版渠道都未找到该书。"""


def fetch_full_text(book_title: str) -> tuple[str, dict[str, Any]]:
    """尝试从公版书库取全文 → (text, metadata)。

    metadata: {channel, source_url, title, author, format}
    """
    errors: list[str] = []

    try:
        return _try_gutenberg(book_title)
    except LookupError as e:
        errors.append(f"Gutenberg: {e}")

    try:
        return _try_archive_org(book_title)
    except LookupError as e:
        errors.append(f"Internet Archive: {e}")

    try:
        return _try_wikisource_zh(book_title)
    except LookupError as e:
        errors.append(f"Wikisource zh: {e}")

    raise NotFoundInPublicDomain(
        "所有公版渠道都未找到全文：\n  - " + "\n  - ".join(errors)
    )


def _http_get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _try_gutenberg(book_title: str) -> tuple[str, dict[str, Any]]:
    api = f"https://gutendex.com/books?search={urllib.parse.quote(book_title)}"
    data = json.loads(_http_get(api, accept="application/json"))
    results = data.get("results", [])
    if not results:
        raise LookupError(f"Gutendex 无结果：{book_title}")

    best = results[0]
    formats: dict[str, str] = best.get("formats", {})

    plain_url = None
    for mime, url in formats.items():
        if mime.startswith("text/plain") and "utf-8" in mime.lower():
            plain_url = url
            break
    if not plain_url:
        for mime, url in formats.items():
            if mime.startswith("text/plain"):
                plain_url = url
                break
    if not plain_url:
        raise LookupError(f"Gutendex 找到《{best.get('title')}》但无 plain text 格式")

    raw = _http_get(plain_url)
    for enc in ("utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    text = _strip_gutenberg_boilerplate(text)
    authors = best.get("authors", [])
    return text, {
        "channel": "project_gutenberg",
        "source_url": plain_url,
        "title": best.get("title"),
        "author": ", ".join(a.get("name", "") for a in authors) or None,
        "format": "txt",
        "gutenberg_id": best.get("id"),
    }


def _strip_gutenberg_boilerplate(text: str) -> str:
    start_re = re.compile(r"\*{3}\s*START OF (?:THE|THIS)? PROJECT GUTENBERG.*?\*{3}", re.IGNORECASE)
    end_re = re.compile(r"\*{3}\s*END OF (?:THE|THIS)? PROJECT GUTENBERG.*?\*{3}", re.IGNORECASE)
    s = start_re.search(text)
    e = end_re.search(text)
    body = text[s.end():e.start()] if s and e else text[s.end():] if s else text[:e.start()] if e else text
    return body.strip()


def _try_archive_org(book_title: str) -> tuple[str, dict[str, Any]]:
    """Internet Archive 优先取 *_djvu.txt（OCR 文本）。"""
    query = f'title:("{book_title}") AND mediatype:texts AND format:"DjVuTXT"'
    api = (
        "https://archive.org/advancedsearch.php?"
        + urllib.parse.urlencode({
            "q": query,
            "fl[]": "identifier,title,creator",
            "rows": 5,
            "page": 1,
            "output": "json",
        })
    )
    data = json.loads(_http_get(api, accept="application/json"))
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        raise LookupError(f"Internet Archive 无 DjVuTXT 结果：{book_title}")

    item = docs[0]
    identifier = item["identifier"]
    txt_url = f"https://archive.org/download/{identifier}/{identifier}_djvu.txt"
    try:
        raw = _http_get(txt_url)
    except Exception as e:
        raise LookupError(f"找到 {identifier} 但下载 djvu txt 失败: {e}")

    text = raw.decode("utf-8", errors="replace")
    return text, {
        "channel": "internet_archive",
        "source_url": txt_url,
        "title": item.get("title"),
        "author": item.get("creator"),
        "format": "txt",
        "archive_id": identifier,
    }


def _try_wikisource_zh(book_title: str) -> tuple[str, dict[str, Any]]:
    api = (
        "https://zh.wikisource.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": book_title,
            "srlimit": 5,
        })
    )
    data = json.loads(_http_get(api, accept="application/json"))
    hits = data.get("query", {}).get("search", [])
    if not hits:
        raise LookupError(f"Wikisource 中文无结果：{book_title}")

    title = hits[0]["title"]
    extract_api = (
        "https://zh.wikisource.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "explaintext": "1",
            "titles": title,
        })
    )
    raw = _http_get(extract_api, accept="application/json")
    pages = json.loads(raw).get("query", {}).get("pages", {})
    text = ""
    for _, page in pages.items():
        text = page.get("extract", "") or ""
        break
    if len(text) < 1000:
        raise LookupError(f"Wikisource 找到《{title}》但 extract 过短 ({len(text)} 字)，可能是目录页")
    page_url = f"https://zh.wikisource.org/wiki/{urllib.parse.quote(title)}"
    return text, {
        "channel": "wikisource_zh",
        "source_url": page_url,
        "title": title,
        "author": None,
        "format": "txt",
    }
