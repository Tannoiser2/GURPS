#!/usr/bin/env python3
"""
Classifica avventure GURPS compilate.
Calcola un punteggio composito 0-100 per ogni avventura.
"""

import json
import glob
import os
import re
from pathlib import Path

# ─── PLACEHOLDER IDs da escludere ────────────────────────────────────────────
PLACEHOLDER_PATTERN = re.compile(
    r'^(loc_ai_\d+|loc_start|loc_node\w*|loc_finale|loc_\d+)$',
    re.IGNORECASE
)

def is_placeholder_id(loc_id: str) -> bool:
    return bool(PLACEHOLDER_PATTERN.match(loc_id))


def get_playable_score(d: dict) -> float:
    """
    Estrae il punteggio playable/doctor (0-100) dal JSON.
    Restituisce valore 0-100.
    """
    vr = d.get('validation_report', {})

    # 1. validation_report.playable_score (già 0-100)
    if 'playable_score' in vr:
        return float(vr['playable_score'])

    # 2. validation_report.quality_gate.score (già 0-100)
    qg = vr.get('quality_gate', {})
    if 'score' in qg:
        return float(qg['score'])

    # 3. _doctor_score * 10 (da 0-10 a 0-100)
    ad = d.get('adventure_definition', {})
    if '_doctor_score' in ad:
        return float(ad['_doctor_score']) * 10.0
    if '_doctor_score' in d:
        return float(d['_doctor_score']) * 10.0

    return 0.0


def score_location_structure(locations: list) -> int:
    """Criterio 2: struttura location (0-25)."""
    if not locations:
        return 0

    points = 0
    loc_ids = {l['id'] for l in locations}
    n = len(locations)

    # +5 se TUTTE le location hanno exits/connections non vuoti
    # (connections_to o exits usato come proxy per connections_to)
    all_connected = all(
        (l.get('exits') or l.get('connections_to'))
        for l in locations
    )
    if all_connected:
        points += 5

    # +5 se almeno 50% ha contains_actors non vuoto
    actors_count = sum(1 for l in locations if l.get('contains_actors'))
    if actors_count / n >= 0.5:
        points += 5

    # +5 se almeno 50% ha contains_clues non vuoto
    clues_count = sum(1 for l in locations if l.get('contains_clues'))
    if clues_count / n >= 0.5:
        points += 5

    # +5 se FOW differenziato (non tutti con stesso status/access_state)
    statuses = {l.get('status') for l in locations}
    access_states = {l.get('access_state') for l in locations}
    if len(statuses) > 1 or len(access_states) > 1:
        points += 5

    # +5 se NON ci sono location con ID placeholder
    has_placeholder = any(is_placeholder_id(l['id']) for l in locations)
    if not has_placeholder:
        points += 5

    return points


def score_cross_references(locations: list, actors: list, clues: list) -> int:
    """Criterio 3: integrità cross-reference (0-20)."""
    loc_ids = {l['id'] for l in locations}
    points = 0

    # +10 per NPC con location_id valido (o senza location_id)
    if actors:
        broken_actors = 0
        total_with_loc = 0
        for a in actors:
            lid = a.get('location_id')
            if lid:
                total_with_loc += 1
                if lid not in loc_ids:
                    broken_actors += 1
        if total_with_loc == 0:
            points += 10  # nessun riferimento = nessun errore
        else:
            ratio_ok = 1.0 - (broken_actors / total_with_loc)
            points += round(10 * ratio_ok)
    else:
        points += 10  # nessun attore = no cross-ref

    # +10 per clue con source_location/location_id validi (o null)
    if clues:
        broken_clues = 0
        total_with_loc = 0
        for c in clues:
            src = c.get('source_location') or c.get('location_id')
            if src:
                total_with_loc += 1
                if src not in loc_ids:
                    broken_clues += 1
        if total_with_loc == 0:
            points += 10
        else:
            ratio_ok = 1.0 - (broken_clues / total_with_loc)
            points += round(10 * ratio_ok)
    else:
        points += 10

    return points


def score_content_richness(clues: list, actors: list, clocks: list) -> int:
    """Criterio 4: ricchezza contenuto (0-15)."""
    points = 0
    if len(clues) >= 6:
        points += 5
    if len(actors) >= 3:
        points += 5
    # almeno 1 clock con più di 3 step
    for ck in clocks:
        steps = ck.get('steps', [])
        if len(steps) > 3:
            points += 5
            break
    return points


def determine_source(filename: str) -> str:
    base = os.path.basename(filename)
    if base.startswith('pdf_'):
        return 'PDF'
    elif base.startswith('ai_') or base == 'peometeo.json':
        return 'AI'
    return 'AI'


