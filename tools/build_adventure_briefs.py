#!/usr/bin/env python3
"""Genera schede sintetiche delle avventure: titolo, flavor text e un prompt
per generare l'immagine di presentazione (da incollare in ChatGPT/Gemini).

Output: data/compiled_adventures/_catalogo/AVVENTURE_BRIEF.md
Idempotente: rilancialo dopo ogni modifica allo store.

    python3 tools/build_adventure_briefs.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "compiled_adventures"
OUT = STORE / "_catalogo" / "AVVENTURE_BRIEF.md"

sys.path.insert(0, str(ROOT / "backend"))
try:
    from App.adventure_runtime_store import genre_folder  # type: ignore
except Exception:
    def genre_folder(g: str) -> str:  # minimal fallback
        k = str(g or "").lower().replace(" ", "_").replace("-", "_")
        return {"sci_fi": "sci-fi", "scifi": "sci-fi"}.get(k, k or "_other")

THEME_LABEL = {
    "sci-fi": "Fantascienza", "fantasy": "Fantasy", "horror": "Horror",
    "investigation": "Investigazione", "action": "Azione", "storico": "Storico",
    "romance": "Romance", "_other": "Altro",
}
# Direzione artistica per genere (per il prompt immagine).
GENRE_STYLE = {
    "fantasy":       "illustrazione fantasy epica, pittura digitale, atmosfera mitica e maestosa",
    "sci-fi":        "concept art fantascientifica cinematografica, dettagli tecnologici, palette fredda",
    "horror":        "horror oscuro e atmosferico, ombre profonde, tensione inquietante",
    "investigation": "estetica noir investigativa, contrasti netti, nebbia e mistero",
    "action":        "illustrazione action cinematografica, dinamica e ad alta tensione",
    "romance":       "pittura evocativa e romantica, luce calda, tono intimo",
    "storico":       "illustrazione storica realistica, ricca di dettagli d'epoca",
    "_other":        "illustrazione cinematografica dettagliata",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def first_sentences(text: str, max_len: int = 320) -> str:
    t = clean(text)
    if len(t) <= max_len:
        return t
    cut = t[:max_len]
    # taglia all'ultimo confine di frase utile
    m = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: m + 1] if m > 80 else cut.rstrip() + "…")


def flavor_of(ad: dict) -> str:
    title = clean(ad.get("title"))
    text = clean(ad.get("premise")) or clean(ad.get("initial_hook")) or clean(ad.get("logline"))
    # alcuni premise/hook iniziano ripetendo il titolo: rimuovilo
    if title and text.lower().startswith(title.lower()):
        text = text[len(title):].lstrip(" :—-")
    return first_sentences(text) or "(nessuna descrizione disponibile)"


def pick_setting(ad: dict) -> str:
    """Prima location evocativa, scartando nomi-struttura generici."""
    generic = re.compile(
        r"^(adventure\s+overview|overview|apertura|opening|prologo|prologue|"
        r"introduzione|introduction|ingresso|entrance|scena|scene|atto|act|"
        r"luogo del confronto|piazza neutrale|sede fazione|mercato delle informazioni|"
        r"hub|inizio|start)\b", re.I)
    for l in (ad.get("locations") or []):
        name = clean(l.get("name"))
        if name and not generic.match(name):
            return name
    return ""


def image_prompt(ad: dict, folder: str) -> str:
    title = clean(ad.get("title"))
    style = GENRE_STYLE.get(folder, GENRE_STYLE["_other"])
    tone = first_sentences(ad.get("tone"), 140)
    scene = first_sentences(ad.get("premise") or ad.get("initial_hook"), 240)
    setting = pick_setting(ad)
    parts = [
        f"Crea un'immagine di copertina per l'avventura «{title}».",
        f"Stile: {style}.",
    ]
    if scene:
        parts.append(f"Scena: {scene}")
    if setting:
        parts.append(f"Ambientazione principale: {setting}.")
    if tone:
        parts.append(f"Atmosfera: {tone}.")
    parts.append("Inquadratura cinematografica verticale, luce drammatica, "
                 "altissimo dettaglio. Nessun testo, logo o scritta nell'immagine.")
    return " ".join(parts)


def collect():
    out = []
    for theme_dir in sorted(STORE.iterdir()):
        if not theme_dir.is_dir() or theme_dir.name.startswith("_"):
            continue
        for jf in sorted(theme_dir.glob("*.json")):
            try:
                ad = json.loads(jf.read_text(encoding="utf-8")).get("adventure_definition") or {}
            except Exception:
                continue
            if not ad.get("id"):
                continue
            folder = genre_folder(ad.get("genre") or theme_dir.name)
            out.append((folder, ad, jf))
    return out


def main():
    rows = collect()
    grouped = defaultdict(list)
    for folder, ad, jf in rows:
        grouped[folder].append((ad, jf))

    L = ["# 🎴 Schede avventure — flavor & prompt immagine\n"]
    L.append(f"> {len(rows)} avventure. Per ognuna: flavor text e un prompt pronto da "
             "incollare in ChatGPT/Gemini per generare l'immagine di presentazione.\n")
    L.append(f"> Generato da `tools/build_adventure_briefs.py`.\n")

    for folder in sorted(grouped):
        items = sorted(grouped[folder], key=lambda x: clean(x[0].get("title")).lower())
        L.append(f"\n## {THEME_LABEL.get(folder, folder)} ({len(items)})\n")
        for ad, jf in items:
            title = clean(ad.get("title")) or jf.stem
            L.append(f"### {title}")
            L.append(f"*{flavor_of(ad)}*\n")
            L.append("**Prompt immagine:**")
            L.append(f"> {image_prompt(ad, folder)}\n")
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"Scritto {OUT} ({len(rows)} avventure)")


if __name__ == "__main__":
    main()
