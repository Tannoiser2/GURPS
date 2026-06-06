#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from textwrap import shorten
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.json_doctor.rules import audit, score


BRIEF = ROOT / "data" / "compiled_adventures" / "_catalogo" / "AVVENTURE_BRIEF.md"
OUT_DIR = ROOT / "data" / "compiled_adventures" / "_catalogo"
OUT_PNG = OUT_DIR / "adventure_brief_sample_A4_portrait_strips_6up.png"
OUT_PDF = OUT_DIR / "adventure_brief_sample_A4_portrait_strips_6up.pdf"

A4_PORTRAIT = (1240, 1754)
MARGIN = 42
GAP = 24

FONT_REGULAR = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)
FONT_BOLD = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)

PALETTE = {
    "paper": "#efe9dc",
    "ink": "#201d19",
    "muted": "#665f55",
    "soft": "#ddd0bd",
    "line": "#b8662c",
    "dark": "#151d1f",
    "panel": "#fffaf0",
    "tag": "#efe0c6",
    "red": "#8d2f2f",
    "blue": "#245f73",
    "green": "#496d3b",
}

THEME_COLORS = {
    "action": "#a84e2b",
    "fantasy": "#7b5b2a",
    "horror": "#7a2834",
    "mystery_horror": "#5d334f",
    "investigation": "#28645e",
    "romance": "#934766",
    "sci-fi": "#2d6f9f",
}

