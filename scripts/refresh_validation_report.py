"""Rinfresca validation_report con la valutazione Doctor LIVE.

Il pannello "Runtime Quality" dell'app legge validation_report.quality.*_score e
.warnings, salvati all'import e mai aggiornati: mostravano 100% / playable_score
94 anche per avventure che il Doctor valuta 4-5/10, con warning obsoleti (attori
che non esistono più). Re-runnare il vecchio validatore non aiuta: è troppo
indulgente per design.

Questa migrazione (deterministica, niente AI) sovrascrive in ogni avventura:
  - validation_report.doctor_score   = punteggio Doctor 0-10
  - validation_report.playable_score = round(doctor*10) 0-100
  - validation_report.quality.*_score = barre derivate dalle categorie Doctor
  - validation_report.warnings       = i finding Doctor reali (errori+warning)

Uso:
    python scripts/refresh_validation_report.py            # dry-run
    python scripts/refresh_validation_report.py --apply    # scrive
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from App.adventure_doctor import audit, score  # noqa: E402

_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "compiled_adventures")
_PEN = {"error": 30, "critical": 30, "warning": 15, "suggestion": 5, "info": 5}


def _refresh(defn: dict) -> dict:
    findings = audit(defn)
    sc = score(findings)  # 0-10
    by_cat = collections.defaultdict(int)
    for f in findings:
        by_cat[f.category] += _PEN.get(f.severity, 5)

    def bar(*cats):
        return max(0, min(100, 100 - sum(by_cat.get(c, 0) for c in cats)))

    quality = {
        # "densità fiction" ≈ qualità complessiva di struttura/trama
        "fiction_density_score": bar("structure", "thread", "balance"),
        "clue_concreteness_score": bar("clue"),
        "npc_agenda_score": bar("npc"),
        "location_playability_score": bar("location"),
        "clock_operational_score": bar("clock"),
    }
    warnings = [f.message for f in findings if f.severity in ("error", "warning", "critical")][:6]
    return {
        "doctor_score": sc,
        "playable_score": round(sc * 10),
        "quality": quality,
        "warnings": warnings,
    }


def main(apply: bool) -> int:
    files = sorted(f for f in glob.glob(os.path.join(_STORE, "*", "*.json"))
                   if "_catalogo" not in f)
    changed = 0
    samples = []
    for f in files:
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        defn = doc.get("adventure_definition")
        if not defn:
            continue
        vr = doc.get("validation_report") or {}
        old = vr.get("playable_score")
        fresh = _refresh(defn)
        vr.update(fresh)
        doc["validation_report"] = vr
        changed += 1
        if len(samples) < 12:
            samples.append((old, fresh["playable_score"], defn.get("title", "?")[:30]))
        if apply:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)

    print(f"=== Refresh validation_report — {'APPLY' if apply else 'DRY-RUN'} ===")
    print(f"avventure aggiornate: {changed}")
    print(f"\nplayable_score: PRIMA → DOPO (campione)")
    for old, new, t in samples:
        print(f"  {str(old):>4} → {new:>3}   {t}")
    if not apply:
        print("\nRilancia con --apply per scrivere.")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
