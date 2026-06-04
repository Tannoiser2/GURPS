"""Migrazione una-tantum: ripara le location orfane nelle avventure dello store.

Contesto
--------
Molte avventure ai_generated hanno attori e indizi che citano luoghi con nomi
reali ("Sala operativa principale") mentre l'array ``locations`` contiene solo
placeholder generici (``loc_ai_N``: "Apertura/Nodo indizi/..."). Tutti i
riferimenti ``actor.location_id`` restano quindi orfani (533 mismatch su 98
avventure), e l'audit del doctor li segnalava facendo scattare enrichment AID.

Cosa fa
-------
Per ogni avventura NON ancora giocata:
  1. materializza le location dai nomi reali che attori/indizi già citano;
  2. ri-aggancia ``actor.location_id`` / ``clue.location_id`` all'id reale;
  3. ricostruisce ``runtime_state.location_runtime`` e ``current_scene_id``.
Deterministico, nessuna chiamata AI. Le avventure con una partita in corso
(``live_game_state`` o ``history``) vengono saltate per non corrompere sessioni.

Uso
---
    python scripts/migra_location_orfane.py            # dry-run (non scrive)
    python scripts/migra_location_orfane.py --apply    # applica le modifiche
"""
from __future__ import annotations

import glob
import json
import os
import sys
from unittest.mock import MagicMock

# La migrazione è puro Python: stub delle dipendenze API pesanti solo se assenti
# (in produzione i pacchetti reali restano quelli installati).
for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

_BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, _BACKEND)

from App.adventure_compiler import _PLACEHOLDER_REF_RE, _id  # noqa: E402
from App.runtime_models import LocationState  # noqa: E402

_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "compiled_adventures")


def _is_placeholder_id(loc_id: str) -> bool:
    return bool(_PLACEHOLDER_REF_RE.match(str(loc_id or "")))


def _is_played(doc: dict) -> bool:
    if doc.get("live_game_state") is not None:
        return True
    return bool((doc.get("runtime_state") or {}).get("history"))


def migrate_definition(defn: dict, runtime_state: dict | None) -> dict | None:
    """Ripara in-place ``defn`` (e ``runtime_state``). Ritorna le statistiche
    o ``None`` se non c'era nulla da fare."""
    locs = defn.get("locations") or []
    actors = defn.get("actors") or []
    clues = defn.get("clues") or []
    loc_ids = {str(l.get("id") or "") for l in locs}

    def _ref(a: dict) -> str:
        return str(a.get("location_id") or "").strip()

    before = sum(1 for a in actors if _ref(a) and _ref(a) not in loc_ids)
    if before == 0:
        return None

    # Conserva le location reali esistenti; scarta solo i placeholder generici.
    real_locs = [l for l in locs if not _is_placeholder_id(l.get("id"))]
    seen = {str(l.get("name") or "").strip().lower() for l in real_locs}

    harvested: list[str] = []

    def _add(val: object) -> None:
        s = str(val or "").strip()
        if not s or s.lower() in seen or _PLACEHOLDER_REF_RE.match(s):
            return
        seen.add(s.lower())
        harvested.append(s)

    for a in actors:
        _add(a.get("location_id"))
        _add(a.get("location"))
    for c in clues:
        _add(c.get("source_location"))
        _add(c.get("location"))

    new_locs: list[dict] = list(real_locs)
    used_ids = {str(l.get("id") or "") for l in real_locs}
    for name in harvested:
        lid = _id("loc", name, len(used_ids) + 1)
        base, n = lid, 2
        while lid in used_ids:
            lid, n = f"{base}_{n}", n + 1
        used_ids.add(lid)
        ls = LocationState(
            id=lid, name=name, description=f"{name}.", type="site",
            access_state="open", source_status="generated", confidence=0.7,
        )
        new_locs.append(json.loads(ls.model_dump_json()))

    if new_locs and not any(l.get("type") == "entry" for l in new_locs):
        new_locs[0]["type"] = "entry"

    # Mappa di risoluzione: id, nome, slug-del-nome -> id reale.
    ref_to_id: dict[str, str] = {}
    for l in new_locs:
        lid = str(l.get("id") or "")
        ref_to_id[lid.lower()] = lid
        nm = str(l.get("name") or "").strip()
        if nm:
            ref_to_id[nm.lower()] = lid
            ref_to_id[_id("loc", nm, 0).lower()] = lid

    def _resolve(*cands: object) -> str | None:
        for c in cands:
            k = str(c or "").strip().lower()
            if k and k in ref_to_id:
                return ref_to_id[k]
        return None

    for a in actors:
        r = _resolve(a.get("location_id"), a.get("location"))
        if r:
            a["location_id"] = r
    for c in clues:
        r = _resolve(c.get("source_location"), c.get("location"), c.get("location_id"))
        if r:
            c["location_id"] = r

    # Ricostruisci contains_actors / contains_clues coerenti.
    by_id = {l["id"]: l for l in new_locs}
    for l in new_locs:
        l["contains_actors"] = []
        l["contains_clues"] = []
    for a in actors:
        lid = str(a.get("location_id") or "")
        if lid in by_id and a.get("id"):
            by_id[lid]["contains_actors"].append(a["id"])
    for c in clues:
        lid = str(c.get("location_id") or "")
        if lid in by_id and c.get("id"):
            by_id[lid]["contains_clues"].append(c["id"])

    defn["locations"] = new_locs

    if runtime_state is not None:
        runtime_state["location_runtime"] = {
            l["id"]: {"status": l.get("status", "known"), "access_state": l.get("access_state", "open")}
            for l in new_locs
        }
        entry = next((l["id"] for l in new_locs if l.get("type") == "entry"),
                     new_locs[0]["id"] if new_locs else None)
        if entry:
            runtime_state["current_scene_id"] = entry

    final_ids = {l["id"] for l in new_locs}
    after = sum(1 for a in actors if _ref(a) and _ref(a) not in final_ids)
    return {"before": before, "after": after, "locations": len(new_locs), "added": len(harvested)}


def main(apply: bool) -> int:
    files = sorted(glob.glob(os.path.join(_STORE, "*.json")) +
                   glob.glob(os.path.join(_STORE, "*", "*.json")))
    changed = skipped_played = no_change = 0
    fixed_before = fixed_after = added_total = 0
    for f in files:
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        defn = doc.get("adventure_definition")
        if not defn:
            continue
        if _is_played(doc):
            skipped_played += 1
            continue
        stats = migrate_definition(defn, doc.get("runtime_state"))
        if not stats:
            no_change += 1
            continue
        changed += 1
        fixed_before += stats["before"]
        fixed_after += stats["after"]
        added_total += stats["added"]
        if apply:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)

    mode = "APPLICATO" if apply else "DRY-RUN (nessun file scritto)"
    print(f"=== Migrazione location orfane — {mode} ===")
    print(f"avventure modificate:           {changed}")
    print(f"  mismatch NPC->location prima: {fixed_before}")
    print(f"  mismatch NPC->location dopo:  {fixed_after}")
    print(f"  location reali materializzate:{added_total}")
    print(f"avventure già a posto:          {no_change}")
    print(f"avventure saltate (giocate):    {skipped_played}")
    if not apply:
        print("\nRilancia con --apply per scrivere le modifiche.")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
