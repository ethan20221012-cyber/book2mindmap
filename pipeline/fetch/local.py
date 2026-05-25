"""本地电子书解析：txt / epub / pdf / mobi / azw / azw3。

mobi/azw/azw3 通过 calibre 的 ebook-convert 转成 epub 后再走 epub 路径。
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup


SUPPORTED_EXTS = {".txt", ".epub", ".pdf", ".mobi", ".azw", ".azw3"}


def extract_full_text(file_path: Path) -> tuple[str, dict]:
    """解析本地电子书 → (full_text, metadata)。

    metadata: {format, file_size, source_file}
    """
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise ValueError(
            f"不支持的格式 {ext}。支持: {', '.join(sorted(SUPPORTED_EXTS))}"
        )

    metadata = {
        "format": ext.lstrip("."),
        "file_size": file_path.stat().st_size,
        "source_file": str(file_path),
    }

    if ext == ".txt":
        text = _read_txt(file_path)
    elif ext == ".epub":
        text = _read_epub(file_path)
    elif ext == ".pdf":
        text = _read_pdf(file_path)
    elif ext in {".mobi", ".azw", ".azw3"}:
        text = _read_via_calibre(file_path)
    else:
        raise AssertionError(f"unreachable: {ext}")

    return text, metadata


def _read_txt(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_epub(path: Path) -> str:
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text("\n", strip=False)
        parts.append(text)
    return "\n\n".join(parts)


def _read_pdf(path: Path) -> str:
    import fitz
    doc = fitz.open(str(path))
    parts: list[str] = []
    try:
        for page in doc:
            parts.append(page.get_text("text"))
    finally:
        doc.close()
    return "\n".join(parts)


def _read_via_calibre(path: Path) -> str:
    """用 calibre 的 ebook-convert 把 mobi/azw/azw3 转成 epub 再读。"""
    cmd = shutil.which("ebook-convert")
    if not cmd:
        raise RuntimeError(
            f"未找到 calibre 的 ebook-convert 命令。\n"
            f"请安装 calibre（https://calibre-ebook.com/download）后重试，"
            f"或先把 {path.name} 用其他工具转为 epub/pdf。"
        )
    with tempfile.TemporaryDirectory() as tmp:
        out_epub = Path(tmp) / (path.stem + ".epub")
        proc = subprocess.run(
            [cmd, str(path), str(out_epub)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0 or not out_epub.exists():
            raise RuntimeError(
                f"ebook-convert 失败 (rc={proc.returncode}):\n{proc.stderr[-500:]}"
            )
        return _read_epub(out_epub)
