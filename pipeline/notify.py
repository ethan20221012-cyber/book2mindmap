"""Stage 6: notify — 用 user 身份给自己发飞书消息。

逻辑：
1. 用 contact +get-user 拿到 self 的 open_id（缓存到 publish.json）
2. im +messages-send --as user --user-id <self> --markdown <msg>
3. 把发送状态写回 publish.json.notified = True
"""

from __future__ import annotations

import json
import shutil
import subprocess

from .common import cache_dir, read_json, write_json, PROJECT_ROOT

LARK_CLI = shutil.which("lark-cli") or "lark-cli"


def run(book_title: str, slug: str, force: bool = False) -> dict:
    cdir = cache_dir(slug)
    publish_path = cdir / "publish.json"

    if not publish_path.exists():
        return {
            "status": "blocked",
            "message": f"找不到 {publish_path}，请先跑 --stage publish",
        }

    state = read_json(publish_path)
    if state.get("notified") and not force:
        return {
            "status": "cached",
            "message": "已发送过；--force 可重发",
            "publish": state,
        }

    if not state.get("self_open_id"):
        info = _run_cli([
            "lark-cli", "contact", "+get-user",
            "--as", "user",
        ])
        open_id = (
            info.get("data", {}).get("user", {}).get("open_id")
            or info.get("data", {}).get("open_id")
        )
        if not open_id:
            return {
                "status": "error",
                "message": "无法解析 self.open_id",
                "raw": info,
            }
        state["self_open_id"] = open_id
        write_json(publish_path, state)

    doc_url = state.get("doc_url", "")
    post_content = json.dumps({
        "zh_cn": {
            "title": f"《{book_title}》读书笔记已生成",
            "content": [
                [{"tag": "a", "text": "打开飞书云文档", "href": doc_url}],
                [{"tag": "text", "text": "含逐章详细笔记 + 思维导图画板"}],
            ],
        }
    }, ensure_ascii=False)

    _run_cli([
        "lark-cli", "im", "+messages-send",
        "--as", "user",
        "--user-id", state["self_open_id"],
        "--content", post_content,
        "--msg-type", "post",
    ])

    state["notified"] = True
    write_json(publish_path, state)
    return {
        "status": "ok",
        "message": "已通过飞书 IM 推送给本人",
        "publish": state,
    }


def _run_cli(args: list[str]) -> dict:
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
