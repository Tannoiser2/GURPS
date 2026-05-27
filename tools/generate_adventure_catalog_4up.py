#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import shorten
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data" / "compiled_adventures"
OUT_PDF = DEFAULT_ROOT / "adventure_catalog_4up_A4.pdf"
OUT_PREVIEW = DEFAULT_ROOT / "adventure_catalog_4up_A4_page1.png"

A4 = (1240, 1754)
MARGIN = 46
GAP = 28

PALETTES = {
    "action": ("#a84e2b", "#f5c07a"),
    "fantasy": ("#7b5b2a", "#e5c678"),
    "horror": ("#782a34", "#e5a0aa"),
    "mystery_horror": ("#5d334f", "#d8a7d6"),
    "investigation": ("#28645e", "#9bd7d1"),
    "detective_classico": ("#28645e", "#9bd7d1"),
    "romance": ("#934766", "#e9afc6"),
    "sci-fi": ("#2d6f9f", "#a4d9f4"),
    "mythic": ("#6c5aa8", "#c7bbff"),
}
DEFAULT_PALETTE = ("#596250", "#d8dfc8")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


F = {
    "title": font(40, True),
    "page": font(20, True),
    "card_title": font(25, True),
    "h": font(17, True),
    "body": font(16),
    "small": font(14),
    "tiny": font(11),
}


def text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return "; ".join(text_value(v) for v in value if text_value(v))
    if isinstance(value, dict):
        return "; ".join(f"{k}: {text_value(v)}" for k, v in value.items() if text_value(v))
    return str(value)


def unwrap(raw: dict[str, Any]) -> dict[str, Any]:
    return raw.get("adventure_definition", raw)


def files_under(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("*/*.json") if "_debug_pdf" not in p.parts)


def item_name(item: dict[str, Any], fallback: str) -> str:
    return text_value(item.get("name") or item.get("label") or item.get("title") or item.get("id") or fallback)


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, width: int, max_lines: int) -> list[str]:
    words = text_value(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(". ") + "..."
    return lines


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    width: int,
    fnt: ImageFont.ImageFont,
    fill: str,
    max_lines: int,
    line_height: int | None = None,
) -> int:
    line_height = line_height or int(getattr(fnt, "size", 14) * 1.25)
    for line in wrap_lines(draw, text, fnt, width, max_lines):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_height
    return y


def known_npcs(data: dict[str, Any]) -> str:
    actors = data.get("actors") or []
    parts = []
    for actor in actors[:4]:
        role = text_value(actor.get("role"))
        desc = text_value(actor.get("description") or actor.get("goal") or actor.get("motivation"))
        label = item_name(actor, "PNG")
        if role:
            label = f"{label} ({role})"
        if desc:
            label = f"{label}: {shorten(desc, width=75, placeholder='...')}"
        parts.append(label)
    return "; ".join(parts) if parts else "Nessun PNG esplicito nel JSON."


def player_intro(data: dict[str, Any]) -> str:
    return text_value(data.get("premise") or data.get("initial_hook") or "Premessa non specificata.")


def objective(data: dict[str, Any]) -> str:
    if data.get("player_facing_objective"):
        return text_value(data["player_facing_objective"])
    objectives = data.get("objectives") or []
    if objectives:
        return text_value(objectives[0].get("label") or objectives[0].get("description") or objectives[0])
    finales = data.get("finale_conditions") or []
    if finales and isinstance(finales[0], dict):
        return text_value(finales[0].get("label") or finales[0].get("method"))
    return "Scopo non specificato nel JSON."


def draw_card(draw: ImageDraw.ImageDraw, path: Path, box: tuple[int, int, int, int]) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = unwrap(raw)

    x1, y1, x2, y2 = box
    w = x2 - x1
    genre = text_value(data.get("genre") or path.parent.name)
    bg, accent = PALETTES.get(genre.lower(), PALETTES.get(path.parent.name.lower(), DEFAULT_PALETTE))
    panel_bg = "#121915"
    ink = "#f4ecdc"
    muted = "#c9bea9"

    draw.rounded_rectangle(box, radius=10, fill=panel_bg, outline=bg, width=3)

    sq = 150
    sx, sy = x1 + 18, y1 + 22
    draw.rounded_rectangle((sx, sy, sx + sq, sy + sq), radius=8, fill=bg, outline=accent, width=2)
    draw.text((sx + 16, sy + 18), genre[:2].upper(), font=font(38, True), fill="#fff7e6")
    draw.text((sx + 16, sy + 72), path.parent.name.upper()[:10], font=F["tiny"], fill="#fff7e6")

    tx = sx + sq + 18
    title = text_value(data.get("title") or path.stem)
    draw_text_block(draw, title, tx, sy, w - sq - 54, F["card_title"], ink, 2, 30)
    draw.text((tx, sy + 68), f"{genre} | {path.stem}", font=F["small"], fill=accent)

    y = sy + sq + 18
    content_x = x1 + 18
    content_w = w - 36

    draw.text((content_x, y), "INTRO PER I PG", font=F["h"], fill=accent)
    y = draw_text_block(draw, player_intro(data), content_x, y + 23, content_w, F["body"], ink, 4, 20)
    y += 10

    draw.text((content_x, y), "PNG NOTI", font=F["h"], fill=accent)
    y = draw_text_block(draw, known_npcs(data), content_x, y + 23, content_w, F["small"], muted, 4, 18)
    y += 10

    draw.text((content_x, y), "SCOPO DELL'AVVENTURA", font=F["h"], fill=accent)
    draw_text_block(draw, objective(data), content_x, y + 23, content_w, F["body"], ink, 4, 20)


def build_pages(files: list[Path]) -> list[Image.Image]:
    pages: list[Image.Image] = []
    card_w = (A4[0] - 2 * MARGIN - GAP) // 2
    card_h = 735
    card_boxes = [
        (MARGIN, 150, MARGIN + card_w, 150 + card_h),
        (MARGIN + card_w + GAP, 150, MARGIN + 2 * card_w + GAP, 150 + card_h),
        (MARGIN, 150 + card_h + GAP, MARGIN + card_w, 150 + 2 * card_h + GAP),
        (MARGIN + card_w + GAP, 150 + card_h + GAP, MARGIN + 2 * card_w + GAP, 150 + 2 * card_h + GAP),
    ]

    for page_idx in range(0, len(files), 4):
        page_files = files[page_idx : page_idx + 4]
        img = Image.new("RGB", A4, "#211a16")
        draw = ImageDraw.Draw(img)
        draw.text((MARGIN, 42), "CATALOGO AVVENTURE GAME MASTER", font=F["title"], fill="#f5ecdc")
        draw.text(
            (MARGIN, 92),
            f"4 avventure per pagina | {len(files)} JSON | pagina {page_idx // 4 + 1}",
            font=F["page"],
            fill="#d5ae6b",
        )
        for path, box in zip(page_files, card_boxes):
            draw_card(draw, path, box)
        draw.text((MARGIN, A4[1] - 38), "Placeholder colore: immagine da aggiungere in seguito", font=F["tiny"], fill="#b9ad9d")
        pages.append(img)
    return pages


def main() -> int:
    root = DEFAULT_ROOT
    files = files_under(root)
    if not files:
        print("Nessun JSON trovato")
        return 1
    pages = build_pages(files)
    pages[0].save(OUT_PDF, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    pages[0].save(OUT_PREVIEW)
    print(f"JSON: {len(files)}")
    print(f"Pagine: {len(pages)}")
    print(OUT_PDF.relative_to(ROOT))
    print(OUT_PREVIEW.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
