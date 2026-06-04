"""Pulisce le piste (story_threads) "vuote" — quelle con 0 indizi collegati mentre
altre piste della stessa avventura ne hanno.

L'import da PDF (e talvolta la generazione) creava due sistemi di piste paralleli:
macro-piste con tutti gli indizi + micro-piste con una revelation ma 0 indizi.
Le micro-piste vuote rendono l'indagine incoerente e fanno crollare il punteggio
del Doctor (spesso 0–2/10) pur essendo l'avventura "caricabile".

Fix deterministico (niente AI): rimuove le piste a 0 indizi e ri-aggancia le loro
revelation alla prima pista valida (così le risposte non restano orfane).
Salta le avventure giocate (i thread id potrebbero essere referenziati da un
salvataggio in corso).

Uso:
    python scripts/pulisci_piste_vuote.py            # dry-run (before/after score)
    python scripts/pulisci_piste_vuote.py --apply    # applica
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


def _is_played(doc: dict) -> bool:
    if doc.get("live_game_state") is not None:
        return True
    return bool((doc.get("runtime_state") or {}).get("history"))


def _clean(defn: dict) -> int:
    """Rimuove le piste a 0 indizi (se ne restano di valide). Ritorna quante."""
    threads = defn.get("story_threads") or []
    if len(threads) < 2:
        return 0
    clue_by_t = collections.Counter(str(c.get("thread_id") or "") for c in (defn.get("clues") or []))
    clued = [t for t in threads if clue_by_t.get(str(t.get("id")), 0) > 0]
    empty_ids = {str(t.get("id")) for t in threads if clue_by_t.get(str(t.get("id")), 0) == 0}
    if not clued or not empty_ids:
        return 0
    keep_id = str(clued[0].get("id"))
    for r in (defn.get("revelations") or []):
        if str(r.get("thread_id") or "") in empty_ids:
            r["thread_id"] = keep_id
    defn["story_threads"] = [t for t in threads if str(t.get("id")) not in empty_ids]
    return len(empty_ids)


def main(apply: bool) -> int:
    files = sorted(f for f in glob.glob(os.path.join(_STORE, "*", "*.json"))
                   if "_catalogo" not in f)
    changed = skipped_played = 0
    removed_total = 0
    sb, sa = [], []
    rows = []
    for f in files:
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        defn = doc.get("adventure_definition")
        if not defn:
            continue
        before = score(audit(defn))
        n = _clean(defn)  # muta defn in-place
        if n == 0:
            continue
        if _is_played(doc):
            skipped_played += 1
            continue
        after = score(audit(defn))
        changed += 1
        removed_total += n
        sb.append(before)
        sa.append(after)
        rows.append((before, after, n, defn.get("title", "?")[:32]))
        if apply:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)

    print(f"=== Pulizia piste vuote — {'APPLY' if apply else 'DRY-RUN'} ===")
    print(f"avventure sistemate:        {changed}")
    print(f"piste vuote rimosse:        {removed_total}")
    print(f"avventure giocate (saltate):{skipped_played}")
    if sb:
        print(f"score medio: {sum(sb)/len(sb):.1f} → {sum(sa)/len(sa):.1f}")
    print()
    for before, after, n, title in sorted(rows):
        print(f"  {before:4.1f} → {after:4.1f}  (-{n} piste)  {title}")
    if not apply:
        print("\nRilancia con --apply per scrivere.")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
