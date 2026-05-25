"""通用工具：slug、缓存路径、JSON I/O。"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_ROOT = PROJECT_ROOT / "cache"
PROMPTS_ROOT = PROJECT_ROOT / "prompts"


def slugify(title: str) -> str:
    """书名 → 文件系统安全的 slug。中文保留，去除标点和空白。"""
    normalized = unicodedata.normalize("NFKC", title).strip()
    cleaned = re.sub(r"[\s/\\:*?\"<>|.,;'`!@#$%^&()\[\]{}=+]+", "-", normalized)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "untitled"


def cache_dir(slug: str) -> Path:
    path = CACHE_ROOT / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def prompt_template(name: str) -> str:
    return read_text(PROMPTS_ROOT / f"{name}.txt")
