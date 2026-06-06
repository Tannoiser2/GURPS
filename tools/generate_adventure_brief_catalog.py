#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.generate_adventure_brief_sample_page import (
    A4_PORTRAIT,
    BRIEF,
    F,
    GAP,
    MARGIN,
    OUT_DIR,
    PALETTE,
    draw_card,
    parse_brief,
    text_value,
    unwrap,
)


SOURCE_DIR = ROOT / "data" / "compiled_adventures"
ASSET_DIR = OUT_DIR / "assets"
OUT_PDF = OUT_DIR / "adventure_brief_catalog_A4_portrait_strips_6up.pdf"
OUT_PREVIEW = OUT_DIR / "adventure_brief_catalog_A4_portrait_strips_6up_page1.png"


def brief_order(path: Path) -> list[str]:
    if not path.exists():
        return []
    titles: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^###\s+(.+)$", line)
        if match:
            heading = match.group(1).strip()
            meta = re.match(r"^(.*?)\s+—\s+⭐\s+[0-9]+(?:\.[0-9]+)?/10\s+·\s+.+$", heading)
            titles.append((meta.group(1) if meta else heading).strip())
    return titles


def json_files() -> list[Path]:
    return sorted(
        p
        for p in SOURCE_DIR.glob("*/*.json")
        if p.parent.name != "_catalogo" and not any(part.startswith("_") for part in p.relative_to(SOURCE_DIR).parts)
    )


def title_for(path: Path) -> str:
    data = unwrap(json.loads(path.read_text(encoding="utf-8")))
    return text_value(data.get("title") or path.stem)


def ordered_files(files: list[Path], order: list[str]) -> list[Path]:
    by_title = {title_for(path): path for path in files}
    used: set[Path] = set()
    result: list[Path] = []
    for title in order:
        path = by_title.get(title)
        if path and path not in used:
            result.append(path)
            used.add(path)
    if order:
        return result
    result.extend(path for path in files if path not in used)
    return result


def image_for(json_path: Path) -> Path:
    return ASSET_DIR / f"{json_path.stem}_brief_card.png"


def page_boxes() -> list[tuple[int, int, int, int]]:
    top = 126
    rows = 6
    card_w = A4_PORTRAIT[0] - MARGIN * 2
    card_h = (A4_PORTRAIT[1] - top - MARGIN - GAP * (rows - 1)) // rows
    return [
        (MARGIN, top + row * (card_h + GAP), MARGIN + card_w, top + row * (card_h + GAP) + card_h)
        for row in range(rows)
    ]


def draw_header(page: Image.Image, page_num: int, total_pages: int, total_cards: int) -> None:
    draw = ImageDraw.Draw(page)
    draw.text((MARGIN, 26), "Schede avventura", font=F["page_title"], fill=PALETTE["ink"])
    draw.text(
        (MARGIN, 69),
        f"Catalogo A4 verticale / 6 strisce per pagina / {total_cards} avventure",
        font=F["page_small"],
        fill=PALETTE["muted"],
    )
    label = f"{page_num}/{total_pages}"
    bbox = draw.textbbox((0, 0), label, font=F["page_small"])
    draw.text((A4_PORTRAIT[0] - MARGIN - (bbox[2] - bbox[0]), 69), label, font=F["page_small"], fill=PALETTE["muted"])
    draw.line((MARGIN, 104, A4_PORTRAIT[0] - MARGIN, 104), fill=PALETTE["soft"], width=2)


def build_pages(cards: list[Path], brief: dict[str, dict[str, str]]) -> list[Image.Image]:
    boxes = page_boxes()
    total_pages = (len(cards) + len(boxes) - 1) // len(boxes)
    pages: list[Image.Image] = []
    for page_idx in range(total_pages):
        page = Image.new("RGB", A4_PORTRAIT, PALETTE["paper"])
        draw_header(page, page_idx + 1, total_pages, len(cards))
        chunk = cards[page_idx * len(boxes) : (page_idx + 1) * len(boxes)]
        for json_path, box in zip(chunk, boxes):
            draw_card(page, json_path, image_for(json_path), brief, box)
        pages.append(page)
    return pages


def main() -> int:
    brief = parse_brief(BRIEF)
    files = ordered_files(json_files(), brief_order(BRIEF))
    if not files:
        print("Nessun JSON trovato.")
        return 1

    pages = build_pages(files, brief)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages[0].save(OUT_PREVIEW)
    pages[0].save(OUT_PDF, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    missing_images = sum(1 for path in files if not image_for(path).exists())

    print(f"Avventure: {len(files)}")
    print(f"Pagine: {len(pages)}")
    print(f"Immagini mancanti: {missing_images}")
    print(OUT_PREVIEW.relative_to(ROOT))
    print(OUT_PDF.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
