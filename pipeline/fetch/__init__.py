"""Stage 1 入口：根据 --source 决定本地解析 / 网络抓取 / fallback 摘要。

产出物（cache/<slug>/）:
- source.json          — 来源元数据 + 校验报告
- fulltext/raw.txt     — 全文原始（仅 local + web 模式）
- fulltext/chapters/   — 切好的章节 (NN.txt)
- search.json          — 仅 fallback 模式
"""

from __future__ import annotations

from pathlib import Path

from ..common import cache_dir, write_text, write_json
from . import fallback, local, validate, web


def run_local(book_title: str, slug: str, source_file: Path, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    source_path = cdir / "source.json"
    if source_path.exists() and not force:
        return {"status": "cached", "message": f"{source_path} 已存在，--force 可重跑"}

    if not source_file.exists():
        return {"status": "error", "message": f"找不到文件: {source_file}"}

    try:
        full_text, meta = local.extract_full_text(source_file)
    except Exception as exc:
        return {"status": "error", "message": f"解析失败: {exc}"}

    return _persist_fulltext(book_title, slug, full_text, {**meta, "mode": "local"})


def run_web(book_title: str, slug: str, allow_fallback: bool, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    source_path = cdir / "source.json"
    if source_path.exists() and not force:
        return {"status": "cached", "message": f"{source_path} 已存在，--force 可重跑"}

    try:
        full_text, meta = web.fetch_full_text(book_title)
    except web.NotFoundInPublicDomain as exc:
        if not allow_fallback:
            return {
                "status": "error",
                "message": f"公版书库未找到《{book_title}》全文，且已禁用 fallback：\n{exc}",
            }
        request_path = fallback.write_request(book_title, slug)
        write_json(source_path, {
            "mode": "fallback_summary",
            "book_title": book_title,
            "reason": str(exc),
        })
        return {
            "status": "request_written",
            "message": (
                f"公版书库未找到全文，已退到 fallback 模式。\n"
                f"请按 {request_path} 完成搜索后写回 search.json，"
                f"然后运行：python book2mindmap.py \"{book_title}\" --stage outline"
            ),
            "request_path": request_path,
        }
    except Exception as exc:
        return {"status": "error", "message": f"web 抓取失败: {exc}"}

    return _persist_fulltext(book_title, slug, full_text, {**meta, "mode": "web"})


def _persist_fulltext(book_title: str, slug: str, full_text: str, meta: dict) -> dict:
    cdir = cache_dir(slug)
    fulltext_dir = cdir / "fulltext"
    chapters_dir = fulltext_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    raw_path = fulltext_dir / "raw.txt"
    write_text(raw_path, full_text)

    chapters, strategy = validate.split_chapters(full_text)
    validation = validate.validate(full_text, chapters)

    for ch in chapters:
        path = chapters_dir / f"{ch.index:02d}.txt"
        write_text(path, f"# {ch.title}\n\n{ch.body}")

    source_payload = {
        "book_title": book_title,
        "mode": meta.get("mode"),
        "channel": meta.get("channel"),
        "source_url": meta.get("source_url"),
        "source_file": meta.get("source_file"),
        "format": meta.get("format"),
        "title_in_source": meta.get("title"),
        "author": meta.get("author"),
        "raw_path": str(raw_path),
        "chapter_strategy": strategy,
        "chapters": [
            {"index": c.index, "title": c.title, "char_count": len(c.body)}
            for c in chapters
        ],
        "validation": validate.validation_to_dict(validation),
    }
    write_json(cdir / "source.json", source_payload)

    msg = (
        f"全文获取成功（{meta.get('mode')} / {meta.get('channel') or meta.get('format')}）\n"
        f"  字数 {validation.word_count}，章节 {validation.chapter_count}"
        f"（策略 {strategy}），confidence={validation.confidence}"
    )
    if validation.issues:
        msg += "\n  问题:\n    - " + "\n    - ".join(validation.issues)

    return {
        "status": "ok",
        "message": msg,
        "validation": validate.validation_to_dict(validation),
        "source": source_payload,
    }
