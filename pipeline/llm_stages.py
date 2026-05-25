"""Stage 2/3/4: LLM 阶段调度器。

按 source.json 里的 mode 分流：
- `local` / `web`  → fulltext 模板，上游已读全文
- `fallback_summary` → 走旧的双引擎搜索摘要模板
"""

from __future__ import annotations

from pathlib import Path

from .common import cache_dir, prompt_template, read_json, read_text, write_text


def _stage_skeleton(
    stage_name: str,
    book_title: str,
    slug: str,
    output_filename: str,
    next_stage: str,
    prompt_body: str,
) -> str:
    return f"""# Stage — {stage_name}

> 由 book2mindmap 自动生成。请按下方 prompt 执行 LLM 任务，把产物写入 `cache/{slug}/{output_filename}`。

## Prompt

{prompt_body}

---

## 完成后

1. 把产物写入：`f:/claude_lark_workspace/book2mindmap/cache/{slug}/{output_filename}`
2. 继续下一阶段：`python book2mindmap.py "{book_title}" --stage {next_stage}`
"""


def _resolve_mode(slug: str) -> tuple[str, dict]:
    cdir = cache_dir(slug)
    source_path = cdir / "source.json"
    if not source_path.exists():
        return "missing", {}
    data = read_json(source_path)
    return data.get("mode", "unknown"), data


