"""Stage 5: publish — 创建飞书文档 + 写画板 + 移动到目标文件夹。

执行链路：
1. docs +create —— XML 骨架带 <whiteboard type="blank"/>，拿到 doc_token + board_token
2. docs +update --command append --doc-format markdown —— 追加 notes.md 正文
3. whiteboard +update --input_format mermaid —— 写思维导图
4. drive +create-folder（仅首次）+ drive +move —— 把文档归档

幂等性：
- publish.json 存在则跳过整个 stage
- 中途失败时已建的资源 token 都写到 publish.json，重跑时可识别已完成步骤
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from .common import cache_dir, read_json, read_text, write_json, PROJECT_ROOT

TARGET_FOLDER_NAME = "书籍读书笔记"
LARK_CLI = shutil.which("lark-cli") or "lark-cli"


def run(book_title: str, slug: str, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    publish_path = cdir / "publish.json"
    notes_path = cdir / "notes.md"
    mindmap_path = cdir / "mindmap.mmd"

    if publish_path.exists() and not force:
        return {
            "status": "cached",
            "message": f"{publish_path} 已存在，跳过；--force 可重发",
            "publish": read_json(publish_path),
        }

    for required in (notes_path, mindmap_path):
        if not required.exists():
            return {
                "status": "blocked",
                "message": f"找不到 {required}，请先跑前置阶段",
            }

    state: dict = {}
    if publish_path.exists() and force:
        state = read_json(publish_path)
        state.pop("mindmap_written", None)
        state.pop("notes_appended", None)

    today = date.today().isoformat()
    doc_title = f"{book_title} · 读书笔记 · {today}"

    if "doc_token" not in state:
        skeleton_xml = (
            f"<title>{_xml_escape(doc_title)}</title>"
            f"<h1>思维导图</h1>"
            f'<whiteboard type="blank"/>'
            f"<h1>逐章详细笔记</h1>"
            f"<p>正文加载中…</p>"
        )
        create_resp = _run_cli([
            "lark-cli", "docs", "+create",
            "--api-version", "v2",
            "--content", skeleton_xml,
            "--as", "user",
        ])
        data = create_resp.get("data", {})
        doc = data.get("document", {})
        new_blocks = doc.get("new_blocks", [])
        whiteboard_blocks = [
            b for b in new_blocks if b.get("block_type") == "whiteboard"
        ]
        if not whiteboard_blocks:
            return {
                "status": "error",
                "message": "create 返回里没有 whiteboard block，无法继续",
                "raw": create_resp,
            }

        state.update({
            "doc_token": doc.get("document_id"),
            "doc_url": doc.get("url"),
            "board_token": whiteboard_blocks[0].get("block_token"),
            "board_block_id": whiteboard_blocks[0].get("block_id"),
        })
        write_json(publish_path, state)

    if not state.get("notes_appended"):
        notes_md = read_text(notes_path)
        rel_notes = _relative_to_cwd(notes_path)
        _run_cli([
            "lark-cli", "docs", "+update",
            "--api-version", "v2",
            "--doc", state["doc_token"],
            "--command", "str_replace",
            "--doc-format", "markdown",
            "--pattern", "正文加载中…",
            "--content", f"@{rel_notes}",
            "--as", "user",
        ])
        state["notes_appended"] = True
        write_json(publish_path, state)

    if not state.get("mindmap_written"):
        rel_mmd = _relative_to_cwd(mindmap_path)
        _run_cli([
            "lark-cli", "whiteboard", "+update",
            "--whiteboard-token", state["board_token"],
            "--input_format", "mermaid",
            "--source", f"@{rel_mmd}",
            "--overwrite",
            "--as", "user",
        ])
        state["mindmap_written"] = True
        write_json(publish_path, state)

    if not state.get("folder_token"):
        state["folder_token"] = _ensure_folder(TARGET_FOLDER_NAME)
        write_json(publish_path, state)

    if not state.get("moved"):
        _run_cli([
            "lark-cli", "drive", "+move",
            "--file-token", state["doc_token"],
            "--type", "docx",
            "--folder-token", state["folder_token"],
            "--as", "user",
        ])
        state["moved"] = True
        write_json(publish_path, state)

    return {
        "status": "ok",
        "message": f"文档已发布：{state.get('doc_url')}",
        "publish": state,
    }


def _ensure_folder(name: str) -> str:
    """检查云空间根目录下是否存在该文件夹；不存在则创建并返回 token。"""
    search = _run_cli([
        "lark-cli", "drive", "+search",
        "--query", name,
        "--doc-types", "folder",
        "--only-title",
        "--page-size", "20",
        "--as", "user",
    ])
    items = (
        search.get("data", {}).get("items")
        or search.get("data", {}).get("docs_entities")
        or []
    )
    for item in items:
        title = item.get("title") or item.get("name") or ""
        if title.strip() == name:
            return (
                item.get("docs_token")
                or item.get("token")
                or item.get("file_token")
                or ""
            )

    created = _run_cli([
        "lark-cli", "drive", "+create-folder",
        "--name", name,
        "--as", "user",
    ])
    data = created.get("data", {})
    return data.get("token") or data.get("folder_token") or ""


def _run_cli(args: list[str]) -> dict:
    """在项目根目录执行 lark-cli，返回解析后的 JSON。"""
    resolved = [LARK_CLI if a == "lark-cli" else a for a in args]
    proc = subprocess.run(
        resolved,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    stdout = proc.stdout.strip()
    if proc.returncode != 0:
        raise RuntimeError(
            f"CLI 失败 (rc={proc.returncode}): {' '.join(args)}\n"
            f"stderr: {proc.stderr}\nstdout: {stdout}"
        )
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"无法解析 CLI 输出: {stdout[:500]}") from exc


def _relative_to_cwd(path: Path) -> str:
    """lark-cli 要求 @file 是 cwd 的相对路径。"""
    return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
