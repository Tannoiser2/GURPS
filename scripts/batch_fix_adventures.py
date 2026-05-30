#!/usr/bin/env python3
"""
Batch fix retroattivo su avventure AI esistenti.

Corregge i JSON salvati in data/compiled_adventures/ (solo file ai_*.json).
Applica 4 fix diretti sul JSON senza chiamare il backend.
"""

import json
import re
import glob
import os
import unicodedata
from pathlib import Path
from typing import Optional

# ─── Patterns ────────────────────────────────────────────────────────────────
PLACEHOLDER_PATTERN = re.compile(
    r'^(loc_ai_\d+|loc_start|loc_node\w*|loc_finale|loc_\d+)$',
    re.IGNORECASE
)
CLUE_PLACEHOLDER_PATTERN = re.compile(r'^clue_ai_\d+$')


def is_placeholder_loc(loc_id: str) -> bool:
    return bool(PLACEHOLDER_PATTERN.match(str(loc_id or '')))


def is_placeholder_clue(clue_id: str) -> bool:
    return bool(CLUE_PLACEHOLDER_PATTERN.match(str(clue_id or '')))


def slugify(text: str, max_len: int = 40) -> str:
    """Lowercase, spazi→underscore, solo caratteri sicuri, max 40 char."""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    # Sostituisce tutto ciò che non è alfanumerico o underscore con underscore
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = text.strip('_')
    return text[:max_len]


# ─── FIX 1 ───────────────────────────────────────────────────────────────────
def fix1_location_placeholder(ad: dict) -> int:
    """
    Fix 1 — Location placeholder → rebuild da refs NPC/clue (se possibili)
    o normalizzazione se struttura interna coerente.
    Ritorna numero di sotto-fix applicati.
    """
    locations = ad.get('locations', [])
    actors = ad.get('actors', [])
    clues = ad.get('clues', [])
    fixes = 0

    if not locations:
        return 0

    loc_ids = [l.get('id', '') for l in locations]

    # Controlla se TUTTE le location hanno ID placeholder
    all_placeholder = all(is_placeholder_loc(lid) for lid in loc_ids)
    if not all_placeholder:
        return 0

    # Raccoglie i riferimenti degli actor e dei clue
    actor_lids = [a.get('location_id') or '' for a in actors]
    clue_src = []
    for c in clues:
        clue_src.append(c.get('source_location') or '')
        clue_src.append(c.get('location_id') or '')

    all_refs = [r for r in actor_lids + clue_src if r]
    all_refs_placeholder = all(is_placeholder_loc(r) for r in all_refs) if all_refs else True

    if not all_refs_placeholder:
        # Ramo A: i riferimenti in NPC/clue contengono nomi REALI
        # Estrae nomi unici non-placeholder dai campi location degli attori e clue
        real_names = []
        seen = set()
        for val in all_refs:
            if val and not is_placeholder_loc(val) and val not in seen:
                real_names.append(val)
                seen.add(val)

        if not real_names:
            return 0

        # Costruisce mappa nome → slug ID
        name_to_slug = {}
        slug_count: dict[str, int] = {}
        for name in real_names:
            slug = slugify(name)
            if not slug:
                slug = 'location'
            if slug in slug_count:
                slug_count[slug] += 1
                slug = f"{slug}_{slug_count[slug]}"
            else:
                slug_count[slug] = 0
            name_to_slug[name] = slug

        # Ricostruisce le location con gli slug (mantenendo campi esistenti)
        # Associa ogni placeholder location all'i-esima real_name (se disponibili)
        old_loc_ids = [l['id'] for l in locations]
        placeholder_to_slug = {}

        # Se il numero di location corrisponde ai nomi reali, mappa 1:1
        if len(real_names) == len(locations):
            for i, loc in enumerate(locations):
                old_id = loc['id']
                new_id = name_to_slug[real_names[i]]
                placeholder_to_slug[old_id] = new_id
                loc['id'] = new_id
                fixes += 1
        else:
            # Mappa le prime N, le restanti ottengono slug numerici
            for i, loc in enumerate(locations):
                old_id = loc['id']
                if i < len(real_names):
                    new_id = name_to_slug[real_names[i]]
                else:
                    new_id = slugify(loc.get('name', f'location_{i}'))
                    if not new_id:
                        new_id = f'location_{i}'
                placeholder_to_slug[old_id] = new_id
                loc['id'] = new_id
                fixes += 1

        # Aggiorna actor location_id
        for a in actors:
            old = a.get('location_id') or ''
            if old in placeholder_to_slug:
                a['location_id'] = placeholder_to_slug[old]
                fixes += 1
            elif old and is_placeholder_loc(old):
                # placeholder non mappato → usa il nome del campo se esistente
                a['location_id'] = slugify(old) or old

        # Aggiorna clue source_location e location_id
        for c in clues:
            for field in ('source_location', 'location_id'):
                old = c.get(field) or ''
                if old and not is_placeholder_loc(old):
                    # Già un nome reale → slug
                    slug = slugify(old)
                    if slug and slug != c.get(field):
                        c[field] = slug
                        fixes += 1
                elif old in placeholder_to_slug:
                    c[field] = placeholder_to_slug[old]
                    fixes += 1

    else:
        # Ramo B: i riferimenti sono ANCH'ESSI placeholder — struttura interna coerente
        # Normalizza i campi mancanti
        for loc in locations:
            changed = False
            if not loc.get('location_type'):
                loc['location_type'] = 'regional'
                changed = True
            if not loc.get('status'):
                loc['status'] = 'unknown'
                changed = True
            if loc.get('connections_to') is None:
                loc['connections_to'] = []
                changed = True
            if loc.get('contains_actors') is None:
                loc['contains_actors'] = []
                changed = True
            if loc.get('contains_clues') is None:
                loc['contains_clues'] = []
                changed = True
            if changed:
                fixes += 1

    return fixes


