#!/usr/bin/env python3
"""
Analisi completa delle avventure AI-generate in data/compiled_adventures/
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path("/home/user/GURPS/data/compiled_adventures")

# Pattern per ID placeholder
PLACEHOLDER_PATTERNS = [
    r'^loc_ai_\w+$',
    r'^loc_node\d+$',
    r'^loc_start$',
    r'^loc_finale$',
    r'^area_\d+$',
    r'^location_\d+$',
    r'^loc_\d+$',
    r'^scene_\d+$',
]

def is_placeholder_id(loc_id):
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, loc_id, re.IGNORECASE):
            return True
    return False

def load_adventures():
    adventures = []
    for path in sorted(BASE_DIR.rglob("ai_*.json")):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            adventures.append((path, data))
        except Exception as e:
            print(f"ERROR loading {path}: {e}")
    return adventures

def analyze_adventure(path, data):
    ad = data.get('adventure_definition', {})
    vr = data.get('validation_report', {})

    result = {
        'file': str(path),
        'filename': path.name,
        'genre_dir': path.parent.name,
        'id': ad.get('id', '?'),
        'title': ad.get('title', '?'),
        'genre': ad.get('genre', path.parent.name),
        'tone': ad.get('tone', ''),
        'scale': None,  # non presente nei JSON
        'problems': [],
        'strengths': [],
    }

    # Doctor score from validation_report.quality_gate.score
    qg = vr.get('quality_gate', {})
    result['doctor_score'] = qg.get('score', None)
    result['vr_passed'] = vr.get('passed', None)
    result['vr_issues'] = qg.get('issues', [])
    result['vr_warnings'] = qg.get('warnings', [])

    # --- Raccolta dati base ---
    actors = ad.get('actors', []) or []
    clues = ad.get('clues', []) or []
    locations = ad.get('locations', []) or []
    clocks = ad.get('event_clocks', []) or []
    pressure_systems = ad.get('pressure_systems', []) or []
    finale_conditions = ad.get('finale_conditions', []) or []
    revelations = ad.get('revelations', []) or []

    result['n_actors'] = len(actors)
    result['n_clues'] = len(clues)
    result['n_locations'] = len(locations)
    result['n_clocks'] = len(clocks)
    result['n_pressure'] = len(pressure_systems)
    result['n_finale'] = len(finale_conditions)

    # Valutazione base struttura
    if result['n_actors'] == 0:
        result['problems'].append("CRITICO: Nessun NPC/attore definito")
    if result['n_clues'] == 0:
        result['problems'].append("CRITICO: Nessuna clue definita")
    if result['n_locations'] == 0:
        result['problems'].append("CRITICO: Nessuna location definita")

    # --- Analisi location ---
    loc_ids = set(loc.get('id', '') for loc in locations)

    # Location type (usa campo 'type')
    loc_types = defaultdict(int)
    loc_with_connections = 0
    loc_with_actors = 0
    loc_with_clues = 0
    placeholder_locs = []
    fow_values = set()

    for loc in locations:
        lid = loc.get('id', '')
        ltype = loc.get('type', None)
        loc_types[ltype] += 1

        # connections: controlla sia connections_to sia exits
        connections = loc.get('connections_to') or loc.get('exits') or []
        if connections:
            loc_with_connections += 1

        # contains_actors
        ca = loc.get('contains_actors') or []
        if ca:
            loc_with_actors += 1

        # contains_clues
        cc = loc.get('contains_clues') or []
        if cc:
            loc_with_clues += 1

        # placeholder check
        if is_placeholder_id(lid):
            placeholder_locs.append(lid)

        # FOW / access_state / status
        fow = loc.get('access_state') or loc.get('status')
        if fow:
            fow_values.add(fow)

    result['loc_types'] = dict(loc_types)
    result['loc_with_connections'] = loc_with_connections
    result['loc_with_actors'] = loc_with_actors
    result['loc_with_clues'] = loc_with_clues
    result['placeholder_locs'] = placeholder_locs
    result['fow_values'] = list(fow_values)
    result['fow_differentiated'] = len(fow_values) > 1

    n_locs = len(locations)
    pct_placeholder = len(placeholder_locs) / n_locs * 100 if n_locs else 0
    result['pct_placeholder'] = pct_placeholder

    if placeholder_locs:
        result['problems'].append(
            f"Location con ID placeholder ({len(placeholder_locs)}/{n_locs}): {', '.join(placeholder_locs)}"
        )

    if not result['fow_differentiated'] and n_locs > 1:
        fow_val = list(fow_values)[0] if fow_values else 'None'
        result['problems'].append(f"FOW non differenziato: tutte le location hanno stato '{fow_val}'")

    if loc_with_connections == 0 and n_locs > 1:
        result['problems'].append("Nessuna location ha connections/exits definiti")
    elif loc_with_connections < n_locs and n_locs > 1:
        result['problems'].append(
            f"Solo {loc_with_connections}/{n_locs} location hanno connections/exits"
        )

    if loc_with_actors == 0 and len(actors) > 0:
        result['problems'].append("Nessuna location ha contains_actors (NPC non collocati)")
    if loc_with_clues == 0 and len(clues) > 0:
        result['problems'].append("Nessuna location ha contains_clues (clue non collocate)")

    # Punti di forza location
    if n_locs >= 5 and loc_with_connections >= n_locs * 0.7:
        result['strengths'].append(f"Buona rete di connections tra location ({loc_with_connections}/{n_locs})")
    if result['fow_differentiated']:
        result['strengths'].append(f"FOW differenziato: {', '.join(sorted(fow_values))}")

    # --- Cross-reference integrità ---
    broken_actor_locations = []
    for actor in actors:
        aloc = actor.get('location_id')
        if aloc and aloc not in loc_ids:
            broken_actor_locations.append((actor.get('id', '?'), aloc))

    result['broken_actor_locations'] = broken_actor_locations
    if broken_actor_locations:
        details = ', '.join(f"{a}→{l}" for a,l in broken_actor_locations)
        result['problems'].append(
            f"NPC con location_id non esistente ({len(broken_actor_locations)}): {details}"
        )

    # Clue con source_location null o rotto
    clue_ids = set(c.get('id', '') for c in clues)
    broken_clue_locations = []
    null_clue_locations = []
    for clue in clues:
        sloc = clue.get('source_location')
        if sloc is None:
            null_clue_locations.append(clue.get('id', '?'))
        elif sloc not in loc_ids:
            broken_clue_locations.append((clue.get('id', '?'), sloc))

    result['null_clue_locations'] = null_clue_locations
    result['broken_clue_locations'] = broken_clue_locations

    if null_clue_locations:
        result['problems'].append(
            f"Clue con source_location null ({len(null_clue_locations)}): {', '.join(null_clue_locations[:5])}"
            + ("..." if len(null_clue_locations) > 5 else "")
        )
    if broken_clue_locations:
        details = ', '.join(f"{c}→{l}" for c,l in broken_clue_locations)
        result['problems'].append(
            f"Clue con source_location non esistente ({len(broken_clue_locations)}): {details}"
        )

    # Finale conditions: required_clues che non esistono
    broken_finale_clues = []
    for fc in finale_conditions:
        for rc in (fc.get('required_clues') or []):
            if rc not in clue_ids:
                broken_finale_clues.append((fc.get('id', '?'), rc))

    result['broken_finale_clues'] = broken_finale_clues
    if broken_finale_clues:
        details = ', '.join(f"{f}:{c}" for f,c in broken_finale_clues)
        result['problems'].append(
            f"finale_conditions con required_clues non esistenti ({len(broken_finale_clues)}): {details}"
        )

    # Check anche required_threads nelle finale
    thread_ids = set()
    for st in (ad.get('story_threads') or []):
        tid = st.get('id')
        if tid:
            thread_ids.add(tid)

    broken_finale_threads = []
    for fc in finale_conditions:
        for rt in (fc.get('required_threads') or []):
            if thread_ids and rt not in thread_ids:
                broken_finale_threads.append((fc.get('id', '?'), rt))
    result['broken_finale_threads'] = broken_finale_threads

    # Punti di forza cross-ref
    if not broken_actor_locations and len(actors) > 0:
        result['strengths'].append("Tutti gli NPC hanno location_id validi")
    if not null_clue_locations and not broken_clue_locations and len(clues) > 0:
        result['strengths'].append("Tutte le clue hanno source_location validi")
    if not broken_finale_clues and len(finale_conditions) > 0:
        result['strengths'].append("Le finale_conditions referenziano clue esistenti")

    # --- Analisi Clock ---
    clock_analysis = []
    for clock in clocks:
        steps = clock.get('steps') or []
        max_val = clock.get('max_value', 0)
        n_steps = len(steps)

        # Step duplicati
        step_texts = [s.get('event', '') for s in steps]
        dup_steps = [t for t in step_texts if step_texts.count(t) > 1]
        unique_dups = list(set(dup_steps))

        clock_analysis.append({
            'id': clock.get('id', '?'),
            'label': clock.get('label', '?'),
            'n_steps': n_steps,
            'max_value': max_val,
            'dup_steps': unique_dups,
        })

    result['clock_analysis'] = clock_analysis

    for ca in clock_analysis:
        if ca['dup_steps']:
            result['problems'].append(
                f"Clock '{ca['id']}': step duplicati: {', '.join(ca['dup_steps'][:2])}"
            )
        if ca['n_steps'] == 0:
            result['problems'].append(f"Clock '{ca['id']}': nessuno step definito (max={ca['max_value']})")
        elif ca['max_value'] > 0 and ca['n_steps'] < ca['max_value'] // 2:
            result['problems'].append(
                f"Clock '{ca['id']}': solo {ca['n_steps']} step su max={ca['max_value']}"
            )

    if clocks and not any(ca['dup_steps'] for ca in clock_analysis) and all(ca['n_steps'] > 0 for ca in clock_analysis):
        result['strengths'].append(f"{len(clocks)} clock con step completi e non duplicati")

    # Punti di forza generali
    if result['n_actors'] >= 5:
        result['strengths'].append(f"Buon numero di NPC ({result['n_actors']})")
    if result['n_clues'] >= 6:
        result['strengths'].append(f"Buon numero di clue ({result['n_clues']})")
    if result['n_pressure'] > 0:
        result['strengths'].append(f"Pressure systems definiti ({result['n_pressure']})")
    if result['n_finale'] >= 2:
        result['strengths'].append(f"Più finali disponibili ({result['n_finale']})")

    # Calcolo % riferimenti rotti
    total_refs = len(actors) + len(clues) + sum(len(fc.get('required_clues') or []) for fc in finale_conditions)
    broken_refs = len(broken_actor_locations) + len(null_clue_locations) + len(broken_clue_locations) + len(broken_finale_clues)
    result['pct_broken_refs'] = (broken_refs / total_refs * 100) if total_refs else 0
    result['broken_refs_count'] = broken_refs
    result['total_refs_count'] = total_refs

    return result

def compute_genre_stats(all_results):
    genre_data = defaultdict(list)
    for r in all_results:
        genre_data[r['genre']].append(r)

    stats = {}
    for genre, adv_list in genre_data.items():
        scores = [a['doctor_score'] for a in adv_list if a['doctor_score'] is not None]
        pct_ph = [a['pct_placeholder'] for a in adv_list]
        pct_br = [a['pct_broken_refs'] for a in adv_list]

        stats[genre] = {
            'count': len(adv_list),
            'avg_score': sum(scores)/len(scores) if scores else None,
            'avg_pct_placeholder': sum(pct_ph)/len(pct_ph) if pct_ph else 0,
            'avg_pct_broken': sum(pct_br)/len(pct_br) if pct_br else 0,
            'adventures': adv_list,
        }
    return stats

def genre_quality_score(stat):
    """Score composito: score alto, placeholder basso, broken refs basso"""
    score = stat.get('avg_score') or 50
    ph = stat['avg_pct_placeholder']
    br = stat['avg_pct_broken']
    return score - ph * 0.5 - br * 0.3

def find_common_bugs(all_results):
    """Individua pattern di bug ricorrenti"""
    patterns = defaultdict(list)

    for r in all_results:
        if r['placeholder_locs']:
            patterns['ID location placeholder'].append(r['title'])
        if r['null_clue_locations']:
            patterns['Clue con source_location null'].append(r['title'])
        if r['broken_clue_locations']:
            patterns['Clue con source_location rotto'].append(r['title'])
        if r['broken_actor_locations']:
            patterns['NPC con location_id rotto'].append(r['title'])
        if r['broken_finale_clues']:
            patterns['Finale con required_clues rotti'].append(r['title'])
        if not r['fow_differentiated'] and r['n_locations'] > 1:
            patterns['FOW non differenziato'].append(r['title'])
        if r['loc_with_actors'] == 0 and r['n_actors'] > 0:
            patterns['NPC non collocati in location (contains_actors vuoto)'].append(r['title'])
        if r['loc_with_clues'] == 0 and r['n_clues'] > 0:
            patterns['Clue non collocate in location (contains_clues vuoto)'].append(r['title'])
        for ca in r['clock_analysis']:
            if ca['dup_steps']:
                patterns['Clock con step duplicati'].append(r['title'])
                break
        for ca in r['clock_analysis']:
            if ca['n_steps'] == 0:
                patterns['Clock senza step definiti'].append(r['title'])
                break

    return patterns

def generate_report(all_results, genre_stats):
    lines = []

    lines.append("# Analisi Avventure AI-Generate — GURPS Adventure System")
    lines.append(f"\n**Avventure analizzate:** {len(all_results)}  ")
    lines.append(f"**Generi:** {len(genre_stats)}  ")
    lines.append(f"**Data analisi:** 2026-05-30\n")

    # ============================================================
    lines.append("---\n")
    lines.append("## 1. Tabella Riassuntiva per Genere\n")

    headers = ["Genere", "N.", "Score medio", "% Placeholder", "% Ref rotti", "Qualità"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"]*len(headers)) + "|")

    sorted_genres = sorted(genre_stats.items(), key=lambda x: genre_quality_score(x[1]), reverse=True)

    for genre, stat in sorted_genres:
        score_str = f"{stat['avg_score']:.1f}" if stat['avg_score'] is not None else "N/A"
        ph_str = f"{stat['avg_pct_placeholder']:.1f}%"
        br_str = f"{stat['avg_pct_broken']:.1f}%"
        q = genre_quality_score(stat)
        if q >= 85:
            qual = "OTTIMA"
        elif q >= 70:
            qual = "BUONA"
        elif q >= 55:
            qual = "MEDIA"
        else:
            qual = "CRITICA"
        lines.append(f"| {genre} | {stat['count']} | {score_str} | {ph_str} | {br_str} | {qual} |")

    lines.append("")

    # ============================================================
    lines.append("---\n")
    lines.append("## 2. Report Individuale per Avventura\n")

    # Raggruppa per genere
    for genre, stat in sorted_genres:
        lines.append(f"### Genere: {genre.upper()}\n")
        for r in stat['adventures']:
            score_disp = str(r['doctor_score']) if r['doctor_score'] is not None else "N/A"
            lines.append(f"#### {r['title']}")
            lines.append(f"- **File:** `{r['filename']}`")
            lines.append(f"- **Genere:** {r['genre']}")
            lines.append(f"- **Doctor Score:** {score_disp}")
            lines.append(f"- **NPC:** {r['n_actors']} | **Clue:** {r['n_clues']} | **Location:** {r['n_locations']} | **Clock:** {r['n_clocks']} | **Pressure:** {r['n_pressure']} | **Finale:** {r['n_finale']}")

            # Location details
            loc_type_str = ", ".join(f"{t}: {n}" for t,n in sorted(r['loc_types'].items()))
            lines.append(f"- **Tipi location:** {loc_type_str if loc_type_str else 'N/A'}")
            lines.append(f"- **Location con connections:** {r['loc_with_connections']}/{r['n_locations']}")
            lines.append(f"- **Location con actors:** {r['loc_with_actors']}/{r['n_locations']}")
            lines.append(f"- **Location con clues:** {r['loc_with_clues']}/{r['n_locations']}")
            lines.append(f"- **FOW valori:** {', '.join(sorted(r['fow_values'])) if r['fow_values'] else 'N/A'} (differenziato: {'sì' if r['fow_differentiated'] else 'NO'})")

            # Clock details
            if r['clock_analysis']:
                clock_strs = [f"{ca['label']} ({ca['n_steps']} step / max {ca['max_value']})" for ca in r['clock_analysis']]
                lines.append(f"- **Clock:** {'; '.join(clock_strs)}")

            lines.append("")

            if r['strengths']:
                lines.append("**Punti di forza:**")
                for s in r['strengths']:
                    lines.append(f"- ✓ {s}")

            if r['problems']:
                lines.append("")
                lines.append("**Problemi critici:**")
                for p in r['problems']:
                    lines.append(f"- ✗ {p}")

            if not r['problems']:
                lines.append("")
                lines.append("*Nessun problema strutturale rilevato.*")

            lines.append("")

    # ============================================================
    lines.append("---\n")
    lines.append("## 3. Classifica Generi per Qualità Strutturale\n")
    lines.append("*(dal migliore al peggiore, basato su: score medio − penalità placeholder − penalità ref rotti)*\n")

    for rank, (genre, stat) in enumerate(sorted_genres, 1):
        q = genre_quality_score(stat)
        score_str = f"{stat['avg_score']:.1f}" if stat['avg_score'] is not None else "N/A"
        lines.append(f"{rank}. **{genre}** — Score composito: {q:.1f} | Score medio: {score_str} | {stat['count']} avventure")

        # Migliore e peggiore avventura del genere
        adv_with_scores = [(a, a['doctor_score']) for a in stat['adventures'] if a['doctor_score'] is not None]
        if adv_with_scores:
            best = max(adv_with_scores, key=lambda x: x[1])
            worst = min(adv_with_scores, key=lambda x: x[1])
            if best[0] != worst[0]:
                lines.append(f"   - Migliore: {best[0]['title']} ({best[1]})")
                lines.append(f"   - Peggiore: {worst[0]['title']} ({worst[1]})")
        lines.append("")

    # ============================================================
    lines.append("---\n")
    lines.append("## 4. Pattern Comuni di Bug\n")

    common_bugs = find_common_bugs(all_results)

    if not common_bugs:
        lines.append("*Nessun pattern di bug comune trovato.*\n")
    else:
        # Ordina per frequenza
        sorted_bugs = sorted(common_bugs.items(), key=lambda x: len(x[1]), reverse=True)

        for bug_name, affected in sorted_bugs:
            pct = len(affected) / len(all_results) * 100
            lines.append(f"### {bug_name}")
            lines.append(f"**Frequenza:** {len(affected)}/{len(all_results)} avventure ({pct:.0f}%)")
            lines.append(f"**Affette:** {', '.join(affected)}")
            lines.append("")

    # ============================================================
    lines.append("---\n")
    lines.append("## 5. Statistiche Globali\n")

    all_scores = [r['doctor_score'] for r in all_results if r['doctor_score'] is not None]
    total_problems = sum(len(r['problems']) for r in all_results)
    adv_with_problems = sum(1 for r in all_results if r['problems'])

    lines.append(f"- **Avventure totali:** {len(all_results)}")
    lines.append(f"- **Con doctor score:** {len(all_scores)}/{len(all_results)}")
    if all_scores:
        lines.append(f"- **Score medio globale:** {sum(all_scores)/len(all_scores):.1f}")
        lines.append(f"- **Score min/max:** {min(all_scores)} / {max(all_scores)}")
    lines.append(f"- **Avventure con problemi:** {adv_with_problems}/{len(all_results)} ({adv_with_problems/len(all_results)*100:.0f}%)")
    lines.append(f"- **Problemi totali rilevati:** {total_problems}")

    total_ph = sum(len(r['placeholder_locs']) for r in all_results)
    total_broken = sum(r['broken_refs_count'] for r in all_results)
    total_refs = sum(r['total_refs_count'] for r in all_results)

    lines.append(f"- **Location placeholder totali:** {total_ph}")
    lines.append(f"- **Riferimenti rotti totali:** {total_broken}/{total_refs} ({total_broken/total_refs*100:.1f}% se total_refs>0)" if total_refs else f"- **Riferimenti rotti totali:** {total_broken}")

    return "\n".join(lines)

def main():
    print("=== ANALISI AVVENTURE AI-GENERATE ===\n")

    adventures = load_adventures()
    print(f"Caricate {len(adventures)} avventure\n")

    all_results = []
    for path, data in adventures:
        r = analyze_adventure(path, data)
        all_results.append(r)
        print(f"  [{r['genre']}] {r['title']} — score={r['doctor_score']} | locs={r['n_locations']} | actors={r['n_actors']} | clues={r['n_clues']} | problems={len(r['problems'])}")

    print()
    genre_stats = compute_genre_stats(all_results)
    report = generate_report(all_results, genre_stats)

    # Salva report
    out_path = Path("/home/user/GURPS/ai_adventures_analysis.md")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport salvato in: {out_path}\n")
    print("=" * 80)
    print(report)
    print("=" * 80)

if __name__ == '__main__':
    main()