def compute_score(d: dict, filepath: str) -> dict:
    ad = d.get('adventure_definition', {})
    locations = ad.get('locations', [])
    actors = ad.get('actors', [])
    clues = ad.get('clues', [])
    clocks = ad.get('event_clocks', [])

    # --- Criterio 1: playable/doctor score (0-40) ---
    raw_playable = get_playable_score(d)   # 0-100
    c1 = round(raw_playable * 40 / 100)   # scala 0-40

    # --- Criterio 2: struttura location (0-25) ---
    c2 = score_location_structure(locations)

    # --- Criterio 3: cross-reference (0-20) ---
    c3 = score_cross_references(locations, actors, clues)

    # --- Criterio 4: ricchezza (0-15) ---
    c4 = score_content_richness(clues, actors, clocks)

    total = c1 + c2 + c3 + c4

    # Metadati
    title = ad.get('title', os.path.basename(filepath).replace('.json', ''))
    source = determine_source(filepath)
    genre_folder = Path(filepath).parent.name
    genre = ad.get('genre', genre_folder)
    if isinstance(genre, list):
        genre = genre[0] if genre else genre_folder

    # Conta clock con steps > 3
    multi_step_clocks = sum(1 for ck in clocks if len(ck.get('steps', [])) > 3)

    return {
        'filepath': filepath,
        'title': title,
        'source': source,
        'genre': genre,
        'total_score': total,
        'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4,
        'raw_playable': raw_playable,
        'n_locations': len(locations),
        'n_actors': len(actors),
        'n_clues': len(clues),
        'n_clocks': len(clocks),
        'multi_step_clocks': multi_step_clocks,
        # detail per debug
        'has_placeholder_ids': any(is_placeholder_id(l['id']) for l in locations),
        'broken_actor_locs': sum(
            1 for a in actors
            if a.get('location_id') and a['location_id'] not in {l['id'] for l in locations}
        ),
        'broken_clue_locs': sum(
            1 for c in clues
            if (c.get('source_location') or c.get('location_id'))
            and (c.get('source_location') or c.get('location_id')) not in {l['id'] for l in locations}
        ),
    }


def short_title(title: str, maxlen: int = 28) -> str:
    if len(title) <= maxlen:
        return title.ljust(maxlen)
    return (title[:maxlen - 1] + '…').ljust(maxlen)


def short_genre(genre: str, maxlen: int = 11) -> str:
    if len(genre) <= maxlen:
        return genre.ljust(maxlen)
    return genre[:maxlen].ljust(maxlen)


