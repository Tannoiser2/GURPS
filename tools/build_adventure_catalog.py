#!/usr/bin/env python3
"""Costruisce una vista "catalogo" delle avventure compilate per il colpo d'occhio.

NON tocca i file canonici (l'app li indicizza per id = nome file). Crea invece
``data/compiled_adventures/_catalogo/`` con:

  * symlink ai file reali, rinominati con un codice ``TEMA-FONTE-PUNTEGGIO``
    e organizzati in sottocartelle per tema;
  * le avventure rotte (valid/playable = False) raccolte in ``_ROTTE/``;
  * un ``CATALOGO.md`` con tabella riassuntiva ordinabile.

Rilancia questo script ogni volta che arricchisci/rigeneri le avventure:
è idempotente, ricostruisce ``_catalogo/`` da zero.

    python3 tools/build_adventure_catalog.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "compiled_adventures"
CATALOG = STORE / "_catalogo"

# Riusa la mappa genere→cartella dell'app per restare coerenti.
sys.path.insert(0, str(ROOT / "backend"))

# Punteggio qualità REALE dal Doctor (audit live), non il playable_score salvato
# a generazione (che era troppo indulgente e non rifletteva la giocabilità vera).
from unittest.mock import MagicMock as _MagicMock  # noqa: E402
for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, _MagicMock())
try:
    from App.adventure_doctor import audit as _audit, score as _doctor_raw  # type: ignore

    def _doctor_score(ad: dict):
        try:
            return round(_doctor_raw(_audit(ad)) * 10)  # 0-10 → 0-100
        except Exception:
            return None
except Exception:  # backend non importabile → nessun punteggio
    def _doctor_score(ad: dict):
        return None

try:
    from App.adventure_runtime_store import genre_folder  # type: ignore
except Exception:  # fallback minimale se il backend non è importabile
    _MAP = {
        "sci_fi": "sci-fi", "sci-fi": "sci-fi", "scifi": "sci-fi", "cyberpunk": "sci-fi",
        "space_opera": "sci-fi", "post_apocalyptic": "sci-fi",
        "fantasy": "fantasy", "dark_fantasy": "fantasy", "mythic": "fantasy",
        "sword_and_sorcery": "fantasy",
        "horror": "horror", "mystery_horror": "horror", "cosmic_horror": "horror",
        "survival_horror": "horror", "gothic": "horror",
        "detective_classico": "investigation", "investigation": "investigation",
        "mystery": "investigation", "noir": "investigation", "thriller": "investigation",
        "spy": "investigation",
        "action": "action", "action_adventure": "action", "heist": "action", "military": "action",
        "ww2": "storico", "western": "storico", "historical": "storico",
        "renaissance": "storico", "ancient": "storico",
        "romance": "romance", "drama": "romance", "social": "romance",
    }

    def genre_folder(genre: str) -> str:  # type: ignore
        key = str(genre or "").lower().strip().replace(" ", "_").replace("-", "_")
        return _MAP.get(key, "_other")


# Codice tema (3 lettere) per ogni cartella canonica.
THEME_CODE = {
    "sci-fi": "SCI", "fantasy": "FAN", "horror": "HOR", "investigation": "INV",
    "action": "ACT", "storico": "STO", "romance": "ROM", "_other": "OTH",
}
THEME_LABEL = {
    "sci-fi": "Fantascienza", "fantasy": "Fantasy", "horror": "Horror",
    "investigation": "Investigazione", "action": "Azione", "storico": "Storico",
    "romance": "Romance", "_other": "Altro",
}


def slugify(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s[:48] or fallback


def source_code(ad: dict, stem: str) -> str:
    mode = (ad.get("source_mode") or "").lower()
    stype = (ad.get("source_type") or "").lower()
    if "pdf" in mode or "pdf" in stype or stem.startswith("pdf_"):
        return "PDF"
    if "ai" in mode or stem.startswith("ai_"):
        return "AI"
    return "GEN"


def collect():
    entries = []
    for theme_dir in sorted(STORE.iterdir()):
        if not theme_dir.is_dir() or theme_dir.name.startswith("_"):
            continue  # salta _backup_*, _debug_pdf, _catalogo
        for jf in sorted(theme_dir.glob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            ad = data.get("adventure_definition")
            if not isinstance(ad, dict) or not ad.get("id"):
                continue  # non è un'avventura compilata
            vr = data.get("validation_report") or {}
            folder = genre_folder(ad.get("genre") or theme_dir.name)
            code_theme = THEME_CODE.get(folder, "OTH")
            src = source_code(ad, jf.stem)
            score = _doctor_score(ad)  # punteggio Doctor live (0-100), non playable_score
            score_txt = f"{int(score):02d}" if isinstance(score, (int, float)) else "NA"
            broken = vr.get("valid") is False          # invalida -> _ROTTE
            unplayable = not broken and vr.get("playable") is False  # valida ma non giocabile
            slug = slugify(ad.get("title", ""), jf.stem)
            code = f"{code_theme}-{src}-{score_txt}"
            entries.append({
                "code": code, "theme": folder, "theme_code": code_theme,
                "src": src, "score": score if isinstance(score, (int, float)) else None,
                "broken": broken, "unplayable": unplayable,
                "slug": slug, "title": ad.get("title") or jf.stem,
                "real": jf, "errors": len(vr.get("errors") or []),
                "warnings": len(vr.get("warnings") or []),
            })
    return entries


def rel_symlink(link: Path, target: Path):
    import os
    link.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(target, link.parent)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(rel)


def build():
    import shutil
    CATALOG.mkdir(parents=True, exist_ok=True)
    # Pulisce SOLO le sottocartelle di link (per-genere + _ROTTE) e il CATALOGO.md
    # che riscrive — NON l'intera cartella, altrimenti cancellerebbe
    # AVVENTURE_BRIEF.md (gestito da build_adventure_briefs.py) ad ogni run.
    for child in CATALOG.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
    (CATALOG / "CATALOGO.md").unlink(missing_ok=True)

    entries = collect()
    # ordina: tema, poi punteggio decrescente, poi titolo
    entries.sort(key=lambda e: (e["theme"], -(e["score"] or -1), e["slug"]))

    used = Counter()
    for e in entries:
        sub = "_ROTTE" if e["broken"] else e["theme"]
        name = f"{e['code']}__{e['slug']}"
        used[name] += 1
        if used[name] > 1:  # evita collisioni di nome
            name = f"{name}_{e['real'].stem[-6:]}"
        link = CATALOG / sub / f"{name}.json"
        rel_symlink(link, e["real"])
        e["link_name"] = f"{sub}/{name}.json"

    write_markdown(entries)
    return entries


def write_markdown(entries):
    n = len(entries)
    by_theme = Counter(e["theme"] for e in entries)
    by_src = Counter(e["src"] for e in entries)
    broken = [e for e in entries if e["broken"]]
    unplayable = [e for e in entries if e["unplayable"]]
    scored = [e["score"] for e in entries if e["score"] is not None and not e["unplayable"]]
    avg = sum(scored) / len(scored) if scored else 0

    L = []
    L.append("# 📚 Catalogo avventure\n")
    L.append("> Vista generata da `tools/build_adventure_catalog.py` — symlink ai file "
             "reali in `data/compiled_adventures/`. **Non** modificare a mano: rilancia lo script.\n")
    L.append(f"**Totale:** {n} avventure · **Punteggio medio (giocabili):** {avg:.0f}/100 · "
             f"**Rotte:** {len(broken)} · **Non giocabili:** {len(unplayable)}\n")
    L.append("**Per fonte:** " + " · ".join(f"{k} {v}" for k, v in sorted(by_src.items())) + "  ")
    L.append("**Per tema:** " + " · ".join(
        f"{THEME_LABEL.get(k, k)} {v}" for k, v in sorted(by_theme.items())) + "\n")
    L.append("**Legenda codice:** `TEMA-FONTE-PUNTEGGIO` — "
             "TEMA: FAN/HOR/SCI/INV/ACT/ROM/STO · FONTE: PDF/AI/GEN · PUNTEGGIO: playable_score (NA = assente)\n")

    if broken:
        L.append("## ⚠️ Rotte (da sistemare)\n")
        L.append("| Codice | Titolo | Errori | Warn | File |")
        L.append("|---|---|---|---|---|")
        for e in sorted(broken, key=lambda e: e["code"]):
            L.append(f"| `{e['code']}` | {e['title']} | {e['errors']} | {e['warnings']} | "
                     f"`{e['real'].parent.name}/{e['real'].name}` |")
        L.append("")

    # sezioni per tema
    grouped = defaultdict(list)
    for e in entries:
        grouped[e["theme"]].append(e)
    for theme in sorted(grouped):
        rows = sorted(grouped[theme], key=lambda e: (-(e["score"] or -1), e["slug"]))
        L.append(f"## {THEME_LABEL.get(theme, theme)} ({len(rows)})\n")
        L.append("| Codice | Titolo | Fonte | Punt. | Stato | File |")
        L.append("|---|---|---|---|---|---|")
        for e in rows:
            if e["broken"]:
                stato = "🔴 rotta"
            elif e["unplayable"]:
                stato = "⛔ non giocabile"
            elif e["score"] is None:
                stato = "⚪ n/d"
            elif e["score"] >= 85:
                stato = "🟢"
            elif e["score"] >= 70:
                stato = "🟡"
            else:
                stato = "🟠"
            sc = e["score"] if e["score"] is not None else "—"
            L.append(f"| `{e['code']}` | {e['title']} | {e['src']} | {sc} | {stato} | "
                     f"`{e['real'].parent.name}/{e['real'].name}` |")
        L.append("")

    (CATALOG / "CATALOGO.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    ents = build()
    print(f"Catalogo generato: {len(ents)} avventure → {CATALOG}")
    print(f"  rotte: {sum(1 for e in ents if e['broken'])}")