# ─── FIX 2 ───────────────────────────────────────────────────────────────────
def fix2_populate_contains(ad: dict) -> int:
    """
    Fix 2 — Popola contains_actors e contains_clues per ogni location.
    Ritorna numero di location aggiornate.
    """
    locations = ad.get('locations', [])
    actors = ad.get('actors', [])
    clues = ad.get('clues', [])
    fixes = 0

    for loc in locations:
        loc_id = loc.get('id', '')

        # Actors in questa location
        new_actors = [
            a['id'] for a in actors
            if a.get('location_id') == loc_id and a.get('id')
        ]

        # Clues in questa location
        new_clues = [
            c['id'] for c in clues
            if c.get('id') and (
                c.get('location_id') == loc_id or
                c.get('source_location') == loc_id
            )
        ]

        changed = False
        current_actors = loc.get('contains_actors') or []
        current_clues = loc.get('contains_clues') or []

        if set(current_actors) != set(new_actors):
            loc['contains_actors'] = new_actors
            changed = True
        if set(current_clues) != set(new_clues):
            loc['contains_clues'] = new_clues
            changed = True

        if changed:
            fixes += 1

    return fixes


# ─── FIX 3 ───────────────────────────────────────────────────────────────────
def fix3_finale_conditions(ad: dict) -> int:
    """
    Fix 3 — Corregge required_clues rotti nelle finale_conditions.
    Ritorna numero di entries corrette.
    """
    finale_conditions = ad.get('finale_conditions', [])
    clues = ad.get('clues', [])
    fixes = 0

    if not isinstance(finale_conditions, list):
        return 0

    real_clue_ids = {c.get('id', '') for c in clues if c.get('id')}

    # Prepara fallback: prima i required, poi tutti
    required_clues = [c['id'] for c in clues if c.get('is_required') and c.get('id')]
    fallback_clues = [c['id'] for c in clues if c.get('id')]

    for entry in finale_conditions:
        req = entry.get('required_clues', [])
        if not req:
            continue

        # Controlla se ci sono clue placeholder non presenti nei clue reali
        broken = [x for x in req if is_placeholder_clue(x) and x not in real_clue_ids]
        if broken:
            # Sostituisce con i primi 3 clue is_required=True, altrimenti i primi 3
            replacement = (required_clues[:3] if required_clues else fallback_clues[:3])
            entry['required_clues'] = replacement
            fixes += 1

    return fixes


# ─── FIX 4 ───────────────────────────────────────────────────────────────────
def fix4_fow_status(ad: dict) -> int:
    """
    Fix 4 — Fog of War: imposta status coerente per tipo di location.
    Ritorna numero di location aggiornate.
    """
    locations = ad.get('locations', [])
    fixes = 0

    FOW_EMPTY = {None, 'open', ''}

    for loc in locations:
        current_status = loc.get('status')
        if current_status not in FOW_EMPTY:
            continue

        loc_type = loc.get('location_type', '') or ''

        if loc_type == 'strategic':
            new_status = 'known'
        elif loc_type == 'local':
            new_status = 'hidden'
        else:
            new_status = 'unknown'

        loc['status'] = new_status
        fixes += 1

    return fixes


# ─── MAIN ────────────────────────────────────────────────────────────────────
def process_file(filepath: str) -> None:
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    ad = data.get('adventure_definition', {})
    if not ad:
        print(f"  [SKIP] Nessuna adventure_definition: {filepath}")
        return

    title = ad.get('title', os.path.basename(filepath))
    total_fixes = 0
    fix_log = []

    # Fix 1
    n = fix1_location_placeholder(ad)
    total_fixes += n
    if n:
        fix_log.append(f"Fix1(placeholder→rebuild/normalize): {n}")

    # Fix 2
    n = fix2_populate_contains(ad)
    total_fixes += n
    if n:
        fix_log.append(f"Fix2(contains_actors/clues): {n} locations")

    # Fix 3
    n = fix3_finale_conditions(ad)
    total_fixes += n
    if n:
        fix_log.append(f"Fix3(finale_conditions): {n} entries")

    # Fix 4
    n = fix4_fow_status(ad)
    total_fixes += n
    if n:
        fix_log.append(f"Fix4(FOW status): {n} locations")

    # Salva
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    rel = os.path.relpath(filepath, '/home/user/GURPS/data/compiled_adventures')
    if total_fixes:
        print(f"  ✓ [{rel}] '{title}' — {total_fixes} fix totali: {', '.join(fix_log)}")
    else:
        print(f"  · [{rel}] '{title}' — nessun fix necessario")


def main():
    base = '/home/user/GURPS/data/compiled_adventures'
    pattern = f'{base}/**/*.json'
    all_files = glob.glob(pattern, recursive=True)

    # Solo file ai_*.json, non pdf_*
    ai_files = [
        f for f in sorted(all_files)
        if os.path.basename(f).startswith('ai_')
        and '_debug_pdf' not in f
    ]

    print(f"\n{'='*70}")
    print(f"  BATCH FIX — Avventure AI ({len(ai_files)} file)")
    print(f"{'='*70}\n")

    for fp in ai_files:
        process_file(fp)

    print(f"\n{'='*70}")
    print("  DONE")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