PROFILE_LABELS = {
    "escalating_horror": "orrore crescente",
    "faction_crisis": "crisi tra fazioni",
    "guided_sandbox": "sandbox guidato",
    "heist": "colpo",
    "investigation_graph": "indagine a nodi",
    "mythic_quest": "ricerca mitica",
    "pursuit_thriller": "inseguimento thriller",
    "ritual_dungeon": "dungeon rituale",
    "room_keyed_dungeon": "luoghi numerati",
    "survival_escape": "sopravvivenza e fuga",
    "scenario": "scenario",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in FONT_BOLD if bold else FONT_REGULAR:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


F = {
    "page_title": font(34, True),
    "page_small": font(17),
    "title": font(31, True),
    "title_small": font(25, True),
    "subtitle": font(17, True),
    "h": font(15, True),
    "body": font(20),
    "small": font(14),
    "stat": font(16),
    "tiny": font(12),
    "metric": font(22, True),
}


def text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return "; ".join(text_value(v) for v in value if text_value(v))
    if isinstance(value, dict):
        return "; ".join(f"{key}: {text_value(item)}" for key, item in value.items() if text_value(item))
    return str(value)


def unwrap(raw: dict[str, Any]) -> dict[str, Any]:
    return raw.get("adventure_definition", raw)


def parse_brief(path: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    if not path.exists():
        return entries
    current: str | None = None
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^###\s+(.+)$", line)
        if match:
            heading = match.group(1).strip()
            meta = re.match(r"^(.*?)\s+—\s+⭐\s+([0-9]+(?:\.[0-9]+)?)/10\s+·\s+(.+)$", heading)
            if meta:
                current = meta.group(1).strip()
                entries[current] = {
                    "flavor": "",
                    "prompt": "",
                    "score": meta.group(2).strip(),
                    "brief_genre": meta.group(3).strip(),
                }
            else:
                current = heading
                entries[current] = {"flavor": "", "prompt": "", "score": "", "brief_genre": ""}
            i += 1
            continue
        if current and line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            entries[current]["flavor"] = line.strip("*").strip()
        if current and line.startswith("> "):
            entries[current]["prompt"] = line[2:].strip()
        i += 1
    return entries


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, width: int, max_lines: int | None = None, ellipsis: bool = True) -> list[str]:
    words = text_value(text).split()
    lines: list[str] = []
    line = ""
    for word in words:
        trial = word if not line else f"{line} {word}"
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = word
        while draw.textbbox((0, 0), line, font=fnt)[2] > width and len(line) > 4:
            cut = max(4, int(len(line) * width / max(draw.textbbox((0, 0), line, font=fnt)[2], 1)))
            lines.append(line[:cut] + "-")
            line = line[cut:]
    if line:
        lines.append(line)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if ellipsis:
            lines[-1] = lines[-1].rstrip(". ") + "..."
    return lines


def draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    w: int,
    fnt: ImageFont.ImageFont,
    fill: str,
    max_lines: int | None = None,
    line_h: int | None = None,
    ellipsis: bool = True,
) -> int:
    line_h = line_h or int(fnt.size * 1.28)
    for line in wrap(draw, text, fnt, w, max_lines, ellipsis=ellipsis):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def cover_crop(path: Path, size: tuple[int, int]) -> Image.Image:
    if not path.exists():
        img = Image.new("RGB", size, PALETTE["dark"])
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, size[0], size[1]), fill="#263238")
        draw.line((0, 0, size[0], size[1]), fill="#b8662c", width=8)
        draw.line((0, size[1], size[0], 0), fill="#b8662c", width=8)
        draw.text((18, size[1] // 2 - 12), "IMMAGINE", font=F["small"], fill="#fff7e9")
        return img
    img = Image.open(path).convert("RGB")
    src_w, src_h = img.size
    dst_w, dst_h = size
    scale = max(dst_w / src_w, dst_h / src_h)
    resized = img.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - dst_w) // 2
    top = (resized.height - dst_h) // 2
    return resized.crop((left, top, left + dst_w, top + dst_h))


def difficulty(data: dict[str, Any]) -> tuple[str, str]:
    clues = len(data.get("clues") or [])
    revelations = len(data.get("revelations") or [])
    locations = len(data.get("locations") or [])
    actors = len(data.get("actors") or [])
    profiles = len(data.get("runtime_profiles") or [])
    complexity = clues * 0.20 + revelations * 0.45 + locations * 0.20 + actors * 0.25 + profiles * 0.35
    if complexity < 4.0:
        return "Facile", "#496d3b"
    if complexity < 6.5:
        return "Media", "#245f73"
    if complexity < 9.0:
        return "Impegnativa", "#8b5a23"
    return "Alta", "#8d2f2f"


def fit_title_font(draw: ImageDraw.ImageDraw, title: str, width: int) -> ImageFont.ImageFont:
    for fnt in (F["title"], F["title_small"], font(18, True)):
        if len(wrap(draw, title, fnt, width, 2)) <= 2:
            return fnt
    return font(18, True)


def stat_pill(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: str) -> int:
    bbox = draw.textbbox((0, 0), text, font=F["stat"])
    w = bbox[2] - bbox[0] + 20
    draw.rounded_rectangle((x, y, x + w, y + 30), radius=5, fill="#fff8ea", outline="#dcc7a6", width=1)
    draw.text((x + 10, y + 6), text, font=F["stat"], fill=color)
    return x + w + 7


def theme_color(data: dict[str, Any], fallback: str) -> str:
    genre = text_value(data.get("genre") or fallback).lower()
    return THEME_COLORS.get(genre, PALETTE["line"])


def light_pill(draw: ImageDraw.ImageDraw, text: str, x: int, y: int) -> int:
    label = shorten(text_value(text), width=28, placeholder="...")
    bbox = draw.textbbox((0, 0), label, font=F["small"])
    w = bbox[2] - bbox[0] + 20
    draw.rounded_rectangle((x, y, x + w, y + 26), radius=5, fill="#fff4dd", outline="#f6ddb2", width=1)
    draw.text((x + 10, y + 5), label, font=F["small"], fill="#3b3027")
    return x + w + 7


def profile_label(value: str) -> str:
    key = text_value(value).strip()
    return PROFILE_LABELS.get(key, key.replace("_", " "))


def brief_title_order(path: Path) -> list[str]:
    if not path.exists():
        return []
    titles: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^###\s+(.+)$", line)
        if not match:
            continue
        heading = match.group(1).strip()
        meta = re.match(r"^(.*?)\s+—\s+⭐\s+[0-9]+(?:\.[0-9]+)?/10\s+·\s+.+$", heading)
        titles.append((meta.group(1) if meta else heading).strip())
    return titles


def title_for_json(path: Path) -> str:
    data = unwrap(json.loads(path.read_text(encoding="utf-8")))
    return text_value(data.get("title") or path.stem)


def sample_cards(limit: int = 6) -> list[tuple[Path, Path]]:
    source_dir = ROOT / "data" / "compiled_adventures"
    files = sorted(
        p
        for p in source_dir.glob("*/*.json")
        if p.parent.name != "_catalogo" and not any(part.startswith("_") for part in p.relative_to(source_dir).parts)
    )
    by_title = {title_for_json(path): path for path in files}
    ordered: list[Path] = []
    used: set[Path] = set()
    for title in brief_title_order(BRIEF):
        path = by_title.get(title)
        if path and path not in used:
            ordered.append(path)
            used.add(path)
    ordered.extend(path for path in files if path not in used)
    return [(path, OUT_DIR / "assets" / f"{path.stem}_brief_card.png") for path in ordered[:limit]]


def draw_card(
    page: Image.Image,
    json_path: Path,
    image_path: Path,
    brief: dict[str, dict[str, str]],
    box: tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(page)
    data = unwrap(json.loads(json_path.read_text(encoding="utf-8")))
    title = text_value(data.get("title") or json_path.stem)
    entry = brief.get(title, {})
    flavor = entry.get("flavor") or text_value(data.get("premise"))
    quality = float(entry.get("score") or score(audit(data)))
    diff_label, diff_color = difficulty(data)
    genre = text_value(entry.get("brief_genre") or data.get("genre") or json_path.parent.name).upper()
    tone = text_value(data.get("tone"))
    accent = theme_color(data, json_path.parent.name)

    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    draw.rounded_rectangle(box, radius=7, fill=PALETTE["panel"], outline="#d1aa75", width=2)
    draw.rectangle((x1, y1, x1 + 9, y2), fill=accent)

    pad = 16
    img_size = min(178, h - pad * 2)
    poster = cover_crop(image_path, (img_size, img_size))
    img_x = x1 + pad + 9
    img_y = y1 + (h - img_size) // 2
    page.paste(poster, (img_x, img_y))
    draw.rectangle((img_x, img_y, img_x + img_size, img_y + img_size), outline="#fff8ed", width=3)

    tx = img_x + img_size + 24
    ty = y1 + 16
    tw = x2 - tx - 22
    bar_h = 47
    draw.rounded_rectangle((tx - 12, ty - 8, x2 - 18, ty - 8 + bar_h), radius=6, fill=accent)
    title_font = fit_title_font(draw, title, tw)
    title_y = ty + 1
    for line in wrap(draw, title, title_font, tw, 2):
        draw.text((tx, title_y), line, font=title_font, fill="#fff7e9")
        title_y += int(title_font.size * 1.04)

    meta_y = ty + bar_h + 8
    draw.text((tx, meta_y), f"{genre} / {shorten(tone, width=76, placeholder='...')}", font=F["subtitle"], fill=accent)

    desc_y = meta_y + 28
    pill_y = y2 - 38
    line_h = 24
    max_desc_lines = max(1, (pill_y - desc_y - 8) // line_h)
    draw_text(draw, flavor, tx, desc_y, tw, F["body"], PALETTE["ink"], max_desc_lines, line_h, ellipsis=False)

    pill_x = tx
    profiles = data.get("runtime_profiles") or ["scenario"]
    for profile in profiles[:3]:
        pill_x = light_pill(draw, profile_label(str(profile)), pill_x, pill_y + 2)
    pill_x = stat_pill(draw, f"punteggio {quality:.1f}", pill_x, pill_y, PALETTE["green"] if quality >= 8 else PALETTE["red"])
    pill_x = stat_pill(draw, diff_label, pill_x, pill_y, diff_color)
    pill_x = stat_pill(draw, f"{len(data.get('clues') or [])} indizi", pill_x, pill_y, PALETTE["blue"])
    pill_x = stat_pill(draw, f"{len(data.get('actors') or [])} PNG", pill_x, pill_y, PALETTE["blue"])
    stat_pill(draw, f"{len(data.get('locations') or [])} luoghi", pill_x, pill_y, PALETTE["blue"])


def main() -> int:
    brief = parse_brief(BRIEF)
    cards = sample_cards()

    page = Image.new("RGB", A4_PORTRAIT, PALETTE["paper"])
    draw = ImageDraw.Draw(page)
    draw.text((MARGIN, 26), "Schede avventura", font=F["page_title"], fill=PALETTE["ink"])
    draw.text((MARGIN, 69), "Prova A4 verticale 210 x 297 mm / 6 strisce a pagina", font=F["page_small"], fill=PALETTE["muted"])
    draw.line((MARGIN, 104, A4_PORTRAIT[0] - MARGIN, 104), fill=PALETTE["soft"], width=2)

    top = 126
    cols = 1
    rows = 6
    card_w = (A4_PORTRAIT[0] - MARGIN * 2 - GAP) // cols
    card_h = (A4_PORTRAIT[1] - top - MARGIN - GAP * (rows - 1)) // rows
    boxes = []
    for row in range(rows):
        for col in range(cols):
            x = MARGIN + col * (card_w + GAP)
            y = top + row * (card_h + GAP)
            boxes.append((x, y, x + card_w, y + card_h))
    for (json_path, image_path), box in zip(cards, boxes):
        draw_card(page, json_path, image_path, brief, box)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.save(OUT_PNG)
    page.save(OUT_PDF, "PDF", resolution=150.0)
    print(OUT_PNG.relative_to(ROOT))
    print(OUT_PDF.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
