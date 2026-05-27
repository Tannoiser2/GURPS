#!/usr/bin/env python3
"""
Generate two-page A4 PDF infographic sheets for compiled GameMaster adventures.

Each output PDF contains:
  1. Player-facing overview, spoiler-light.
  2. GM analysis sheet with spoilers, clues, NPCs, clocks, audit findings and fixes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from textwrap import shorten
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.json_doctor.rules import audit, score

DEFAULT_DIR = ROOT / "data" / "compiled_adventures"

A4 = (1240, 1754)
MARGIN = 58
GAP = 18

FONT_REGULAR_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)
FONT_BOLD_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)

PALETTES = {
    "fantasy": {"bg": "#f4efe2", "ink": "#27221b", "muted": "#675f51", "accent": "#7c5a24", "soft": "#e6d7b8", "card": "#fffaf0"},
    "horror": {"bg": "#eee9e4", "ink": "#241f22", "muted": "#675b62", "accent": "#8b2734", "soft": "#dbc7cb", "card": "#fbf8f5"},
    "mystery_horror": {"bg": "#eee9e4", "ink": "#241f22", "muted": "#675b62", "accent": "#8b2734", "soft": "#dbc7cb", "card": "#fbf8f5"},
    "investigation": {"bg": "#edf1ee", "ink": "#1f2926", "muted": "#586660", "accent": "#286b63", "soft": "#c8dcd5", "card": "#fbfdfb"},
    "action": {"bg": "#f1eee8", "ink": "#252525", "muted": "#63615c", "accent": "#a94d25", "soft": "#e1c7b5", "card": "#fffaf5"},
    "sci-fi": {"bg": "#eef2f6", "ink": "#1d2530", "muted": "#566473", "accent": "#2c6f9e", "soft": "#c6d9e8", "card": "#fbfdff"},
    "romance": {"bg": "#f4edf0", "ink": "#2a2025", "muted": "#6c5b62", "accent": "#9b4162", "soft": "#e5c9d4", "card": "#fff9fb"},
}
DEFAULT_PALETTE = {"bg": "#f1efe9", "ink": "#242424", "muted": "#62605c", "accent": "#536d48", "soft": "#d5ddc8", "card": "#fffdf8"}

POSTER = {
    "bg": "#07151b",
    "panel": "#0e2530",
    "panel2": "#132f3b",
    "ink": "#f3ead8",
    "muted": "#b8c3bd",
    "line": "#c38a32",
    "blue": "#4aa3d8",
    "green": "#57b56b",
    "purple": "#9b63c7",
    "red": "#c84e3c",
    "gold": "#d9a441",
    "black": "#050b0f",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


F = {
    "title": font(50, True),
    "subtitle": font(26, True),
    "h": font(25, True),
    "body": font(21),
    "small": font(17),
    "tiny": font(14),
    "metric": font(33, True),
    "poster_title": font(58, True),
    "poster_title_small": font(44, True),
    "poster_title_tiny": font(36, True),
    "poster_h": font(23, True),
    "poster_body": font(16),
    "poster_small": font(14),
    "poster_tiny": font(12),
    "poster_num": font(30, True),
}


def unwrap(raw: dict[str, Any]) -> dict[str, Any]:
    return raw.get("adventure_definition", raw)


def text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return "; ".join(text_value(v) for v in value if text_value(v))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item:
                parts.append(f"{key}: {text_value(item)}")
        return "; ".join(parts)
    return str(value)


def first_text(*values: Any, max_len: int = 320) -> str:
    for value in values:
        txt = text_value(value)
        if txt:
            return shorten(txt, width=max_len, placeholder="...")
    return "Non specificato nel JSON."


def item_name(item: dict[str, Any], fallback: str = "Elemento") -> str:
    return text_value(item.get("name") or item.get("label") or item.get("title") or item.get("id") or fallback)


def palette_for(data: dict[str, Any], category: str) -> dict[str, str]:
    genre = text_value(data.get("genre")).lower()
    return PALETTES.get(genre) or PALETTES.get(category.lower()) or DEFAULT_PALETTE


def files_under(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(
        p for p in target.rglob("*.json")
        if not any(part.startswith("_") for part in p.relative_to(target).parts)
    )


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, width: int) -> list[str]:
    text = re.sub(r"\s+", " ", text_value(text)).strip()
    if not text:
        return []
    words = text.split(" ")
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
    return lines


def fit_lines(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    clipped = lines[:max_lines]
    clipped[-1] = clipped[-1].rstrip(". ") + "..."
    return clipped


def pixel_shorten(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, width: int) -> str:
    text = text_value(text)
    if draw.textbbox((0, 0), text, font=fnt)[2] <= width:
        return text
    ell = "..."
    while text and draw.textbbox((0, 0), text + ell, font=fnt)[2] > width:
        text = text[:-1].rstrip()
    return (text + ell) if text else ell


def fit_font(draw: ImageDraw.ImageDraw, text: str, fonts: list[ImageFont.ImageFont], width: int) -> ImageFont.ImageFont:
    for fnt in fonts:
        if draw.textbbox((0, 0), text, font=fnt)[2] <= width:
            return fnt
    return fonts[-1]


class Page:
    def __init__(self, title: str, subtitle: str, palette: dict[str, str], footer: str):
        self.img = Image.new("RGB", A4, palette["bg"])
        self.draw = ImageDraw.Draw(self.img)
        self.p = palette
        self.y = MARGIN
        self.footer = footer
        self.header(title, subtitle)

    def header(self, title: str, subtitle: str) -> None:
        self.draw.rounded_rectangle((0, 0, A4[0], 188), radius=0, fill=self.p["accent"])
        self.draw.rectangle((0, 168, A4[0], 188), fill=self.p["soft"])
        self.draw.text((MARGIN, 42), shorten(title, width=42, placeholder="..."), fill="white", font=F["title"])
        self.draw.text((MARGIN, 112), subtitle, fill="#fff8ed", font=F["subtitle"])
        self.y = 220

    def section(self, title: str, x: int, y: int, w: int, h: int, fill: str | None = None) -> int:
        fill = fill or self.p["card"]
        self.draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=fill, outline=self.p["soft"], width=2)
        self.draw.text((x + 18, y + 14), title.upper(), fill=self.p["accent"], font=F["h"])
        return y + 50

    def paragraph(self, text: str, x: int, y: int, w: int, fnt: ImageFont.ImageFont | None = None, fill: str | None = None, max_lines: int = 8) -> int:
        fnt = fnt or F["body"]
        fill = fill or self.p["ink"]
        lines = fit_lines(wrap_text(self.draw, text, fnt, w), max_lines)
        line_h = int(fnt.size * 1.28)
        for line in lines:
            self.draw.text((x, y), line, fill=fill, font=fnt)
            y += line_h
        return y

    def bullet_list(self, items: Iterable[str], x: int, y: int, w: int, max_items: int, max_lines_each: int = 2) -> int:
        count = 0
        for raw in items:
            if count >= max_items:
                break
            text = text_value(raw)
            if not text:
                continue
            lines = fit_lines(wrap_text(self.draw, text, F["small"], w - 25), max_lines_each)
            if not lines:
                continue
            self.draw.ellipse((x, y + 7, x + 8, y + 15), fill=self.p["accent"])
            for idx, line in enumerate(lines):
                self.draw.text((x + 22, y), line, fill=self.p["ink"], font=F["small"])
                y += 22
            y += 8
            count += 1
        return y

    def metric(self, label: str, value: int | str, x: int, y: int, w: int) -> None:
        self.draw.rounded_rectangle((x, y, x + w, y + 76), radius=8, fill=self.p["soft"])
        self.draw.text((x + 16, y + 10), str(value), fill=self.p["accent"], font=F["metric"])
        self.draw.text((x + 78, y + 25), label, fill=self.p["ink"], font=F["small"])

    def footer_line(self) -> None:
        self.draw.line((MARGIN, A4[1] - 55, A4[0] - MARGIN, A4[1] - 55), fill=self.p["soft"], width=2)
        self.draw.text((MARGIN, A4[1] - 38), self.footer, fill=self.p["muted"], font=F["tiny"])


def player_known(data: dict[str, Any]) -> list[str]:
    items = [
        first_text(data.get("initial_hook"), data.get("player_facing_objective"), max_len=210),
    ]
    for obj in data.get("objectives", [])[:3]:
        items.append(first_text(obj.get("label"), obj.get("description"), max_len=150))
    for loc in data.get("locations", [])[:3]:
        if loc.get("is_starting_location") or len(items) < 4:
            items.append(f"{item_name(loc, 'Luogo')}: {first_text(loc.get('description'), loc.get('visual_identity'), max_len=130)}")
    for resource in data.get("resources", [])[:2]:
        items.append(f"Risorsa: {item_name(resource)}")
    return [i for i in items if i and i != "Non specificato nel JSON."]


def player_page(data: dict[str, Any], path: Path, category: str) -> Image.Image:
    p = palette_for(data, category)
    title = first_text(data.get("title"), path.stem, max_len=80)
    subtitle = f"Scheda giocatori | {category} | {first_text(data.get('genre'), category, max_len=40)}"
    page = Page(title, subtitle, p, f"{path.name} - pagina giocatori senza spoiler maggiori")

    page.section("Presentazione", MARGIN, 230, 1124, 310)
    page.paragraph(first_text(data.get("premise"), data.get("initial_hook"), max_len=720), MARGIN + 22, 286, 1080, max_lines=8)

    w = 260
    y = 575
    counts = [("NPC", len(data.get("actors", []))), ("Luoghi", len(data.get("locations", []))), ("Indizi", len(data.get("clues", []))), ("Clock", len(data.get("event_clocks", [])))]
    for i, (label, value) in enumerate(counts):
        page.metric(label, value, MARGIN + i * (w + 28), y, w)

    page.section("Cose note prima di iniziare", MARGIN, 690, 544, 650)
    page.bullet_list(player_known(data), MARGIN + 22, 750, 500, max_items=9, max_lines_each=3)

    page.section("Obiettivi visibili", 638, 690, 544, 300)
    objective_items = []
    if data.get("player_facing_objective"):
        objective_items.append(data["player_facing_objective"])
    objective_items.extend(first_text(o.get("label"), o.get("description"), max_len=170) for o in data.get("objectives", [])[:5])
    page.bullet_list(objective_items, 660, 750, 500, max_items=5, max_lines_each=3)

    page.section("Cast iniziale e tono", 638, 1022, 544, 318)
    actor_items = []
    for actor in data.get("actors", [])[:5]:
        role = text_value(actor.get("role")) or "ruolo aperto"
        actor_items.append(f"{item_name(actor)} ({role}): {first_text(actor.get('description'), actor.get('motivation'), max_len=115)}")
    if data.get("tone"):
        actor_items.insert(0, f"Tono: {text_value(data.get('tone'))}")
    page.bullet_list(actor_items, 660, 1082, 500, max_items=6, max_lines_each=2)

    page.section("Avvertenze al tavolo", MARGIN, 1372, 1124, 260, fill="#fffdf9")
    warnings = [
        "La scheda non rivela la verita nascosta: il GM deve usare la pagina successiva.",
        "Gli elementi elencati sono materiale di partenza, non soluzioni obbligate.",
        "Se i PG seguono strade inattese, usare NPC, indizi e clock come strumenti mobili."
    ]
    page.bullet_list(warnings, MARGIN + 22, 1432, 1076, max_items=4, max_lines_each=2)
    page.footer_line()
    return page.img


def clue_summary(clue: dict[str, Any]) -> str:
    bits = [item_name(clue, "Indizio")]
    reveals = first_text(clue.get("reveals"), clue.get("payoff"), clue.get("hidden_implication"), max_len=140)
    if reveals != "Non specificato nel JSON.":
        bits.append(reveals)
    return ": ".join(bits)


def gm_page(data: dict[str, Any], path: Path, category: str) -> Image.Image:
    p = palette_for(data, category)
    title = first_text(data.get("title"), path.stem, max_len=80)
    findings = audit(data)
    s = score(findings)
    sev = Counter(f.severity for f in findings)
    subtitle = f"Scheda GM | score JSON Doctor {s:.1f}/10 | {sev['critical']} critici, {sev['warning']} warning, {sev['info']} info"
    page = Page(title, subtitle, p, f"{path.name} - pagina GM con spoiler, audit e fix")

    page.section("Verita nascosta e posta in gioco", MARGIN, 230, 1124, 292)
    hidden = first_text(data.get("hidden_truth"), data.get("core_truths"), data.get("revelations"), max_len=680)
    page.paragraph(hidden, MARGIN + 22, 286, 1080, max_lines=7)

    page.section("Indizi chiave", MARGIN, 550, 544, 430)
    page.bullet_list((clue_summary(c) for c in data.get("clues", [])[:9]), MARGIN + 22, 610, 500, max_items=8, max_lines_each=2)

    page.section("NPC e piani", 638, 550, 544, 430)
    actor_items = []
    for actor in data.get("actors", [])[:7]:
        plan = first_text(actor.get("current_plan"), actor.get("motivation"), actor.get("secret"), max_len=130)
        actor_items.append(f"{item_name(actor)}: {plan}")
    page.bullet_list(actor_items, 660, 610, 500, max_items=7, max_lines_each=2)

    page.section("Luoghi, clock e finali", MARGIN, 1010, 544, 405)
    loc_items = []
    for loc in data.get("locations", [])[:5]:
        loc_items.append(f"{item_name(loc)}: {first_text(loc.get('gameplay_function'), loc.get('description'), max_len=105)}")
    for clock in data.get("event_clocks", [])[:3]:
        loc_items.append(f"Clock {item_name(clock)}: max {clock.get('max_value', '?')}, tick/fail {clock.get('ticks_per_failure', '?')}")
    if data.get("finale_conditions"):
        loc_items.append("Finali: " + first_text(data.get("finale_conditions"), max_len=120))
    page.bullet_list(loc_items, MARGIN + 22, 1070, 500, max_items=8, max_lines_each=2)

    page.section("Audit e fix suggeriti", 638, 1010, 544, 405)
    if findings:
        fix_items = []
        for f in findings[:8]:
            prefix = {"critical": "CRIT", "warning": "WARN", "info": "INFO"}.get(f.severity, f.severity.upper())
            fix = f.fix_hint or f.message
            fix_items.append(f"{prefix} {f.category}/{f.entity_id}: {shorten(f.message + ' - Fix: ' + fix, width=170, placeholder='...')}")
        page.bullet_list(fix_items, 660, 1070, 500, max_items=8, max_lines_each=2)
    else:
        page.paragraph("Nessun finding rilevato dalle regole automatiche. Resta utile una lettura umana per coerenza tematica, pacing e nomi.", 660, 1070, 500, max_lines=4)

    page.section("Checklist coerenza", MARGIN, 1445, 1124, 172)
    checklist = [
        "Ogni verita importante ha almeno due indizi indipendenti o un recupero se l'indizio viene perso.",
        "Ogni antagonista ha pressione, piano corrente, fallback e reazioni a prove/minacce/corruzione.",
        "I clock hanno conseguenze visibili, condizione di risoluzione e segnali anticipatori.",
        "I luoghi iniziali collegano hook, NPC e primo indizio senza bloccare l'avventura."
    ]
    page.bullet_list(checklist, MARGIN + 22, 1505, 1076, max_items=4, max_lines_each=1)
    page.footer_line()
    return page.img


def poster_bg(draw: ImageDraw.ImageDraw, genre: str) -> None:
    draw.rectangle((0, 0, A4[0], A4[1]), fill=POSTER["bg"])
    for y in range(0, A4[1], 18):
        shade = 16 + int(30 * y / A4[1])
        draw.line((0, y, A4[0], y), fill=(5, shade, shade + 8), width=18)
    if "sci" in genre:
        for i in range(0, A4[0], 82):
            draw.line((i, 190, i + 140, 1500), fill="#12394a", width=1)
        for i in range(70):
            x = (i * 97) % A4[0]
            y = 210 + (i * 53) % 1180
            draw.ellipse((x, y, x + 2, y + 2), fill="#89c8e8")
    elif "horror" in genre or "investigation" in genre:
        for i in range(14):
            x = 30 + i * 90
            draw.rectangle((x, 640 - (i % 5) * 28, x + 58, 1390), fill="#0a1d26", outline="#173541")
            draw.rectangle((x + 12, 680, x + 22, 690), fill="#d59c39")
            draw.rectangle((x + 36, 760, x + 46, 770), fill="#d59c39")
    elif "action" in genre:
        for i in range(18):
            y = 360 + i * 62
            draw.line((0, y, A4[0], y + 80), fill="#26312b", width=6)
        draw.line((140, 210, 1040, 1440), fill="#594128", width=28)
        draw.line((160, 210, 1060, 1440), fill="#0b1518", width=12)
    else:
        base = 1260
        for ridge, color in [(0, "#1f4651"), (90, "#17333f"), (180, "#102832")]:
            pts = [(0, base - ridge)]
            for i in range(0, A4[0] + 120, 120):
                peak = base - ridge - 170 - ((i * 37) % 150)
                pts.append((i, peak))
                pts.append((i + 65, base - ridge - 40 - ((i * 19) % 80)))
            pts.extend([(A4[0], A4[1]), (0, A4[1])])
            draw.polygon(pts, fill=color)
    draw.rectangle((0, 0, A4[0], A4[1]), outline=POSTER["line"], width=4)


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str = "", outline: str | None = None, fill: str | None = None) -> None:
    outline = outline or POSTER["line"]
    fill = fill or "#0b1b23"
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=2)
    if title:
        draw.text((box[0] + 14, box[1] + 10), title.upper(), fill=POSTER["gold"], font=F["poster_h"])


def poster_text(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, w: int, max_lines: int, fnt: ImageFont.ImageFont | None = None, fill: str | None = None) -> int:
    fnt = fnt or F["poster_body"]
    fill = fill or POSTER["ink"]
    lines = fit_lines(wrap_text(draw, text, fnt, w), max_lines)
    for line in lines:
        draw.text((x, y), line, fill=fill, font=fnt)
        y += int(fnt.size * 1.28)
    return y


def bullet(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, w: int, color: str = "#d9a441", max_lines: int = 2) -> int:
    lines = fit_lines(wrap_text(draw, text, F["poster_small"], w - 20), max_lines)
    if not lines:
        return y
    draw.ellipse((x, y + 6, x + 7, y + 13), fill=color)
    for line in lines:
        draw.text((x + 18, y), line, fill=POSTER["ink"], font=F["poster_small"])
        y += 18
    return y + 7


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, width: int = 4, dashed: bool = False) -> None:
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    dist = max(1, math.hypot(dx, dy))
    ux, uy = dx / dist, dy / dist
    if dashed:
        step = 22
        gap = 12
        t = 0
        while t < dist - 20:
            a = t
            b = min(t + step, dist - 20)
            draw.line((x1 + ux * a, y1 + uy * a, x1 + ux * b, y1 + uy * b), fill=color, width=width)
            t += step + gap
    else:
        draw.line((x1, y1, x2, y2), fill=color, width=width)
    ah = 16
    left = (-uy, ux)
    tip = (x2, y2)
    base = (x2 - ux * ah, y2 - uy * ah)
    draw.polygon([
        tip,
        (base[0] + left[0] * 7, base[1] + left[1] * 7),
        (base[0] - left[0] * 7, base[1] - left[1] * 7),
    ], fill=color)


def location_flags(loc: dict[str, Any], idx: int, degree: int) -> tuple[str, str]:
    if loc.get("is_starting_location") or idx == 0:
        return "PUNTO DI PARTENZA", POSTER["red"]
    if degree >= 3:
        return "HUB", POSTER["blue"]
    if loc.get("locked_paths"):
        return "GATE", POSTER["gold"]
    if loc.get("hazards"):
        return "PERICOLO", POSTER["red"]
    return "SCENA", POSTER["green"]


def thumb(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], genre: str, seed: int) -> None:
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill="#162b33")
    if "horror" in genre or "investigation" in genre:
        draw.rectangle((x1, y1 + 45, x2, y2), fill="#10171b")
        for i in range(4):
            bx = x1 + 18 + i * 45 + (seed % 17)
            draw.rectangle((bx, y1 + 35 - i * 4, bx + 28, y2), fill="#27313a")
            draw.rectangle((bx + 8, y1 + 55, bx + 15, y1 + 64), fill="#d69b3d")
        draw.ellipse((x2 - 58, y1 + 12, x2 - 25, y1 + 45), fill="#c8d6d0")
    elif "sci" in genre:
        draw.rectangle((x1, y1, x2, y2), fill="#0d2533")
        draw.ellipse((x1 + 30, y1 + 18, x2 - 30, y2 + 50), outline="#4aa3d8", width=3)
        draw.rectangle((x1 + 54, y1 + 56, x2 - 54, y1 + 78), fill="#8fd5f2")
    elif "action" in genre:
        draw.rectangle((x1, y1 + 50, x2, y2), fill="#3c2a1d")
        draw.line((x1, y2 - 14, x2, y1 + 44), fill="#c47b2e", width=5)
        draw.rectangle((x1 + 40, y1 + 55, x1 + 110, y1 + 85), fill="#15191c")
    else:
        draw.rectangle((x1, y1, x2, y2), fill="#193744")
        pts = [(x1, y2), (x1 + 50, y1 + 28), (x1 + 120, y2), (x1 + 180, y1 + 18), (x2, y2)]
        draw.polygon(pts, fill="#dce3df")
        draw.polygon([(x1, y2), (x1 + 45, y1 + 62), (x1 + 115, y2), (x1 + 165, y1 + 70), (x2, y2)], fill="#335a61")
    draw.rectangle(box, outline="#d59c39", width=1)


def collect_edges(locations: list[dict[str, Any]]) -> list[tuple[int, int]]:
    index = {loc.get("id"): i for i, loc in enumerate(locations)}
    edges: set[tuple[int, int]] = set()
    for i, loc in enumerate(locations):
        for ex in loc.get("exits") or []:
            if ex in index:
                a, b = i, index[ex]
                edges.add((min(a, b), max(a, b)))
    if not edges and len(locations) > 1:
        edges = {(i, i + 1) for i in range(len(locations) - 1)}
    return sorted(edges)


def visual_player_page(data: dict[str, Any], path: Path, category: str) -> Image.Image:
    genre = first_text(data.get("genre"), category, max_len=40).lower()
    title = first_text(data.get("title"), path.stem, max_len=80)
    locations = list(data.get("locations", []))[:8]
    edges = collect_edges(locations)
    degree = Counter()
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1

    img = Image.new("RGB", A4, POSTER["bg"])
    d = ImageDraw.Draw(img)
    poster_bg(d, genre)

    title_font = fit_font(d, title.upper(), [F["poster_title"], F["poster_title_small"], F["poster_title_tiny"]], 660)
    d.text((36, 30), pixel_shorten(d, title.upper(), title_font, 660), fill=POSTER["ink"], font=title_font)
    d.text((38, 105), "MAPPA DELLE LOCATION CONNESSE", fill="#8fd5f2", font=F["subtitle"])
    d.text((38, 146), "RUNTIME LOCATION GRAPH", fill=POSTER["ink"], font=F["poster_h"])

    panel(d, (720, 28, 965, 154), "Panoramica")
    poster_text(d, first_text(data.get("premise"), data.get("initial_hook"), max_len=230), 736, 70, 210, 4, F["poster_tiny"])

    panel(d, (985, 28, 1200, 174), "Legenda")
    legend = [("->", "Movimento / accesso", POSTER["green"]), ("--", "Percorso alternativo", POSTER["purple"]), ("!", "Trigger / pericolo", POSTER["red"]), ("?", "Indagine / indizi", POSTER["blue"]), ("#", "Gate narrativo", POSTER["gold"])]
    y = 68
    for sym, label, col in legend:
        d.text((1000, y), sym, fill=col, font=F["poster_body"])
        d.text((1032, y), label, fill=POSTER["ink"], font=F["poster_tiny"])
        y += 20

    positions = [
        (44, 240, 330, 485),
        (390, 500, 650, 700),
        (500, 235, 760, 455),
        (900, 245, 1182, 510),
        (645, 740, 905, 960),
        (380, 1025, 650, 1245),
        (900, 875, 1182, 1115),
        (42, 790, 330, 1035),
    ]
    centers: list[tuple[int, int]] = []
    for idx in range(len(locations)):
        x1, y1, x2, y2 = positions[idx]
        centers.append(((x1 + x2) // 2, (y1 + y2) // 2))

    for n, (a, b) in enumerate(edges):
        color = POSTER["green"] if n % 3 == 0 else (POSTER["purple"] if n % 3 == 1 else POSTER["gold"])
        draw_arrow(d, centers[a], centers[b], color, 4, dashed=(n % 3 != 0))

    for idx, loc in enumerate(locations):
        x1, y1, x2, y2 = positions[idx]
        tag, col = location_flags(loc, idx, degree[idx])
        panel(d, (x1, y1, x2, y2), "", outline=col, fill="#0b1b23")
        d.ellipse((x1 + 10, y1 + 10, x1 + 58, y1 + 58), fill=col, outline=POSTER["ink"], width=2)
        d.text((x1 + 25, y1 + 17), str(idx + 1), fill="white", font=F["poster_num"])
        d.text((x1 + 70, y1 + 15), pixel_shorten(d, item_name(loc).upper(), F["poster_h"], x2 - x1 - 84), fill=POSTER["ink"], font=F["poster_h"])
        d.text((x1 + 70, y1 + 42), tag, fill=col, font=F["poster_small"])
        thumb(d, (x1 + 14, y1 + 68, x2 - 14, y1 + 138), genre, idx)
        y = y1 + 150
        details = [
            first_text(loc.get("description"), loc.get("visual_identity"), max_len=95),
        ]
        if loc.get("clue_slots"):
            details.append("Indizi: " + ", ".join(map(str, loc.get("clue_slots")[:3])))
        if loc.get("hazards"):
            details.append("Pericoli: " + first_text(loc.get("hazards"), max_len=90))
        if loc.get("locked_paths"):
            details.append("Gate: " + first_text(loc.get("locked_paths"), max_len=90))
        for detail in details[:4]:
            y = bullet(d, detail, x1 + 18, y, x2 - x1 - 34, color=col, max_lines=2)

    panel(d, (42, 520, 330, 715), "Tipi collegamento")
    for yy, col, label, dashed in [(570, POSTER["green"], "Percorso principale", False), (610, POSTER["purple"], "Percorso secondario", True), (650, POSTER["gold"], "Gate / requisito", True), (690, POSTER["red"], "Zona pericolosa", True)]:
        draw_arrow(d, (70, yy), (155, yy), col, 3, dashed=dashed)
        d.text((174, yy - 10), label, fill=POSTER["ink"], font=F["poster_small"])

    panel(d, (700, 1182, 1198, 1396), "Percorsi principali")
    if locations:
        start = 1
        final = min(len(locations), 8)
        routes = [
            f"{start} -> {final}: approccio diretto",
            f"{start} -> 2 -> {final}: rotta con hub",
            f"{start} -> 3 -> {final}: rotta indizi",
            "Tutti i percorsi possono convergere sul finale"
        ]
        y = 1232
        for route in routes:
            y = bullet(d, route, 724, y, 450, color=POSTER["green"], max_lines=1)

    finales = data.get("finale_conditions") or []
    panel(d, (42, 1430, 1198, 1650), "Esiti finali principali")
    fx = 58
    for idx, finale in enumerate(finales[:3] if isinstance(finales, list) else []):
        box = (fx + idx * 375, 1488, fx + idx * 375 + 350, 1622)
        col = [POSTER["green"], POSTER["gold"], POSTER["red"]][idx % 3]
        panel(d, box, "", outline=col, fill="#10232a")
        d.ellipse((box[0] + 12, box[1] + 12, box[0] + 52, box[1] + 52), fill=col)
        d.text((box[0] + 26, box[1] + 18), chr(65 + idx), fill="white", font=F["poster_h"])
        d.text((box[0] + 66, box[1] + 16), pixel_shorten(d, item_name(finale).upper(), F["poster_h"], box[2] - box[0] - 84), fill=POSTER["ink"], font=F["poster_h"])
        poster_text(d, first_text(finale.get("description"), finale.get("method"), max_len=150), box[0] + 18, box[1] + 62, 310, 3, F["poster_small"])
    if not finales:
        poster_text(d, "Finali non specificati nel JSON: usare la pagina GM per identificare possibili condizioni di uscita.", 64, 1490, 1040, 3, F["poster_body"])

    d.text((44, 1688), f"{path.name} - pagina giocatori / runtime graph", fill=POSTER["muted"], font=F["poster_tiny"])
    return img


def visual_gm_page(data: dict[str, Any], path: Path, category: str) -> Image.Image:
    genre = first_text(data.get("genre"), category, max_len=40).lower()
    title = first_text(data.get("title"), path.stem, max_len=80)
    findings = audit(data)
    sev = Counter(f.severity for f in findings)
    s = score(findings)
    img = Image.new("RGB", A4, POSTER["bg"])
    d = ImageDraw.Draw(img)
    poster_bg(d, genre)
    d.text((36, 30), pixel_shorten(d, title.upper(), F["poster_title"], 1120), fill=POSTER["ink"], font=F["poster_title"])
    d.text((38, 106), "SCHEDA GM: SPOILER, INDIZI, BUG E FIX", fill="#8fd5f2", font=F["subtitle"])
    d.text((38, 146), f"JSON DOCTOR SCORE {s:.1f}/10 - {sev['critical']} critici, {sev['warning']} warning, {sev['info']} info", fill=POSTER["ink"], font=F["poster_h"])

    panel(d, (44, 220, 1196, 410), "Verita nascosta")
    poster_text(d, first_text(data.get("hidden_truth"), data.get("core_truths"), data.get("revelations"), max_len=560), 66, 270, 1100, 5, F["poster_body"])

    panel(d, (44, 440, 600, 820), "Indizi e rivelazioni")
    y = 492
    for clue in data.get("clues", [])[:9]:
        y = bullet(d, clue_summary(clue), 66, y, 500, color=POSTER["blue"], max_lines=2)

    panel(d, (630, 440, 1196, 820), "NPC, pressione e piani")
    y = 492
    for actor in data.get("actors", [])[:8]:
        role = text_value(actor.get("role")) or "npc"
        plan = first_text(actor.get("current_plan"), actor.get("motivation"), actor.get("secret"), max_len=130)
        y = bullet(d, f"{item_name(actor)} ({role}): {plan}", 652, y, 510, color=POSTER["gold"], max_lines=2)

    panel(d, (44, 850, 600, 1225), "Clock, gate e pericoli")
    y = 902
    for clock in data.get("event_clocks", [])[:5]:
        label = item_name(clock)
        y = bullet(d, f"{label}: max {clock.get('max_value', '?')}, tick/fail {clock.get('ticks_per_failure', '?')}. {first_text(clock.get('resolution_condition'), clock.get('discovery_hint'), max_len=110)}", 66, y, 500, color=POSTER["red"], max_lines=2)
    for loc in data.get("locations", [])[:5]:
        hazards = first_text(loc.get("hazards"), loc.get("locked_paths"), max_len=90)
        if hazards != "Non specificato nel JSON.":
            y = bullet(d, f"{item_name(loc)}: {hazards}", 66, y, 500, color=POSTER["purple"], max_lines=2)

    panel(d, (630, 850, 1196, 1225), "Audit e fix prioritari")
    y = 902
    if findings:
        for f in findings[:9]:
            col = POSTER["red"] if f.severity == "critical" else (POSTER["gold"] if f.severity == "warning" else POSTER["blue"])
            y = bullet(d, f"{f.severity.upper()} {f.category}/{f.entity_id}: {f.message}. Fix: {f.fix_hint}", 652, y, 510, color=col, max_lines=2)
    else:
        poster_text(d, "Nessun finding automatico. Controllare comunque pacing, ridondanza degli indizi e coerenza delle motivazioni.", 652, y, 500, 4, F["poster_body"])

    panel(d, (44, 1255, 1196, 1556), "Analisi runtime")
    metrics = [
        ("Tipo", first_text(data.get("genre"), category, max_len=22)),
        ("Location", len(data.get("locations", []))),
        ("NPC", len(data.get("actors", []))),
        ("Indizi", len(data.get("clues", []))),
        ("Clock", len(data.get("event_clocks", []))),
    ]
    x = 70
    for label, val in metrics:
        d.rounded_rectangle((x, 1310, x + 190, 1385), radius=8, fill="#10232a", outline=POSTER["line"], width=2)
        d.text((x + 14, 1320), str(val), fill=POSTER["ink"], font=F["poster_h"])
        d.text((x + 14, 1352), label, fill=POSTER["muted"], font=F["poster_small"])
        x += 218
    checklist = [
        "Ogni verita importante deve avere indizi ridondanti o recuperabili.",
        "Ogni antagonista deve reagire a prove, minacce, fallimenti e ritardi.",
        "I gate non devono bloccare il gioco senza percorsi alternativi.",
        "I clock devono mostrare segnali prima di produrre conseguenze dure.",
    ]
    y = 1420
    for item in checklist:
        y = bullet(d, item, 70, y, 1050, color=POSTER["green"], max_lines=1)

    d.text((44, 1688), f"{path.name} - pagina GM / runtime analysis", fill=POSTER["muted"], font=F["poster_tiny"])
    return img


def output_path_for(json_path: Path) -> Path:
    return json_path.with_name(f"{json_path.stem}_infografica_A4.pdf")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def generate_one(path: Path, overwrite: bool = False) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = unwrap(raw)
    try:
        category = path.parent.relative_to(DEFAULT_DIR).parts[0]
    except ValueError:
        category = path.parent.name
    out = output_path_for(path)
    if out.exists() and not overwrite:
        raise FileExistsError(f"Esiste gia: {out}")
    pages = [
        visual_player_page(data, path, category),
        visual_gm_page(data, path, category),
    ]
    pages[0].save(out, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera PDF A4 a due pagine per le avventure compilate.")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_DIR), help="File JSON o directory root delle avventure")
    parser.add_argument("--overwrite", action="store_true", help="Sovrascrive PDF gia esistenti")
    args = parser.parse_args()

    target = Path(args.path)
    files = files_under(target)
    if not files:
        print(f"Nessun JSON trovato in {target}")
        return 1

    made = []
    for path in files:
        out = generate_one(path, overwrite=args.overwrite)
        made.append(out)
        print(f"OK {display_path(path)} -> {display_path(out)}")

    print(f"\nGenerati {len(made)} PDF.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
