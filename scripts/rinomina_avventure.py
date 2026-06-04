"""Rinomina i file avventura con nome-hash (adv_<hash>.json) in nomi leggibili
derivati dal titolo (es. ai_la_reliquia_di_velmora.json).

Il nome-file è accoppiato all'`id` interno (lo store carica `{id}.json`), quindi
NON basta rinominare: lo script aggiorna anche tutte le occorrenze dell'id dentro
il file (definition.id, legacy_adventure.id/.adventure_definition_id,
runtime_state.definition_id) in modo coerente.

Sicurezza:
- salta le avventure GIOCATE (live_game_state/history) per non orfanare una
  sessione o un bookmark attivo all'id vecchio;
- gestisce le collisioni di nome con suffisso numerico;
- lascia invariati i file già con nome leggibile.

Uso:
    python scripts/rinomina_avventure.py            # dry-run (mostra il piano)
    python scripts/rinomina_avventure.py --apply    # rinomina davvero
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import unicodedata

_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "compiled_adventures")
_HASH_RE = re.compile(r"^adv_[0-9a-f]{10}$")


def _slugify(title: str) -> str:
    s = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s[:42].strip("_") or "avventura"


def _replace_id(obj, old: str, new: str):
    if isinstance(obj, dict):
        return {k: _replace_id(v, old, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_id(v, old, new) for v in obj]
    return new if obj == old else obj


def main(apply: bool) -> int:
    files = sorted(f for f in glob.glob(os.path.join(_STORE, "*", "*.json"))
                   if "_catalogo" not in f)
    used = {os.path.basename(f)[:-5] for f in files}  # tutti gli stem attuali

    renames = []
    skipped_played = skipped_readable = 0
    for f in files:
        stem = os.path.basename(f)[:-5]
        if not _HASH_RE.match(stem):
            skipped_readable += 1
            continue
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if doc.get("live_game_state") is not None or (doc.get("runtime_state") or {}).get("history"):
            skipped_played += 1
            continue
        title = (doc.get("adventure_definition") or {}).get("title", "")
        base = "ai_" + _slugify(title)
        cand, n = base, 2
        others = used - {stem}
        while cand in others:
            cand, n = f"{base}_{n}", n + 1
        used.discard(stem)
        used.add(cand)
        renames.append((f, stem, cand, doc))

    print(f"=== Rinomina avventure — {'APPLY' if apply else 'DRY-RUN'} ===")
    print(f"file con nome leggibile (invariati): {skipped_readable}")
    print(f"avventure giocate (saltate):         {skipped_played}")
    print(f"da rinominare:                       {len(renames)}\n")
    for f, old_id, new_id, _ in renames:
        genre = os.path.basename(os.path.dirname(f))
        print(f"  {genre}/{old_id}  →  {new_id}")

    if apply:
        for f, old_id, new_id, doc in renames:
            doc = _replace_id(doc, old_id, new_id)
            newpath = os.path.join(os.path.dirname(f), new_id + ".json")
            with open(newpath, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
            if os.path.abspath(newpath) != os.path.abspath(f):
                os.remove(f)
        print(f"\n✅ Rinominate {len(renames)} avventure. Rigenera il catalogo dopo.")
    else:
        print("\nRilancia con --apply per rinominare.")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
