"""全文完整性校验 + 章节切分。

输入: 全文 plain text（已去除所有标签）。
输出: chapters 列表 [{index, title, body}]，加一个 validation 报告。

章节识别策略（按优先级，第一个命中就返回）:
1. 中文 第 X 章/节/部分
2. 英文 CHAPTER N / Chapter N / PART N
3. 目录块 (Contents / 目录) 抽出章名 → 在正文中找首次出现位置切分
   —— 适用于 Project Gutenberg 经典书（章名是单行普通短语，无 "Chapter" 前缀）
4. 纯数字标题行 (1. 2. 3.)
5. 都不中→单章 fallback，confidence: low
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Chapter:
    index: int
    title: str
    body: str


@dataclass
class Validation:
    word_count: int
    char_count: int
    chapter_count: int
    confidence: str
    issues: list[str]


CN_CHAPTER_RE = re.compile(
    r"^[　\s]*第\s*([一二三四五六七八九十百千零\d]+)\s*[章节部分回篇]\s*[:：]?\s*(.*)$",
    re.MULTILINE,
)
EN_CHAPTER_RE = re.compile(
    r"^[\s]*(?:CHAPTER|Chapter|PART|Part)\s+([\dIVXLCM]+|[A-Za-z]+)(?:[.:\s]+(.*))?$",
    re.MULTILINE,
)
NUMERIC_HEADING_RE = re.compile(r"^[\s]*(\d{1,3})[.、\s]+([^\n]{2,80})$", re.MULTILINE)

CONTENTS_RE = re.compile(
    r"(?:^|\n)[\s]*(?:Contents|CONTENTS|目\s*录|目\s*次)\s*\n",
    re.IGNORECASE,
)


def _split_by_regex(text: str, pattern: re.Pattern) -> list[Chapter] | None:
    matches = list(pattern.finditer(text))
    if len(matches) < 3:
        return None
    chapters: list[Chapter] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title_line = text[m.start():m.end()].strip()
        body = text[m.end():end].strip()
        chapters.append(Chapter(index=i + 1, title=title_line, body=body))
    return chapters


def _split_by_toc(text: str) -> list[Chapter] | None:
    """从目录块抽章名，在正文中按章名首次出现位置切分。

    Project Gutenberg 经典书常见模式：开头有 "Contents" 块，列出短章名（如
    Walden 的 "Economy / Reading / Sounds ..."），随后正文里每章以同一短语
    单独成行作为标题。
    """
    toc_match = CONTENTS_RE.search(text)
    if not toc_match:
        return None

    after_toc = text[toc_match.end():]
    toc_titles_raw: list[str] = []
    blank_run = 0
    for line in after_toc.split("\n"):
        s = line.strip()
        if not s:
            blank_run += 1
            if blank_run >= 4 and toc_titles_raw:
                break
            continue
        blank_run = 0
        if len(s) > 80:
            break
        if any(s.startswith(p) for p in ("---", "===", "***", "* * *", "_")):
            break
        toc_titles_raw.append(s)
        if len(toc_titles_raw) > 80:
            break

    toc_titles = [t for t in toc_titles_raw if 2 <= len(t) <= 80]
    toc_titles = [
        t for t in toc_titles
        if not (t.isupper() and len(t) <= 12)
    ]
    if len(toc_titles) < 3:
        return None

    body_start = toc_match.end()
    skipped = 0
    while toc_titles:
        first_title = toc_titles[0]
        first_pos = text.find(first_title, body_start + 500)
        if first_pos > 0:
            break
        toc_titles.pop(0)
        skipped += 1
        if skipped > 10:
            return None
    if len(toc_titles) < 3:
        return None

    seen: set[str] = set()
    deduped: list[str] = []
    for t in toc_titles:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    toc_titles = deduped

    positions: list[tuple[int, str]] = []
    cursor = body_start
    for title in toc_titles:
        title_pattern = re.compile(
            r"(?:^|\n)\s*" + re.escape(title) + r"\s*\n",
            re.IGNORECASE,
        )
        m = title_pattern.search(text, cursor)
        if not m:
            continue
        positions.append((m.start(), title))
        cursor = m.end()

    if len(positions) < 3:
        return None

    chapters: list[Chapter] = []
    for i, (pos, title) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        line_end = text.find("\n", pos)
        body_start_inner = line_end + 1 if line_end > 0 else pos + len(title)
        body = text[body_start_inner:end].strip()
        chapters.append(Chapter(index=i + 1, title=title, body=body))
    return chapters


def split_chapters(full_text: str) -> tuple[list[Chapter], str]:
    """返回 (chapters, strategy_used)。"""
    cn = _split_by_regex(full_text, CN_CHAPTER_RE)
    if cn:
        return cn, "cn_chapter"
    en = _split_by_regex(full_text, EN_CHAPTER_RE)
    if en:
        return en, "en_chapter"
    toc = _split_by_toc(full_text)
    if toc:
        return toc, "toc_block"
    numeric = _split_by_regex(full_text, NUMERIC_HEADING_RE)
    if numeric:
        return numeric, "numeric_heading"
    return (
        [Chapter(index=1, title="全文", body=full_text.strip())],
        "single_chapter_fallback",
    )


def validate(full_text: str, chapters: list[Chapter], expected_min_chapters: int = 3) -> Validation:
    """计算字数 / 章数，给出 confidence。"""
    issues: list[str] = []

    char_count = len(full_text)
    cn_chars = sum(1 for c in full_text if "一" <= c <= "鿿")
    if cn_chars > char_count * 0.3:
        word_count = cn_chars + len(re.findall(r"[A-Za-z]+", full_text))
    else:
        word_count = len(re.findall(r"\b\w+\b", full_text))

    chapter_count = len(chapters)

    if word_count < 5000:
        issues.append(f"字/词数过少 ({word_count})，疑似仅为节选/试读")
    if chapter_count < expected_min_chapters:
        issues.append(f"章数过少 ({chapter_count} < {expected_min_chapters})，章节识别可能失败")
    if chapter_count == 1 and chapters[0].title == "全文":
        issues.append("未能识别任何章节标记，后续笔记将以全文为单一块输入")

    if not issues:
        confidence = "high"
    elif len(issues) == 1 and word_count >= 5000:
        confidence = "medium"
    else:
        confidence = "low"

    return Validation(
        word_count=word_count,
        char_count=char_count,
        chapter_count=chapter_count,
        confidence=confidence,
        issues=issues,
    )


def chapters_to_dict(chapters: list[Chapter]) -> list[dict[str, Any]]:
    return [asdict(c) for c in chapters]


def validation_to_dict(v: Validation) -> dict[str, Any]:
    return asdict(v)
