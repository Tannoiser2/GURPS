"""Migrazione AI: risolve i riferimenti location orfani delle avventure da PDF.

Contesto
--------
Le avventure importate da PDF hanno spesso ``actor.location_id`` = id-segnaposto
del modulo (``section_1``, ``p11_room_6``) che non corrisponde a nessuna location
reale: il passo LLM di risoluzione semantica (``resolve_actor_locations_with_llm``)
non era stato applicato. Restano 234 attori orfani su 34 avventure — non
risolvibili in modo deterministico (niente nome/sezione a cui agganciarsi).

Cosa fa
-------
Per ogni avventura NON giocata con attori orfani, chiede al modello — passando
SOLO la lista di location (id+nome) e di attori (nome/ruolo/movente) — quale
location si adatta meglio a ciascun attore. Riusa il resolver già esistente del
percorso PDF; non serve il testo originale del modulo. Una chiamata per avventura.

Costo indicativo: ~1 chiamata breve (~800 token) per avventura → pochi centesimi
in totale.

Uso
---
    python scripts/migra_pdf_location_llm.py            # dry-run: elenca i target, NON chiama l'AI
    python scripts/migra_pdf_location_llm.py --apply    # chiama l'AI e scrive (richiede API key)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

_BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, _BACKEND)

_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "compiled_adventures")
_PLACEHOLDER_RE = re.compile(r"^(section_\d+|p\d+_room_\d+|room_\d+|loc_\d+|area_\d+)$")


def _is_played(doc: dict) -> bool:
    if doc.get("live_game_state") is not None:
        return True
    return bool((doc.get("runtime_state") or {}).get("history"))


def _orphan_actors(defn: dict) -> list[dict]:
    loc_ids = {str(l.get("id") or "") for l in (defn.get("locations") or [])}
    out = []
    for a in (defn.get("actors") or []):
        ref = str(a.get("location_id") or "").strip()
        if (not ref or _PLACEHOLDER_RE.match(ref)) and ref not in loc_ids:
            out.append(a)
    return out


def _actors_with_descriptions(actors: list[dict]) -> list[dict]:
    """Arricchisce la desc passata al modello con movente/segreto, se manca,
    per dargli più segnale su dove collocare ogni PNG."""
    enriched = []
    for a in actors:
        b = dict(a)
        if not b.get("description"):
            b["description"] = " · ".join(
                str(a.get(k) or "") for k in ("role", "goal", "secret") if a.get(k)
            )[:160]
        enriched.append(b)
    return enriched


def _rebuild_containment(defn: dict) -> None:
    by_id = {l["id"]: l for l in (defn.get("locations") or []) if l.get("id")}
    for l in by_id.values():
        l["contains_actors"] = []
    for a in (defn.get("actors") or []):
        lid = str(a.get("location_id") or "")
        if lid in by_id and a.get("id"):
            by_id[lid]["contains_actors"].append(a["id"])


def main(apply: bool) -> int:
    files = sorted(glob.glob(os.path.join(_STORE, "*.json")) +
                   glob.glob(os.path.join(_STORE, "*", "*.json")))

    targets: list[tuple[str, dict, list[dict]]] = []
    skipped_played = 0
    for f in files:
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        defn = doc.get("adventure_definition")
        if not defn:
            continue
        orphans = _orphan_actors(defn)
        if not orphans:
            continue
        if _is_played(doc):
            skipped_played += 1
            continue
        targets.append((f, doc, orphans))

    tot_actors = sum(len(o) for _, _, o in targets)
    print(f"=== Resolver LLM location PDF — {'APPLY' if apply else 'DRY-RUN'} ===")
    print(f"avventure target:            {len(targets)}")
    print(f"attori orfani da risolvere:  {tot_actors}")
    print(f"avventure saltate (giocate): {skipped_played}")

    if not apply:
        for f, _, orphans in targets:
            print(f"  - {os.path.basename(f):40s} {len(orphans)} attori")
        print(f"\nStima costo: ~{len(targets)} chiamate brevi (~$0.02 l'una) ≈ "
              f"${0.02 * len(targets):.2f}")
        print("Rilancia con --apply (e API key configurata) per risolvere e scrivere.")
        return 0

    # --- APPLY: serve il provider AI (dipendenze backend installate + API key) ---
    try:
        from App import claude_service  # noqa: E402
        from App.llm_extractors import resolve_actor_locations_with_llm  # noqa: E402
    except BaseException as exc:  # noqa: BLE001  # pragma: no cover - dipende dall'ambiente
        print(f"\nERRORE: impossibile caricare il backend AI ({exc}).")
        print("Esegui --apply nell'ambiente con le dipendenze installate e ANTHROPIC_API_KEY.")
        return 1

    if not claude_service._text_provider_available():
        print("\nERRORE: nessun provider AI disponibile (configura ANTHROPIC_API_KEY).")
        return 1

    changed = resolved_total = unresolved_total = 0
    for f, doc, orphans in targets:
        defn = doc["adventure_definition"]
        locations = defn.get("locations") or []
        actors_enriched = _actors_with_descriptions(defn.get("actors") or [])
        mapping = resolve_actor_locations_with_llm(
            "", locations, actors_enriched, title=defn.get("title", ""),
        ) or {}
        applied = 0
        for a in defn.get("actors") or []:
            aid = str(a.get("id") or "")
            if aid in mapping:
                a["location_id"] = mapping[aid]
                a["location"] = next(
                    (l.get("name") for l in locations if l.get("id") == mapping[aid]),
                    a.get("location"),
                )
                applied += 1
        if applied:
            _rebuild_containment(defn)
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
            changed += 1
        resolved_total += applied
        unresolved_total += len(orphans) - applied
        print(f"  {os.path.basename(f):40s} {applied}/{len(orphans)} risolti")

    print(f"\navventure modificate:   {changed}")
    print(f"attori risolti:         {resolved_total}")
    print(f"attori ancora orfani:   {unresolved_total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