def main():
    pattern = '/home/user/GURPS/data/compiled_adventures/**/*.json'
    files = glob.glob(pattern, recursive=True)
    files = [
        f for f in files
        if '_debug_pdf' not in f
        and 'index.json' not in f
    ]

    results = []
    for fp in sorted(files):
        try:
            with open(fp, encoding='utf-8') as f:
                d = json.load(f)
            r = compute_score(d, fp)
            results.append(r)
        except Exception as e:
            print(f"  [ERRORE] {fp}: {e}")

    # Ordina per score decrescente, poi titolo alfabetico
    results.sort(key=lambda x: (-x['total_score'], x['title']))

    # ─── CLASSIFICA COMPLETA ──────────────────────────────────────────────────
    print()
    print("=" * 105)
    print("  CLASSIFICA COMPLETA — AVVENTURE GURPS COMPILATE")
    print("=" * 105)
    header = f"{'#':>3} | {'SCORE':>5} | {'Titolo':<28} | {'Fonte':<5} | {'Genere':<11} | {'Loc':>3} | {'NPC':>3} | {'Clue':>4} | {'Clock':>5}"
    print(header)
    print("-" * 105)

    for i, r in enumerate(results, 1):
        line = (
            f"{i:>3} | "
            f"{r['total_score']:>5} | "
            f"{short_title(r['title'])} | "
            f"{r['source']:<5} | "
            f"{short_genre(r['genre'])} | "
            f"{r['n_locations']:>3} | "
            f"{r['n_actors']:>3} | "
            f"{r['n_clues']:>4} | "
            f"{r['n_clocks']:>5}"
        )
        print(line)

    print()

    # ─── TOP 10 ASSOLUTA ─────────────────────────────────────────────────────
    print("=" * 105)
    print("  TOP 10 ASSOLUTA — con commento sui punti di forza")
    print("=" * 105)

    top10 = results[:10]
    for i, r in enumerate(top10, 1):
        strengths = []
        if r['c1'] >= 36:
            strengths.append(f"score validazione eccellente ({r['raw_playable']:.0f}/100)")
        elif r['c1'] >= 28:
            strengths.append(f"buona validazione ({r['raw_playable']:.0f}/100)")
        if r['c2'] == 25:
            strengths.append("struttura location perfetta")
        elif r['c2'] >= 20:
            strengths.append(f"struttura location solida ({r['c2']}/25)")
        if r['c3'] == 20:
            strengths.append("cross-ref senza errori")
        elif r['c3'] >= 15:
            strengths.append(f"cross-ref buono ({r['c3']}/20)")
        if r['c4'] == 15:
            strengths.append("contenuto ricco (clue+NPC+clock)")
        elif r['c4'] >= 10:
            strengths.append(f"buon contenuto ({r['c4']}/15)")
        if r['n_clues'] >= 10:
            strengths.append(f"{r['n_clues']} clue")
        if r['n_actors'] >= 5:
            strengths.append(f"{r['n_actors']} NPC")
        if r['multi_step_clocks'] >= 2:
            strengths.append(f"{r['multi_step_clocks']} clock articolati")
        comment = "; ".join(strengths) if strengths else "punteggio equilibrato"
        print(f"  #{i:>2} [{r['total_score']:>3}] {r['title'][:40]:<40}  ({r['source']}/{r['genre'][:10]})")
        print(f"        → {comment}")
    print()

    # ─── TOP 5 AI ────────────────────────────────────────────────────────────
    ai_results = [r for r in results if r['source'] == 'AI']
    pdf_results = [r for r in results if r['source'] == 'PDF']

    print("=" * 105)
    print("  TOP 5 AI")
    print("=" * 105)
    for i, r in enumerate(ai_results[:5], 1):
        print(f"  #{i} [{r['total_score']:>3}] {r['title'][:50]:<50}  Loc:{r['n_locations']} NPC:{r['n_actors']} Clue:{r['n_clues']} Clock:{r['n_clocks']}")
    print()

    # ─── TOP 5 PDF ───────────────────────────────────────────────────────────
    print("=" * 105)
    print("  TOP 5 PDF")
    print("=" * 105)
    for i, r in enumerate(pdf_results[:5], 1):
        print(f"  #{i} [{r['total_score']:>3}] {r['title'][:50]:<50}  Loc:{r['n_locations']} NPC:{r['n_actors']} Clue:{r['n_clues']} Clock:{r['n_clocks']}")
    print()

    # ─── FONDO CLASSIFICA ────────────────────────────────────────────────────
    print("=" * 105)
    print("  FONDO CLASSIFICA — Ultime 5 (con motivazione)")
    print("=" * 105)
    bottom5 = results[-5:]
    for i, r in enumerate(bottom5, len(results) - 4):
        problems = []
        if r['c1'] <= 12:
            problems.append(f"validazione bassa ({r['raw_playable']:.0f}/100, solo {r['c1']}/40 pt)")
        if r['c2'] <= 5:
            problems.append(f"struttura location carente ({r['c2']}/25 pt)")
        if r['c3'] <= 10:
            problems.append(f"cross-ref rotti ({r['broken_actor_locs']} attori, {r['broken_clue_locs']} clue)")
        if r['c4'] <= 5:
            problems.append(f"contenuto scarso (clue:{r['n_clues']}, NPC:{r['n_actors']}, clock:{r['n_clocks']})")
        if r['has_placeholder_ids']:
            problems.append("ID location placeholder (loc_ai_X, ecc.)")
        note = "; ".join(problems) if problems else "punteggio complessivamente basso"
        print(f"  #{i:>2} [{r['total_score']:>3}] {r['title'][:40]:<40}  ({r['source']}/{r['genre'][:10]})")
        print(f"        → PROBLEMI: {note}")
    print()

    # ─── STATISTICHE SINTETICHE ──────────────────────────────────────────────
    print("=" * 105)
    print("  STATISTICHE SINTETICHE")
    print("=" * 105)
    scores = [r['total_score'] for r in results]
    print(f"  Totale avventure: {len(results)}  (AI: {len(ai_results)}, PDF: {len(pdf_results)})")
    print(f"  Score medio:      {sum(scores)/len(scores):.1f}")
    print(f"  Score mediano:    {sorted(scores)[len(scores)//2]}")
    print(f"  Score massimo:    {max(scores)}  ({results[0]['title'][:40]})")
    print(f"  Score minimo:     {min(scores)}  ({results[-1]['title'][:40]})")
    ai_scores = [r['total_score'] for r in ai_results]
    pdf_scores = [r['total_score'] for r in pdf_results]
    if ai_scores:
        print(f"  Media AI:         {sum(ai_scores)/len(ai_scores):.1f}")
    if pdf_scores:
        print(f"  Media PDF:        {sum(pdf_scores)/len(pdf_scores):.1f}")
    print()


if __name__ == '__main__':
    main()
