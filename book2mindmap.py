"""book2mindmap 主入口。

第一阶段 fetch 必须显式指定来源：
    python book2mindmap.py "书名" --source local --source-file books/xxx.epub
    python book2mindmap.py "书名" --source web                  # 公版书库
    python book2mindmap.py "书名" --source web --no-fallback     # 公版没有就退出

不指定 --source 时打印帮助提示并以退出码 2 退出（让 Claude Code 通过
AskUserQuestion 把选择补上）。

后续阶段（不再依赖 --source）:
    python book2mindmap.py "书名" --stage outline
    python book2mindmap.py "书名" --stage notes
    python book2mindmap.py "书名" --stage mindmap
    python book2mindmap.py "书名" --stage publish
    python book2mindmap.py "书名" --stage notify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pipeline import fetch, llm_stages, notify, publish
from pipeline.common import slugify

STAGES = ["fetch", "outline", "notes", "mindmap", "publish", "notify"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="书籍 → 思维导图 + 飞书云文档 管道"
    )
    parser.add_argument("book_title", help="书名（中英皆可）")
    parser.add_argument(
        "--stage",
        choices=["all"] + STAGES,
        default="all",
        help="执行某一阶段（默认 all：从当前缺失的 stage 开始顺序跑）",
    )
    parser.add_argument(
        "--source",
        choices=["local", "web"],
        help="Stage 1 来源。local: 本地电子书；web: 网络公版书库",
    )
    parser.add_argument(
        "--source-file",
        type=Path,
        help="--source local 时的电子书路径（txt/epub/pdf/mobi/azw/azw3）",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="--source web 时禁止退到双引擎搜索摘要",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重跑该阶段，无视已有缓存",
    )
    args = parser.parse_args()

    book_title = args.book_title.strip()
    slug = slugify(book_title)

    print(f"[book2mindmap] 书名: {book_title}")
    print(f"[book2mindmap] slug: {slug}")
    print(f"[book2mindmap] 阶段: {args.stage} (force={args.force})")
    print()

    stages_to_run = STAGES if args.stage == "all" else [args.stage]

    for stage in stages_to_run:
        force = args.force and (args.stage == stage or args.stage == "all")
        print(f"--- Stage: {stage} ---")
        result = _dispatch(stage, book_title, slug, args, force=force)
        status = result.get("status")
        message = result.get("message", "")
        print(f"[{status}] {message}")
        print()

        if status == "need_source":
            return 2
        if status == "blocked":
            return 2
        if status == "error":
            return 1
        if status == "request_written":
            print(
                "→ 这是 LLM/搜索人工阶段。请按生成的 _*_request.md "
                "完成产物后，再次运行 book2mindmap.py 继续。"
            )
            return 0

    return 0


def _dispatch(stage: str, book_title: str, slug: str, args, force: bool) -> dict:
    if stage == "fetch":
        return _dispatch_fetch(book_title, slug, args, force)
    if stage == "outline":
        return llm_stages.run_outline(book_title, slug, force=force)
    if stage == "notes":
        return llm_stages.run_notes(book_title, slug, force=force)
    if stage == "mindmap":
        return llm_stages.run_mindmap(book_title, slug, force=force)
    if stage == "publish":
        return publish.run(book_title, slug, force=force)
    if stage == "notify":
        return notify.run(book_title, slug, force=force)
    return {"status": "error", "message": f"unknown stage: {stage}"}


def _dispatch_fetch(book_title: str, slug: str, args, force: bool) -> dict:
    if args.source is None:
        return {
            "status": "need_source",
            "message": (
                "请通过 --source 指定全文来源：\n"
                "  --source local --source-file <路径>   # 本地电子书 (txt/epub/pdf/mobi/azw/azw3)\n"
                "  --source web                          # 公版书库自动搜索\n"
                "  --source web --no-fallback            # 公版找不到就退出（不退到摘要 fallback）"
            ),
        }
    if args.source == "local":
        if not args.source_file:
            return {
                "status": "error",
                "message": "--source local 必须同时给出 --source-file <路径>",
            }
        return fetch.run_local(book_title, slug, args.source_file, force=force)
    if args.source == "web":
        return fetch.run_web(
            book_title, slug, allow_fallback=not args.no_fallback, force=force
        )
    return {"status": "error", "message": f"未知 source: {args.source}"}


if __name__ == "__main__":
    sys.exit(main())
