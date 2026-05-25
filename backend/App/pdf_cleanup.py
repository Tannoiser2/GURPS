"""PDF text cleanup pass.

Run BEFORE regex-based structure extraction. Removes the most common OCR
artifacts that turn into spurious clues, NPC descriptions, or section labels:

- inline parenthetical examples (`(e.g., ...)`, `(es. ...)`) — these span lines
  and were being matched as clue/NPC text in modules like Gotham-39
- words broken across line endings with a hyphen
- repeated header / footer lines (same line appearing on >=3 pages of the doc)
- column-split paragraphs (line ends mid-sentence, next line starts lowercase)
- stat-block bleed (sequences of numeric tokens dense enough to be a stat line)

Public API:
    clean_pdf_text(text)            -> cleaned single blob
    clean_pdf_pages(pages)          -> cleaned list[str], same length

Both are pure functions and safe to call on already-clean text.
"""
from __future__ import annotations

import re
from collections import Counter


_PAREN_EG_RE = re.compile(
    r"\(\s*(?:e\.?g\.?|i\.?e\.?|es\.?|esempio|esempi|for example|ad esempio)[^()]*?\)",
    re.IGNORECASE | re.DOTALL,
)
# Unmatched / multi-line parenthetical that opens with e.g. but never closes
# in the same paragraph: keep up to next blank line.
_PAREN_EG_OPEN_RE = re.compile(
    r"\(\s*(?:e\.?g\.?|i\.?e\.?|es\.?|esempio|esempi|for example|ad esempio)\b[^()\n]*"
    r"(?:\n[^()\n]*){0,8}?(?=\n\s*\n|$)",
    re.IGNORECASE,
)

_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")

_STAT_LINE_RE = re.compile(
    r"^\s*(?:ST|DX|IQ|HT|HP|FP|Will|Per|Basic Speed|Basic Move|Dodge|Parry|Block|SM|DR|AC|HD)\b[:\s]",
    re.IGNORECASE | re.MULTILINE,
)

# Token used inline to mark a removed parenthetical so regexes downstream
# don't accidentally bridge across the removal site.
_GAP = " "


def _strip_parentheticals(text: str) -> str:
    text = _PAREN_EG_RE.sub(_GAP, text)
    text = _PAREN_EG_OPEN_RE.sub(_GAP, text)
    return text


def _dehyphenate(text: str) -> str:
    return _HYPHEN_BREAK_RE.sub(r"\1\2", text)


def _join_column_breaks(text: str) -> str:
    """Lines that end mid-sentence and continue on the next line (lowercase
    start, no terminal punctuation) get joined. Headers and list items are
    left alone.
    """
    out_lines: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        cur = lines[i]
        if (
            i + 1 < len(lines)
            and cur.strip()
            and not cur.rstrip().endswith((".", "!", "?", ":", ";", '"', "”", ")"))
            and len(cur.strip()) > 30
            and lines[i + 1].strip()
            and lines[i + 1].lstrip()[:1].islower()
        ):
            cur = cur.rstrip() + " " + lines[i + 1].lstrip()
            lines[i + 1] = cur
            i += 1
            continue
        out_lines.append(cur)
        i += 1
    return "\n".join(out_lines)


def _drop_repeated_headers(pages: list[str]) -> list[str]:
    """Lines appearing identically on >=3 pages and short enough to be a
    running header/footer get removed from every page they appear on.
    """
    if len(pages) < 3:
        return pages
    counter: Counter[str] = Counter()
    for page in pages:
        seen_on_page: set[str] = set()
        for raw in (page or "").split("\n"):
            line = raw.strip()
            if 3 <= len(line) <= 70 and line not in seen_on_page:
                counter[line] += 1
                seen_on_page.add(line)
    threshold = max(3, len(pages) // 4)
    junk = {line for line, n in counter.items() if n >= threshold}
    if not junk:
        return pages
    cleaned: list[str] = []
    for page in pages:
        kept = [raw for raw in (page or "").split("\n") if raw.strip() not in junk]
        cleaned.append("\n".join(kept))
    return cleaned


def _strip_stat_lines(text: str) -> str:
    """Drop full lines that are obviously stat-block readouts. Narrative
    paragraphs near a stat block are preserved; only the dense numeric lines
    are removed so they don't get scooped up as NPC description.
    """
    kept: list[str] = []
    for line in text.split("\n"):
        if _STAT_LINE_RE.search(line):
            digit_share = sum(ch.isdigit() for ch in line) / max(1, len(line))
            if digit_share > 0.05 or ";" in line or "," in line:
                continue
        kept.append(line)
    return "\n".join(kept)


def clean_pdf_text(text: str) -> str:
    if not text:
        return ""
    text = _strip_parentheticals(text)
    text = _dehyphenate(text)
    text = _strip_stat_lines(text)
    text = _join_column_breaks(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def clean_pdf_pages(pages: list[str]) -> list[str]:
    if not pages:
        return []
    deheadered = _drop_repeated_headers([p or "" for p in pages])
    return [clean_pdf_text(p) for p in deheadered]
