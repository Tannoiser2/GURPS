#!/usr/bin/env python3
"""
fix_pdf_crossrefs.py

Risolve le cross-reference rotte negli 8 JSON PDF delle avventure GURPS:
- NPC -> location_id non risolto (placeholder section_N, p\d+_room_\d+, ecc.)
- Clue -> source_location testuale non corrispondente agli ID slug
- contains_actors / contains_clues vuoti
- FOW piatto (tutte status = "known")
"""

import json
import re
import os
import sys

FILES = [
    "data/compiled_adventures/fantasy/pdf_la_foresta_dei_sogni_impossibili.json",
    "data/compiled_adventures/fantasy/pdf_cat_nani.json",
    "data/compiled_adventures/fantasy/pdf_lupo_di_kosmar.json",
    "data/compiled_adventures/fantasy/pdf_cattedrale_luna_infernale.json",
    "data/compiled_adventures/horror/pdf_opera_unceasing.json",
    "data/compiled_adventures/action/pdf_minutes_not_hours.json",
    "data/compiled_adventures/action/pdf_the_sirens_citadel.json",
    "data/compiled_adventures/sci-fi/pdf_clear_light_of_doomsday.json",
]

# Mapping location type -> FOW scope category
# strategic (urban, vehicle) -> known
# regional (outdoor, wilderness) -> unknown
# local (indoor, dungeon) -> hidden
TYPE_TO_SCOPE = {
    "urban":     "strategic",
    "vehicle":   "strategic",
    "outdoor":   "regional",
    "wilderness": "regional",
    "indoor":    "local",
    "dungeon":   "local",
}

BROKEN_LOC_PATTERN = re.compile(
    r'^(section_\d+|p\d+_room_\d+|p\d+_room_[a-z]|room_\d+)$'
)


def slugify(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]+', '_', text.strip().lower())[:40].strip('_')


def is_broken_loc(loc_id: str, loc_by_id: dict) -> bool:
    if not loc_id:
        return True
    if BROKEN_LOC_PATTERN.match(loc_id):
        return True
    if loc_id not in loc_by_id:
        return True
    return False


def find_location_by_text(text: str, loc_by_id: dict, loc_by_name: dict) -> str | None:
    """Try various strategies to map a text string to a location id."""
    if not text:
        return None

    # Strategy 1: slug del testo -> cerca in loc_by_id
    sl = slugify(text)
    if sl in loc_by_id:
        return sl

    # Strategy 2: testo lowercase -> cerca in loc_by_name
    low = text.lower().strip()
    if low in loc_by_name:
        return loc_by_name[low]

    # Strategy 3: match parziale slug - il testo contiene parte di un id, o un id contiene parte del testo
    for loc_id in loc_by_id:
        if sl and (sl in loc_id or loc_id in sl):
            return loc_id

    # Strategy 4: match per parole-chiave - ogni parola del testo in nome o id location
    words = [w for w in re.split(r'[\s_\-/]+', low) if len(w) >= 3]
    for loc_id, loc in loc_by_id.items():
        loc_name_low = loc["name"].lower()
        for word in words:
            if word in loc_name_low or word in loc_id:
                return loc_id

    # Strategy 5: ogni parola di ogni loc_name nel testo
    for loc_name_low, loc_id in loc_by_name.items():
        name_words = [w for w in re.split(r'[\s_\-/]+', loc_name_low) if len(w) >= 3]
        for nw in name_words:
            if nw in low:
                return loc_id

    return None


def pick_fallback_location(loc_by_id: dict, preferred_scope: str | None = None) -> str | None:
    """Scegli una location di fallback: prima local, poi regional, poi la prima disponibile."""
    order = ["local", "regional", "strategic"]
    if preferred_scope and preferred_scope in order:
        order = [preferred_scope] + [s for s in order if s != preferred_scope]

    for scope in order:
        types_in_scope = [t for t, s in TYPE_TO_SCOPE.items() if s == scope]
        for loc_id, loc in loc_by_id.items():
            if loc.get("type") in types_in_scope:
                return loc_id

    # ultimo fallback: prima location qualunque
    if loc_by_id:
        return next(iter(loc_by_id))
    return None


def resolve_actor_location(actor: dict, loc_by_id: dict, loc_by_name: dict) -> str | None:
    """Risolvi la location_id di un NPC con location_id rotto."""
    name = actor.get("name", "")
    loc_text = actor.get("location", "")  # campo testuale opzionale

    # Strategy 1: slug del nome NPC -> cerca in loc_by_id
    name_slug = slugify(name)
    if name_slug and name_slug in loc_by_id:
        return name_slug

    # Strategy 2: match parziale slug nome NPC in loc ids o names
    if name_slug:
        for loc_id, loc in loc_by_id.items():
            if name_slug in loc_id or name_slug in slugify(loc["name"]):
                return loc_id
        # Tokenizza il nome e cerca ogni token
        tokens = [t for t in re.split(r'[\s_\-/]+', name_slug) if len(t) >= 3]
        for token in tokens:
            for loc_id, loc in loc_by_id.items():
                if token in loc_id or token in slugify(loc["name"]):
                    return loc_id

    # Strategy 3: usa il campo location testuale (se presente)
    if loc_text:
        result = find_location_by_text(loc_text, loc_by_id, loc_by_name)
        if result:
            return result

    # Strategy 4: cerca ogni parola del nome NPC nelle location
    name_low = name.lower()
    name_words = [w for w in re.split(r'[\s_\-/]+', name_low) if len(w) >= 3]
    for word in name_words:
        for loc_id, loc in loc_by_id.items():
            if word in loc["name"].lower() or word in loc_id:
                return loc_id

    # Fallback: prima location locale, poi regionale, poi qualunque
    return pick_fallback_location(loc_by_id, preferred_scope="local")


