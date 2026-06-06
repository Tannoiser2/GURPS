#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.generate_adventure_brief_catalog import json_files, title_for
from tools.generate_adventure_brief_sample_page import BRIEF, OUT_DIR, brief_title_order


CATALOG_DIR = ROOT / "data" / "compiled_adventures" / "_catalogo"
ASSET_DIR = CATALOG_DIR / "assets"
OUTPUT_SIZE = 1024

SHEET_GRIDS = {
    1: (4, 3, 12),
    2: (4, 3, 12),
    3: (4, 3, 12),
    4: (3, 4, 12),
    # Sheet 5 contains a 4x4 collage, but the brief sequence uses only
    # the first 12 cells. The final row is ignored.
    5: (4, 4, 12),
    6: (4, 3, 12),
}


def center_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def square_output(crop: Image.Image) -> Image.Image:
    return center_square(crop.convert("RGB")).resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.Resampling.LANCZOS)


def crop_cells(sheet: Image.Image, cols: int, rows: int, max_cells: int) -> list[Image.Image]:
    w, h = sheet.size
    cells: list[Image.Image] = []
    for row in range(rows):
        for col in range(cols):
            if len(cells) >= max_cells:
                return cells
            left = round(col * w / cols)
            right = round((col + 1) * w / cols)
            top = round(row * h / rows)
            bottom = round((row + 1) * h / rows)
            # Trim collage separator lines without eating meaningful image content.
            inset = 3
            crop = sheet.crop((left + inset, top + inset, right - inset, bottom - inset))
            cells.append(square_output(crop))
    return cells


def crop_sheet_7(sheet: Image.Image) -> list[Image.Image]:
    w, h = sheet.size
    inset = 3
    boxes = [
        (0 + inset, 0 + inset, w // 2 - inset, h // 2 - inset),
        (w // 2 + inset, 0 + inset, w - inset, h // 2 - inset),
        (0 + inset, h // 2 + inset, w - inset, h - inset),
    ]
    return [square_output(sheet.crop(box)) for box in boxes]


def main() -> int:
    titles = brief_title_order(BRIEF)
    by_title = {title_for(path): path for path in json_files()}
    missing = [title for title in titles if title not in by_title]
    if missing:
        print("Titoli nel brief senza JSON:")
        for title in missing:
            print(f"- {title}")
        return 1

    sheets = [CATALOG_DIR / f"{idx}.png" for idx in range(1, 8)]
    missing_sheets = [path for path in sheets if not path.exists()]
    if missing_sheets:
        print("Fogli collage mancanti:")
        for path in missing_sheets:
            print(f"- {path.relative_to(ROOT)}")
        return 1

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    title_idx = 0
    written: list[Path] = []
    for sheet_idx, sheet_path in enumerate(sheets, start=1):
        remaining = len(titles) - title_idx
        if sheet_idx == 7:
            max_cells = min(3, remaining)
        else:
            max_cells = min(SHEET_GRIDS[sheet_idx][2], remaining)
        sheet = Image.open(sheet_path).convert("RGB")
        cells = crop_sheet_7(sheet)[:max_cells] if sheet_idx == 7 else crop_cells(sheet, *SHEET_GRIDS[sheet_idx])[:max_cells]
        for cell in cells:
            title = titles[title_idx]
            json_path = by_title[title]
            out_path = ASSET_DIR / f"{json_path.stem}_brief_card.png"
            cell.save(out_path, "PNG")
            written.append(out_path)
            title_idx += 1
        print(f"{sheet_path.name}: estratte {max_cells} immagini")

    print(f"Immagini scritte: {len(written)}")
    print(f"Prima: {written[0].relative_to(ROOT)}")
    print(f"Ultima: {written[-1].relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
