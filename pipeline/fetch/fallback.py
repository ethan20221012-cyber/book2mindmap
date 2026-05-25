"""Fallback: 当用户选 web 但公版书库没找到全文时，退回到双引擎搜索摘要。

复用旧 search.py 的"生成请求文件让 Claude Code 执行搜索"模式。
"""

from __future__ import annotations

from ..common import cache_dir, write_text


SEARCH_REQUEST_TEMPLATE = """# Stage 1 (Fallback) — 网络搜索请求

> 由 book2mindmap 自动生成。**公版书库未找到全文**，本次以网络二手资料构建笔记。
> 请用 bing-search + tavily 双引擎对下面这本书做搜索，把结果整合写到 `search.json`。

## 书名
{book_title}

## 任务

1. **bing-search**：搜索关键词组合
   - `{book_title} 章节 目录`
   - `{book_title} 主要内容 简介`
   - `{book_title} 核心观点 评价`
   - 取前 10 条结果

2. **tavily-research**: input = `《{book_title}》这本书的章节目录、核心论点、主要内容、读者评价是什么？`

3. 把结果写入 `cache/{slug}/search.json`：

```json
{{
  "book_title": "{book_title}",
  "engine_a": {{
    "name": "bing-search",
    "queries": ["..."],
    "results": [{{"title": "...", "url": "...", "snippet": "..."}}]
  }},
  "engine_b": {{
    "name": "tavily-research",
    "query": "...",
    "answer": "...",
    "results": [{{"title": "...", "url": "...", "content": "..."}}]
  }}
}}
```

## 完成后

继续：`python book2mindmap.py "{book_title}" --stage outline`

## 重要：本次为 fallback 模式

后续生成的笔记必须在头部标注「**仅依据网络二手资料整理，未直接阅读全文**」。
"""


def write_request(book_title: str, slug: str) -> str:
    cdir = cache_dir(slug)
    path = cdir / "_search_request.md"
    write_text(path, SEARCH_REQUEST_TEMPLATE.format(book_title=book_title, slug=slug))
    return str(path)