def resolve_clue_location(
    clue: dict,
    loc_by_id: dict,
    loc_by_name: dict,
    actors: list,
    resolved_actor_locs: dict
) -> str | None:
    """Risolvi source_location di un clue."""
    src = clue.get("source_location", "")

    # Strategy 1: slug diretto
    if src:
        sl = slugify(src)
        if sl in loc_by_id:
            return sl

    # Strategy 2: case-insensitive match
    if src:
        result = find_location_by_text(src, loc_by_id, loc_by_name)
        if result:
            return result

    # Strategy 3: usa thread_id per cercare NPC con stesso thread risolto
    thread_id = clue.get("thread_id")
    if thread_id:
        # Cerca attori collegati allo stesso thread (cerca nel campo goal/secret/etc se menziona thread)
        for actor in actors:
            actor_id = actor["id"]
            if actor_id in resolved_actor_locs:
                # Semplice euristica: se l'attore è nello stesso thread
                actor_threads = []
                for rel in actor.get("relationships", []):
                    pass  # non c'è thread diretto sugli attori
                # Usa il clue source come testo da cercare nell'attore
                if src and src.lower() in actor.get("name", "").lower():
                    return resolved_actor_locs[actor_id]

    # Fallback: prima location locale o regionale
    return pick_fallback_location(loc_by_id, preferred_scope="local")


def get_scope(loc: dict) -> str:
    return TYPE_TO_SCOPE.get(loc.get("type", ""), "local")


def fix_fow(locations: list) -> int:
    """Aggiorna lo status FOW delle location. Ritorna il numero di location aggiornate."""
    updated = 0
    for loc in locations:
        current_status = loc.get("status")
        # Solo se lo status è piatto (known/open/None/"")
        if current_status not in (None, "known", "open", ""):
            continue

        scope = get_scope(loc)
        if scope == "strategic":
            new_status = "known"
        elif scope == "regional":
            new_status = "unknown"
        else:  # local
            new_status = "hidden"

        if current_status != new_status:
            loc["status"] = new_status
            updated += 1

    return updated


def fix_file(filepath: str, base_dir: str) -> None:
    full_path = os.path.join(base_dir, filepath)
    fname = os.path.basename(filepath)

    with open(full_path, encoding="utf-8") as f:
        data = json.load(f)

    ad = data.get("adventure_definition", {})
    locations = ad.get("locations", [])
    actors = ad.get("actors", [])
    clues = ad.get("clues", [])

    # Indici
    loc_by_id = {l["id"]: l for l in locations}
    loc_by_name = {l["name"].lower(): l["id"] for l in locations}

    print(f"=== {fname} ===")

    # --- Step 2: Fix NPC location_id rotti ---
    npc_total = len(actors)
    npc_resolved = 0
    resolved_actor_locs: dict[str, str] = {}

    for actor in actors:
        loc_id = actor.get("location_id", "")
        if not is_broken_loc(loc_id, loc_by_id):
            # Già risolto
            resolved_actor_locs[actor["id"]] = loc_id
            npc_resolved += 1
            continue

        new_loc = resolve_actor_location(actor, loc_by_id, loc_by_name)
        if new_loc:
            actor["location_id"] = new_loc
            resolved_actor_locs[actor["id"]] = new_loc
            npc_resolved += 1
        else:
            # Non risolto - lascia invariato ma non conta
            pass

    print(f"  NPC risolti: {npc_resolved}/{npc_total}")

    # --- Step 3: Fix Clue source_location rotti ---
    clue_total = len(clues)
    clue_resolved = 0

    for clue in clues:
        src = clue.get("source_location", "")
        if src and src in loc_by_id:
            clue_resolved += 1
            continue

        new_loc = resolve_clue_location(
            clue, loc_by_id, loc_by_name, actors, resolved_actor_locs
        )
        if new_loc:
            clue["source_location"] = new_loc
            clue_resolved += 1

    print(f"  Clue risolti: {clue_resolved}/{clue_total}")

    # --- Step 4: Popola contains_actors e contains_clues ---
    locs_with_actors = 0
    locs_with_clues = 0

    for loc in locations:
        lid = loc["id"]
        new_actors = [a["id"] for a in actors if a.get("location_id") == lid]
        new_clues = [
            c["id"] for c in clues
            if c.get("source_location") == lid or c.get("location_id") == lid
        ]
        if new_actors or loc.get("contains_actors") != new_actors:
            loc["contains_actors"] = new_actors
        if new_clues or loc.get("contains_clues") != new_clues:
            loc["contains_clues"] = new_clues
        if new_actors:
            locs_with_actors += 1
        if new_clues:
            locs_with_clues += 1

    print(f"  contains_actors popolato: {locs_with_actors}/{len(locations)} location")
    print(f"  contains_clues popolato: {locs_with_clues}/{len(locations)} location")

    # --- Step 5: Fix FOW ---
    fow_updated = fix_fow(locations)
    print(f"  FOW aggiornato: {fow_updated}/{len(locations)} location")

    # --- Step 6: Salva ---
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()


def main():
    # Determina base_dir: la directory del repo (parent di scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)

    print(f"Base dir: {base_dir}")
    print()

    for filepath in FILES:
        full = os.path.join(base_dir, filepath)
        if not os.path.exists(full):
            print(f"ATTENZIONE: file non trovato: {full}")
            continue
        fix_file(filepath, base_dir)

    print("Fatto.")


if __name__ == "__main__":
    main()