def run_outline(book_title: str, slug: str, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    outline_path = cdir / "outline.json"
    request_path = cdir / "_outline_request.md"

    if outline_path.exists() and not force:
        return {"status": "cached", "message": f"{outline_path} 已存在，跳过"}

    mode, source = _resolve_mode(slug)
    if mode == "missing":
        return {
            "status": "blocked",
            "message": f"找不到 source.json，请先跑 --stage fetch",
        }

    if mode in ("local", "web"):
        return _outline_from_fulltext(book_title, slug, source, request_path)
    if mode == "fallback_summary":
        return _outline_from_summary(book_title, slug, request_path)
    return {"status": "error", "message": f"未知 source.mode: {mode}"}


def _outline_from_fulltext(book_title: str, slug: str, source: dict, request_path: Path) -> dict:
    cdir = cache_dir(slug)
    chapters_dir = cdir / "fulltext" / "chapters"
    chapter_files = sorted(chapters_dir.glob("*.txt"))

    excerpts: list[str] = []
    for f in chapter_files:
        body = read_text(f)
        head = body[:600]
        excerpts.append(f"--- chapter {f.stem} ---\n{head}\n")
    chapter_excerpts = "\n".join(excerpts)

    template = prompt_template("outline_fulltext")
    validation = source.get("validation", {})
    prompt_body = (
        template.replace("{book_title}", book_title)
        .replace("{strategy}", source.get("chapter_strategy", "unknown"))
        .replace("{source_channel}", source.get("channel") or source.get("source_file") or "")
        .replace("{source_url}", source.get("source_url") or source.get("source_file") or "")
        .replace("{word_count}", str(validation.get("word_count", 0)))
        .replace("{chapter_count}", str(validation.get("chapter_count", 0)))
        .replace("{confidence}", validation.get("confidence", "unknown"))
        .replace("{chapter_excerpts}", chapter_excerpts)
    )

    write_text(
        request_path,
        _stage_skeleton(
            "outline 章节目录整理（fulltext 模式）",
            book_title, slug, "outline.json", "notes", prompt_body,
        ),
    )
    return {
        "status": "request_written",
        "message": f"已生成 {request_path}（fulltext 模式）",
    }


def _outline_from_summary(book_title: str, slug: str, request_path: Path) -> dict:
    cdir = cache_dir(slug)
    search_path = cdir / "search.json"
    if not search_path.exists():
        return {
            "status": "blocked",
            "message": f"找不到 {search_path}，请按 _search_request.md 完成搜索",
        }
    search = read_json(search_path)
    template = prompt_template("outline")
    prompt_body = (
        template.replace("{book_title}", book_title)
        .replace("{search_a}", _json_dump(search.get("engine_a", {})))
        .replace("{search_b}", _json_dump(search.get("engine_b", {})))
    )
    write_text(
        request_path,
        _stage_skeleton(
            "outline 章节目录提取（fallback 摘要模式）",
            book_title, slug, "outline.json", "notes", prompt_body,
        ),
    )
    return {
        "status": "request_written",
        "message": f"已生成 {request_path}（fallback 摘要模式）",
    }


def run_notes(book_title: str, slug: str, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    notes_path = cdir / "notes.md"
    request_path = cdir / "_notes_request.md"
    outline_path = cdir / "outline.json"

    if notes_path.exists() and not force:
        return {"status": "cached", "message": f"{notes_path} 已存在，跳过"}

    if not outline_path.exists():
        return {"status": "blocked", "message": f"找不到 {outline_path}"}

    mode, source = _resolve_mode(slug)
    if mode == "missing":
        return {"status": "blocked", "message": "找不到 source.json"}

    outline = read_json(outline_path)
    if mode in ("local", "web"):
        return _notes_from_fulltext(book_title, slug, source, outline, request_path)
    if mode == "fallback_summary":
        return _notes_from_summary(book_title, slug, outline, request_path)
    return {"status": "error", "message": f"未知 source.mode: {mode}"}


def _notes_from_fulltext(book_title: str, slug: str, source: dict, outline: dict, request_path: Path) -> dict:
    template = prompt_template("chapter_notes_fulltext")
    validation = source.get("validation", {})
    prompt_body = (
        template.replace("{book_title}", book_title)
        .replace("{outline}", _json_dump(outline))
        .replace("{source_channel}", source.get("channel") or source.get("source_file") or "")
        .replace("{source_url}", source.get("source_url") or source.get("source_file") or "")
        .replace("{language}", outline.get("language", "zh"))
        .replace("{word_count}", str(validation.get("word_count", 0)))
    )
    write_text(
        request_path,
        _stage_skeleton(
            "notes 逐章详细笔记（fulltext 模式）",
            book_title, slug, "notes.md", "mindmap", prompt_body,
        ),
    )
    return {
        "status": "request_written",
        "message": f"已生成 {request_path}（fulltext 模式）",
    }


def _notes_from_summary(book_title: str, slug: str, outline: dict, request_path: Path) -> dict:
    cdir = cache_dir(slug)
    search = read_json(cdir / "search.json")
    template = prompt_template("chapter_notes")
    prompt_body = (
        template.replace("{book_title}", book_title)
        .replace("{outline}", _json_dump(outline))
        .replace("{search_a}", _json_dump(search.get("engine_a", {})))
        .replace("{search_b}", _json_dump(search.get("engine_b", {})))
    )
    write_text(
        request_path,
        _stage_skeleton(
            "notes 逐章详细笔记（fallback 摘要模式）",
            book_title, slug, "notes.md", "mindmap", prompt_body,
        ),
    )
    return {
        "status": "request_written",
        "message": f"已生成 {request_path}（fallback 摘要模式）",
    }


def run_mindmap(book_title: str, slug: str, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    mindmap_path = cdir / "mindmap.mmd"
    request_path = cdir / "_mindmap_request.md"
    notes_path = cdir / "notes.md"

    if mindmap_path.exists() and not force:
        return {"status": "cached", "message": f"{mindmap_path} 已存在，跳过"}

    if not notes_path.exists():
        return {"status": "blocked", "message": f"找不到 {notes_path}"}

    notes_content = read_text(notes_path)
    template = prompt_template("mindmap")
    prompt_body = (
        template.replace("{book_title}", book_title)
        .replace("{notes}", notes_content)
    )

    write_text(
        request_path,
        _stage_skeleton(
            "mindmap 思维导图生成",
            book_title, slug, "mindmap.mmd", "publish", prompt_body,
        ),
    )
    return {
        "status": "request_written",
        "message": f"已生成 {request_path}",
    }


def _json_dump(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)
