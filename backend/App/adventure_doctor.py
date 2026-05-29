"""
Adventure Doctor — audit and AI-powered enrichment for adventure definitions.
Mirrors tools/json_doctor but runs inside the backend using claude_service.

Audit rules coverage:
  STRUCTURE   — campi obbligatori avventura
  NPC         — pressure_response, reaction_table, agenda, location coerenza
  CLOCK       — step, resolution, discovery_hint
  CLUE        — payoff, hidden_implication, wrong_interpretations, thread ref
  THREAD      — cicli parent, thread senza clue, parent inesistenti
  LOCATION    — location vuote, tactical_map incomplete, actor location ref
  RESOURCE    — risorse mancanti per genere
  EQUIPMENT   — armi NPC, item sconosciuti, skill_bonuses, loot, key_item ref
"""

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Set

from .claude_service import _call_claude as _claude_raw


def _llm(prompt: str, max_tokens: int = 1024) -> str:
    return _claude_raw(prompt, max_tokens=max_tokens)


# ─── Finding ──────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str    # "error" — blocks runtime (missing required fields)
                     # "warning" — degrades play experience
                     # "suggestion" — nice to have, cosmetic improvement
    category: str    # "structure" | "npc" | "clock" | "clue" | "thread" |
                     # "location" | "resource" | "equipment"
    entity_id: str
    message: str
    fix_hint: str = ""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ids(lst: list, key: str = "id") -> Set[str]:
    return {str(item.get(key, "")) for item in lst if item.get(key)}


def _detect_thread_cycles(threads: List[Dict]) -> List[str]:
    """Restituisce gli id di thread coinvolti in cicli parent_thread_ids."""
    graph: Dict[str, List[str]] = {
        t["id"]: list(t.get("parent_thread_ids") or [])
        for t in threads if t.get("id")
    }
    visited: Set[str] = set()
    in_stack: Set[str] = set()
    cycles: List[str] = []

    def dfs(node: str):
        visited.add(node)
        in_stack.add(node)
        for nb in graph.get(node, []):
            if nb not in visited:
                dfs(nb)
            elif nb in in_stack and nb not in cycles:
                cycles.append(nb)
        in_stack.discard(node)

    for tid in graph:
        if tid not in visited:
            dfs(tid)
    return cycles


# ─── Audit rules ──────────────────────────────────────────────────────────────

def _structure_rules(data: Dict) -> List[Finding]:
    findings = []
    title = data.get("title", data.get("id", "?"))
    for fld, sev, human_msg, hint in [
        ("premise",
         "error",
         "L'avventura non ha una premessa: i giocatori non sapranno da dove partire",
         "Aggiungi una descrizione generale dell'avventura (2-4 frasi che spiegano la situazione iniziale)"),
        ("initial_hook",
         "error",
         "Manca il gancio iniziale: il Master non ha una scena di apertura con cui coinvolgere i giocatori",
         "Aggiungi il gancio iniziale — la scena concreta in cui i PG vengono trascinati nell'avventura"),
        ("actors",
         "error",
         "L'avventura non ha personaggi non giocanti: non ci sono PNG con cui interagire",
         "Aggiungi almeno 2-3 PNG principali con motivazioni proprie"),
        ("locations",
         "warning",
         "Non sono definite le location: il Master non sa dove ambientare le scene",
         "Aggiungi le location principali dove si svolge l'avventura"),
        ("event_clocks",
         "warning",
         "Nessun clock di tensione: l'avventura non ha senso di urgenza né conseguenze per l'inattività",
         "Aggiungi almeno 1 clock per creare pressione temporale e rendere le scelte dei PG rilevanti"),
        ("finale_conditions",
         "suggestion",
         "Non sono definite le condizioni di vittoria/sconfitta: il Master non sa quando l'avventura finisce",
         "Definisci le condizioni di vittoria e sconfitta per dare una struttura narrativa chiara"),
    ]:
        if not data.get(fld):
            findings.append(Finding(sev, "structure", title, human_msg, hint))

    if not data.get("clues") and not data.get("story_threads"):
        findings.append(Finding("error", "structure", title,
            "L'avventura non ha indizi né piste narrative: i giocatori non hanno modo di progredire",
            "Aggiungi almeno 3-5 clues concreti o story_threads per guidare l'investigazione"))

    # Genere incompatibile con le armi dichiarate negli attori
    genre = str(data.get("genre", "")).lower()
    if genre:
        try:
            from .data_weapons import GENRE_ERA_MAP, WEAPON_BY_ID, ERA_MODERN
            valid_eras = set(GENRE_ERA_MAP.get(genre, [ERA_MODERN]))
            for actor in data.get("actors", []):
                for item_name in (actor.get("items") or []):
                    from .data_weapons import item_to_weapon_id
                    wid = item_to_weapon_id(str(item_name))
                    if wid:
                        w = WEAPON_BY_ID.get(wid)
                        if w and not any(e in valid_eras for e in (w.get("eras") or [])):
                            findings.append(Finding("warning", "equipment", actor.get("id", "?"),
                                f"NPC '{actor.get('name','?')}': arma '{item_name}' incompatibile con genere '{genre}'",
                                f"Usa un'arma dell'era corretta o correggi il genere"))
        except Exception:
            pass

    return findings


def _npc_rules(actors: List[Dict], location_ids: Set[str]) -> List[Finding]:
    findings = []
    for a in actors:
        aid = a.get("id", "?")
        name = a.get("name", aid)

        # pressure_response
        pr = a.get("pressure_response") or {}
        if not pr or len(pr) < 2:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': pressure_response assente o incompleto",
                "Aggiungi almeno i livelli low/medium/high/extreme"))

        # reaction_table
        rt = a.get("reaction_table") or {}
        if not rt or len(rt) < 2:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': reaction_table assente o incompleto",
                "Aggiungi almeno 2 situazioni (es. se_minacciato, se_alleato)"))

        # antagonista con pressione bassa
        if a.get("role") in ("villain", "antagonist") and (a.get("agenda_pressure") or 0) < 5:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': agenda_pressure {a.get('agenda_pressure',0)} troppo bassa per antagonista",
                "Imposta agenda_pressure tra 7 e 9"))

        # campi strategici
        _strategic_field_labels = {
            "goal": ("l'obiettivo dell'NPC", "cosa vuole ottenere dall'avventura"),
            "current_plan": ("il piano attuale dell'NPC", "cosa sta facendo concretamente adesso"),
            "fallback_plan": ("il piano di riserva", "cosa fa se il piano principale fallisce"),
        }
        for fld in ("goal", "current_plan", "fallback_plan"):
            if not a.get(fld):
                label, desc = _strategic_field_labels[fld]
                findings.append(Finding("suggestion", "npc", aid,
                    f"'{name}' non ha {label}: rende l'NPC piatto e prevedibile",
                    f"Aggiungi '{fld}': {desc}"))

        # location_id esistente
        loc_id = str(a.get("location_id") or "").strip()
        if loc_id and location_ids and loc_id not in location_ids:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': location_id '{loc_id}' non corrisponde a nessuna location",
                "Correggi location_id o aggiungi la location mancante"))

    return findings


def _clock_rules(clocks: List[Dict]) -> List[Finding]:
    findings = []
    for c in clocks:
        cid = c.get("id", "?")
        label = c.get("label", cid)

        if len(c.get("steps") or []) < 3:
            findings.append(Finding("warning", "clock", cid,
                f"Clock '{label}': meno di 3 step narrativi",
                "Aggiungi almeno 4 step con effetti progressivi crescenti"))

        if not c.get("resolution_condition"):
            findings.append(Finding("warning", "clock", cid,
                f"Clock '{label}': resolution_condition mancante",
                "Spiega come i PG possono fermare/invertire il clock"))

        if not c.get("discovery_hint"):
            findings.append(Finding("suggestion", "clock", cid,
                f"Il clock '{label}' non ha un presagio narrativo: i giocatori non hanno avvertimenti ambientali del pericolo",
                "Aggiungi discovery_hint: una frase evocativa che il Master può usare per segnalare il clock senza rivelare troppo"))

    return findings


def _clue_rules(clues: List[Dict], thread_ids: Set[str]) -> List[Finding]:
    findings = []
    for cl in clues:
        cid = cl.get("id", "?")
        label = cl.get("label", cid)

        _clue_field_labels = {
            "payoff": (
                "non ha un payoff narrativo: il Master non sa cosa cambia quando i giocatori lo trovano",
                "Aggiungi 'payoff': descrivi cosa sblocca o rivela narrativamente questo indizio quando viene scoperto"
            ),
            "hidden_implication": (
                "non ha un'implicazione nascosta: è un indizio a una dimensione senza profondità",
                "Aggiungi 'hidden_implication': il significato segreto che emerge solo se i PG mettono insieme più pezzi"
            ),
            "wrong_interpretations": (
                "non ha false interpretazioni: non permette ai giocatori di sbagliarsi e imparare",
                "Aggiungi 'wrong_interpretations': 1-2 letture plausibili ma errate che rendono il mistero più ricco"
            ),
        }
        for fld in ("payoff", "hidden_implication", "wrong_interpretations"):
            if not cl.get(fld):
                issue, fix = _clue_field_labels[fld]
                findings.append(Finding("suggestion", "clue", cid,
                    f"L'indizio '{label}' {issue}", fix))

        # thread_id esistente
        tid = str(cl.get("thread_id") or "").strip()
        if tid and thread_ids and tid not in thread_ids:
            findings.append(Finding("warning", "clue", cid,
                f"Indizio '{label}': thread_id '{tid}' non corrisponde a nessun thread",
                "Correggi thread_id o crea il thread mancante"))

    return findings


def _thread_rules(threads: List[Dict], clue_ids: Set[str],
                  actors: List[Dict] = None, locations: List[Dict] = None,
                  clues: List[Dict] = None, revelations: List[Dict] = None) -> List[Finding]:
    findings = []
    all_thread_ids = _ids(threads)

    # ── Phantom thread references: ID citati da clue/revelation ma mai definiti in story_threads
    # Sono il motivo principale per cui il grafo mostra "piste vuote scollegate" senza che il
    # tab Piste le mostri.
    phantom_ids = set()
    phantom_sources: Dict[str, List[str]] = {}  # id → ["clue:c_3", "rev:r_1"]
    for cl in (clues or []):
        tid = str(cl.get("thread_id") or "").strip()
        if tid and tid not in all_thread_ids:
            phantom_ids.add(tid)
            phantom_sources.setdefault(tid, []).append(f"clue:{cl.get('id', '?')}")
    for rv in (revelations or []):
        tid = str(rv.get("thread_id") or "").strip()
        if tid and tid not in all_thread_ids:
            phantom_ids.add(tid)
            phantom_sources.setdefault(tid, []).append(f"revelation:{rv.get('id', '?')}")
    for pid in sorted(phantom_ids):
        sources = ", ".join(phantom_sources.get(pid, []))
        findings.append(Finding("warning", "thread", pid,
            f"Pista fantasma '{pid}': citata da {sources} ma non definita in story_threads — "
            f"appare scollegata nel grafo, il narratore non sa come risolverla",
            f"Crea uno stub di story_threads con id='{pid}', oppure rimuovi il riferimento da {sources}"))

    # Build lookup sets for actor names and location names (lower-case)
    _actors = actors or []
    _locations = locations or []
    actor_names_lower: List[str] = [
        str(a.get("name") or a.get("id") or "").lower()
        for a in _actors if a.get("name") or a.get("id")
    ]
    location_names_lower: List[str] = [
        str(loc.get("name") or loc.get("id") or "").lower()
        for loc in _locations if loc.get("name") or loc.get("id")
    ]
    known_sources_lower: List[str] = actor_names_lower + location_names_lower

    # ── Check 1: at least 2 root threads ──────────────────────────────────────
    root_threads = [
        t for t in threads
        if not t.get("parent_thread_ids")
    ]
    if threads and len(root_threads) < 2:
        findings.append(Finding("warning", "thread", "adventure",
            f"Meno di 2 piste radice (root thread): con una sola pista immediatamente accessibile "
            f"i giocatori rischiano di bloccarsi se non trovano il primo indizio",
            "Imposta parent_thread_ids a [] o rimuovilo da almeno un altro thread in modo da avere "
            "2+ piste percorribili fin dall'inizio"))

    # Cicli
    cycles = _detect_thread_cycles(threads)
    for tid in cycles:
        findings.append(Finding("warning", "thread", tid,
            f"Thread '{tid}': ciclo rilevato in parent_thread_ids",
            "Rimuovi la dipendenza circolare"))

    for t in threads:
        tid = t.get("id", "?")
        label = t.get("title") or t.get("question") or tid

        # parent inesistenti
        for pid in (t.get("parent_thread_ids") or []):
            if pid and pid not in all_thread_ids:
                findings.append(Finding("warning", "thread", tid,
                    f"Thread '{label}': parent '{pid}' non esiste",
                    "Rimuovi il parent o crea il thread mancante"))

        # nessuna clue associata
        collected = set(t.get("collected_clue_ids") or []) | set(t.get("clue_plan") or [])
        if not collected and not t.get("partial_clues"):
            findings.append(Finding("suggestion", "thread", tid,
                f"La pista '{label}' non ha indizi collegati: i giocatori non hanno modo di progredire su questa domanda",
                "Collega almeno 1 clue a questa pista tramite thread_id o clue_plan"))

        # risposta canonica mancante
        if not t.get("true_answer") and not t.get("answer"):
            findings.append(Finding("suggestion", "thread", tid,
                f"La pista '{label}' non ha una risposta canonica: il Master non sa qual è la verità",
                "Aggiungi 'true_answer': la risposta corretta che il Master conosce ma che i giocatori devono scoprire"))

        # ── Check 2: clue source specificity ──────────────────────────────────
        clue_plan_entries: List[str] = [
            str(c) for c in (t.get("clue_plan") or [])
            if isinstance(c, str)
        ]
        if clue_plan_entries and known_sources_lower:
            vague_clues: List[str] = []
            for clue_text in clue_plan_entries:
                clue_lower = clue_text.lower()
                has_source = any(src and src in clue_lower for src in known_sources_lower)
                if not has_source:
                    vague_clues.append(clue_text)
            if vague_clues:
                sev = "info" if len(vague_clues) == 1 else "warning"
                findings.append(Finding(sev, "thread", tid,
                    f"La pista '{label}': clue_plan contiene indizi senza source specifico "
                    f"(luogo/PNG non identificato)",
                    "Riformula ogni indizio con '(in LUOGO / con NPC)' per guidare il narratore"))

        # ── Check 3: linked_npcs completeness ─────────────────────────────────
        linked_npcs = t.get("linked_npcs") or []
        if not linked_npcs and clue_plan_entries and actor_names_lower:
            clue_plan_text = " ".join(clue_plan_entries).lower()
            mentions_actor = any(
                name and name in clue_plan_text
                for name in actor_names_lower
            )
            if mentions_actor:
                findings.append(Finding("info", "thread", tid,
                    f"La pista '{label}': linked_npcs vuoto ma clue_plan cita PNG — "
                    f"il narratore potrebbe non associare correttamente gli indizi",
                    "Popola linked_npcs con gli ID degli attori citati in clue_plan"))

        # ── Check 4: clue diversity ────────────────────────────────────────────
        required_clues = t.get("required_clues") or 0
        if (isinstance(required_clues, int) and required_clues >= 2
                and len(clue_plan_entries) >= 2
                and known_sources_lower):
            # Find which sources are mentioned in each clue entry
            clue_sources: List[Set[str]] = []
            for clue_text in clue_plan_entries:
                clue_lower = clue_text.lower()
                sources_in_clue = {
                    src for src in known_sources_lower
                    if src and src in clue_lower
                }
                clue_sources.append(sources_in_clue)

            # All clues mention sources AND all mention exactly the same single source
            non_empty = [s for s in clue_sources if s]
            if (len(non_empty) == len(clue_plan_entries)
                    and len(non_empty) >= 2
                    and len(set.union(*non_empty)) == 1):
                findings.append(Finding("info", "thread", tid,
                    f"La pista '{label}': tutti gli indizi citano la stessa fonte — "
                    f"diversifica i source per rendere l'investigazione più ricca",
                    "Distribuisci gli indizi tra più location o PNG diversi"))

    return findings


def _location_rules(locations: List[Dict], actor_ids_by_loc: Dict[str, List],
                    clue_ids_by_loc: Dict[str, List]) -> List[Finding]:
    findings = []
    for loc in locations:
        lid = loc.get("id", "?")
        name = loc.get("name", lid)

        # Location completamente vuota
        has_actors = bool(actor_ids_by_loc.get(lid))
        has_clues  = bool(clue_ids_by_loc.get(lid))
        has_loot   = bool(loc.get("contains_loot") or loc.get("loot"))
        has_desc   = bool(loc.get("description") or loc.get("scene_description"))
        has_enemy  = bool(loc.get("contains_actors") or loc.get("has_combat_potential"))
        tmap       = loc.get("tactical_map") or {}
        has_tmap   = bool(tmap.get("enabled") or tmap)

        if not has_actors and not has_clues and not has_desc and not has_enemy:
            findings.append(Finding("suggestion", "location", lid,
                f"La location '{name}' è completamente vuota: i giocatori non hanno motivo di visitarla",
                "Aggiungi una descrizione, un PNG o almeno un indizio che rende la location rilevante"))

        # Zona calda senza tactical_map
        if loc.get("has_combat_potential") or loc.get("contains_actors"):
            if not has_tmap:
                findings.append(Finding("suggestion", "location", lid,
                    f"'{name}' può avere combattimento ma manca la mappa tattica: il Master non ha informazioni per gestire gli scontri",
                    "Aggiungi tactical_map con enabled:true, layout e features per supportare il combattimento"))
            elif has_tmap:
                # tactical_map presente ma incompleta
                if not tmap.get("features"):
                    findings.append(Finding("suggestion", "location", lid,
                        f"'{name}': la mappa tattica non ha elementi di copertura o interazione",
                        "Aggiungi features: ['copertura', 'ostacolo', 'tavolo rovesciabile', ...]"))
                if not tmap.get("hazards"):
                    findings.append(Finding("suggestion", "location", lid,
                        f"'{name}': la mappa tattica non ha rischi ambientali",
                        "Aggiungi hazards: ['terreno difficile', 'fuoco', 'buio', ...] per rendere il combattimento più interessante"))
                if not tmap.get("layout"):
                    findings.append(Finding("suggestion", "location", lid,
                        f"'{name}': la mappa tattica non ha un layout definito",
                        "Specifica layout: 'room' | 'narrow' | 'open' per aiutare il Master a descrivere lo spazio"))

        # contains_loot ma nessun item definito
        if loc.get("contains_loot") and not loc.get("loot") and not loc.get("items"):
            findings.append(Finding("suggestion", "location", lid,
                f"'{name}' dichiara di contenere loot ma non ha item definiti: i giocatori non troveranno nulla di concreto",
                "Aggiungi items: [...] alla location oppure rimuovi contains_loot se non è rilevante"))

    # Gerarchia: rileva location "orfane" che logicamente appartengono a un'altra
    loc_names = {l.get("id", ""): l.get("name", "") for l in locations}
    has_any_parent = any(l.get("parent_location_id") for l in locations)
    orphans_found = []
    for loc in locations:
        if loc.get("parent_location_id"):
            continue  # già ha un parent
        lid = loc.get("id", "?")
        name = loc.get("name", lid)
        name_lower = name.lower()
        for other_id, other_name in loc_names.items():
            if other_id == lid:
                continue
            # Se il nome di questa location contiene il nome di un'altra → probabile figlio
            other_lower = other_name.lower()
            if len(other_lower) > 3 and other_lower in name_lower and other_id != lid:
                orphans_found.append(lid)
                findings.append(Finding("warning", "location", lid,
                    f"'{name}' sembra trovarsi dentro '{other_name}' ma non ha parent_location_id impostato",
                    f"Imposta parent_location_id: \"{other_id}\" per inserirla nella gerarchia della mappa"))
                break

    # Se ci sono molte location senza alcuna gerarchia, suggerisci di organizzarle
    if len(locations) >= 5 and not has_any_parent:
        findings.append(Finding("suggestion", "location", "hierarchy",
            f"L'avventura ha {len(locations)} location ma nessuna ha parent_location_id: la mappa di gioco le mostrerà tutte piatte",
            "Usa il Doctor (Migliora) per organizzarle automaticamente in aree principali e sub-zone, "
            "oppure imposta parent_location_id nell'editor per ogni sotto-location"))

    return findings


def _balance_rules(data: Dict) -> List[Finding]:
    """Rileva squilibri strutturali tra indizi (clues) e piste (story_threads).

    Problemi tipici dei PDF:
    - Troppe objectives, nessun story_thread investigativo
    - Clues senza thread_id valido (orfani)
    - Threads senza clue collegate (piste vuote)
    - Meno di 2 clue per thread (il giocatore non può dedurre)
    """
    findings = []
    threads = data.get("story_threads") or []
    clues = data.get("clues") or []
    objectives = data.get("objectives") or []
    title = data.get("title", data.get("id", "?"))

    thread_ids = {str(t.get("id", "")) for t in threads if t.get("id")}

    # Clue → thread mapping
    clues_per_thread: Dict[str, List[str]] = {tid: [] for tid in thread_ids}
    orphan_clue_ids: List[str] = []
    for cl in clues:
        tid = str(cl.get("thread_id") or "").strip()
        cid = str(cl.get("id") or cl.get("label") or "?")
        if tid and tid in thread_ids:
            clues_per_thread[tid].append(cid)
        else:
            orphan_clue_ids.append(cid)

    # [BALANCE-1] Nessun thread investigativo ma ci sono obiettivi
    if not threads and objectives:
        findings.append(Finding("warning", "balance", title,
            f"Nessuna pista investigativa (story_threads): l'avventura ha {len(objectives)} obiettivi "
            "ma i giocatori non hanno domande da investigare — la narrativa diventa lineare",
            "Converti almeno 2 obiettivi in piste investigative con domanda e risposta nascosta"))

    # [BALANCE-2] Troppo pochi thread (< 2)
    elif len(threads) < 2 and clues:
        findings.append(Finding("warning", "balance", title,
            f"Solo {len(threads)} pista investigativa con {len(clues)} indizi: "
            "se i giocatori falliscono il primo indizio si bloccano",
            "Aggiungi almeno una seconda pista radice percorribile indipendentemente"))

    # [BALANCE-3] Clue orfani (senza thread_id valido)
    if orphan_clue_ids:
        findings.append(Finding("warning", "balance", "orphan_clues",
            f"{len(orphan_clue_ids)} indizi senza pista assegnata: "
            f"{', '.join(orphan_clue_ids[:5])}{'...' if len(orphan_clue_ids) > 5 else ''} — "
            "il motore narrativo non sa come usarli",
            "Assegna un thread_id valido a ogni indizio, o crea una nuova pista che li raccolga"))

    # [BALANCE-4] Thread con meno di 2 clue (il giocatore non può dedurre)
    for tid, clist in clues_per_thread.items():
        t = next((t for t in threads if t.get("id") == tid), {})
        label = t.get("title") or t.get("question") or tid
        if len(clist) < 2:
            findings.append(Finding("warning", "balance", tid,
                f"La pista '{label}' ha solo {len(clist)} indizi: "
                "GURPS richiede almeno 2 prove per una deduzione credibile",
                f"Aggiungi almeno 1 indizio con thread_id='{tid}'"))

    # [BALANCE-5] Rapporto clue/thread troppo sbilanciato
    if threads and clues:
        avg = len(clues) / len(threads)
        if avg < 1.5:
            findings.append(Finding("suggestion", "balance", title,
                f"Media di {avg:.1f} indizi per pista: troppo pochi per permettere deduzioni — "
                "i giocatori troveranno la soluzione per esclusione, non per ragionamento",
                "Obiettivo: almeno 2-3 indizi per pista, con tipi diversi (fisico, testimonianza, documento)"))

    return findings


def _resource_rules(resources: list, genre: str, title: str) -> List[Finding]:
    if not resources:
        horror = ("horror", "cosmic", "thriller", "survival", "western")
        sev = "warning" if any(h in genre.lower() for h in horror) else "suggestion"
        if sev == "warning":
            msg = "Nessuna risorsa limitata definita: per un genere horror/survival le risorse (sanità, munizioni, luce) sono fondamentali"
        else:
            msg = "Nessuna risorsa narrativa definita: aggiungere risorse limitate (tempo, morale, forniture) rende le scelte dei giocatori più significative"
        return [Finding(sev, "resource", title,
            msg,
            "Considera risorse narrative come sanità mentale, munizioni, tempo, morale")]
    return []


def _equipment_rules(data: Dict) -> List[Finding]:
    """Regole specifiche per il sistema equipaggiamento/inventario."""
    findings = []
    genre = str(data.get("genre", "")).lower()
    title = data.get("title", data.get("id", "?"))

    # Import lazy per evitare dipendenze circolari all'avvio
    try:
        from .data_weapons import WEAPON_BY_ID, item_to_weapon_id, GENRE_ERA_MAP, ERA_MODERN
        from .data_items import ITEM_CATALOG, _ALIAS_TO_ITEM_ID
        from .data_skills import VALID_SKILLS
        weapon_check_available = True
        valid_eras = set(GENRE_ERA_MAP.get(genre, [ERA_MODERN])) if genre else set()
    except Exception:
        weapon_check_available = False
        WEAPON_BY_ID = {}
        item_to_weapon_id = lambda x: None
        ITEM_CATALOG = {}
        _ALIAS_TO_ITEM_ID = {}
        VALID_SKILLS = set()
        valid_eras = set()

    # Raccoglie tutti i key_items / quest_items definiti nelle location
    loc_items: List[Dict] = []
    key_item_names: Set[str] = set()
    for loc in data.get("locations", []):
        for itm in (loc.get("items") or loc.get("loot") or []):
            if isinstance(itm, dict):
                loc_items.append(itm)
                if itm.get("category") in ("key_item", "quest_item"):
                    key_item_names.add(str(itm.get("name", "")).lower())
            elif isinstance(itm, str):
                key_item_names.add(itm.lower())

    # Raccoglie riferimenti agli item dai clue e thread
    referenced_items: Set[str] = set()
    for cl in data.get("clues", []):
        for fld in ("label", "payoff", "hidden_implication", "reveals"):
            txt = str(cl.get(fld) or "").lower()
            referenced_items.update(txt.split())
    for t in data.get("story_threads", []):
        for fld in ("question", "true_answer", "answer", "payoff"):
            txt = str(t.get(fld) or "").lower()
            referenced_items.update(txt.split())
    # Anche key_items della StoryState se presente
    for ki in data.get("key_items", []):
        if isinstance(ki, dict):
            key_item_names.add(str(ki.get("name", "")).lower())

    # ── Controlli NPC equipaggiamento ─────────────────────────────────────────
    for actor in data.get("actors", []):
        aid = actor.get("id", "?")
        name = actor.get("name", aid)
        threat = int(actor.get("threat_to_player") or actor.get("agenda_pressure") or 0)
        items = actor.get("items") or []
        role = str(actor.get("role") or "").lower()

        # NPC combattente (antagonista o threat alto) senza nessuna arma
        is_combatant = role in ("villain", "antagonist", "enemy") or threat >= 2
        if is_combatant and weapon_check_available:
            has_weapon = False
            for item_name in items:
                if item_to_weapon_id(str(item_name)):
                    has_weapon = True
                    break
            # Controlla anche actions se presenti
            if actor.get("actions"):
                has_weapon = True
            if not has_weapon and not items:
                findings.append(Finding("warning", "equipment", aid,
                    f"NPC '{name}' (antagonista/minaccia) senza armi né items",
                    "Aggiungi items: ['pistola', 'coltello', ...] o actions"))

        # Item dell'NPC non riconoscibili dal sistema
        if weapon_check_available:
            for item_name in items:
                item_str = str(item_name)
                wid = item_to_weapon_id(item_str)
                # Controlla anche nel catalogo oggetti
                in_catalog = item_str.lower() in _ALIAS_TO_ITEM_ID or item_str.lower() in ITEM_CATALOG
                if not wid and not in_catalog and len(item_str) > 3:
                    findings.append(Finding("suggestion", "equipment", aid,
                        f"L'oggetto '{item_str}' di '{name}' non è nel catalogo del sistema: le statistiche potrebbero non essere calcolate correttamente",
                        "Verifica il nome dell'oggetto o aggiungilo a data_items.py / data_weapons.py"))

    # ── Controlli item nelle location ─────────────────────────────────────────
    for itm in loc_items:
        iid = itm.get("id") or itm.get("name") or "?"
        iname = itm.get("name", iid)

        # skill_bonuses con skill sconosciute
        if weapon_check_available:
            for skill_name, bonus in (itm.get("skill_bonuses") or {}).items():
                if skill_name not in VALID_SKILLS:
                    findings.append(Finding("suggestion", "equipment", str(iid),
                        f"L'item '{iname}' dà un bonus a una skill sconosciuta ('{skill_name}'): il bonus potrebbe non essere applicato",
                        f"Usa nomi di skill riconosciute: ricerca, investigare, percezione, furtivita, ..."))

            # weapon_id esistente
            wid = itm.get("weapon_id") or ""
            if wid and wid not in WEAPON_BY_ID:
                findings.append(Finding("warning", "equipment", str(iid),
                    f"Item '{iname}': weapon_id '{wid}' non esiste in WEAPON_TABLE",
                    "Controlla l'id con data_weapons.py WEAPON_BY_ID"))

    # ── key_item/quest_item non referenziati in nessun thread né clue ─────────
    for item_name in key_item_names:
        # Cerca se il nome appare in qualche thread o clue
        found_ref = any(
            item_name in str(cl.get("label") or cl.get("payoff") or "").lower()
            for cl in data.get("clues", [])
        ) or any(
            item_name in str(t.get("question") or t.get("payoff") or "").lower()
            for t in data.get("story_threads", [])
        ) or any(
            item_name in str(ki.get("uso") or ki.get("use") or "").lower()
            for ki in data.get("key_items", [])
            if isinstance(ki, dict)
        )
        if not found_ref and len(item_name) > 3:
            findings.append(Finding("suggestion", "equipment", item_name,
                f"L'oggetto chiave '{item_name}' non è menzionato in nessun indizio né pista: i giocatori potrebbero non sapere che esiste",
                "Collega l'oggetto a un thread o clue che ne giustifichi il ritrovamento"))

    # ── Items negli aventura-level key_items ──────────────────────────────────
    for ki in data.get("key_items", []):
        if not isinstance(ki, dict):
            continue
        kiname = ki.get("name") or ki.get("id") or "?"
        if not ki.get("dove") and not ki.get("location") and not ki.get("where"):
            findings.append(Finding("suggestion", "equipment", str(kiname),
                f"L'oggetto importante '{kiname}' non ha una posizione: il Master non sa dove collocarlo nella fiction",
                "Aggiungi 'dove': 'nome_location' per indicare dove i giocatori possono trovare l'oggetto"))

    return findings


def _build_location_indexes(data: Dict):
    """Costruisce gli indici location→actors e location→clues."""
    actor_by_loc: Dict[str, List[str]] = {}
    for actor in data.get("actors", []):
        loc = str(actor.get("location_id") or "").strip()
        if loc:
            actor_by_loc.setdefault(loc, []).append(actor.get("id", "?"))

    clue_by_loc: Dict[str, List[str]] = {}
    for cl in data.get("clues", []):
        loc = str(cl.get("source_location") or cl.get("location_id") or "").strip()
        if loc:
            clue_by_loc.setdefault(loc, []).append(cl.get("id", "?"))

    return actor_by_loc, clue_by_loc


def audit(data: Dict) -> List[Finding]:
    """Esegue tutti i controlli e restituisce la lista di Finding."""
    location_ids = _ids(data.get("locations", []))
    clue_ids     = _ids(data.get("clues", []))
    thread_ids   = _ids(data.get("story_threads", []))
    actor_by_loc, clue_by_loc = _build_location_indexes(data)

    findings: List[Finding] = []
    findings.extend(_structure_rules(data))
    findings.extend(_npc_rules(data.get("actors", []), location_ids))
    findings.extend(_clock_rules(data.get("event_clocks", [])))
    findings.extend(_clue_rules(data.get("clues", []), thread_ids))
    findings.extend(_thread_rules(
        data.get("story_threads", []),
        clue_ids,
        actors=data.get("actors", []),
        locations=data.get("locations", []),
        clues=data.get("clues", []),
        revelations=data.get("revelations", []),
    ))
    findings.extend(_location_rules(data.get("locations", []), actor_by_loc, clue_by_loc))
    findings.extend(_resource_rules(
        data.get("resources", []),
        data.get("genre", ""),
        data.get("title", data.get("id", "?")),
    ))
    findings.extend(_equipment_rules(data))
    findings.extend(_balance_rules(data))
    return findings


def score(findings: List[Finding]) -> float:
    _weights = {"error": 1.5, "warning": 0.5, "suggestion": 0.1,
                # Legacy aliases kept for backward compatibility
                "critical": 1.5, "info": 0.1}
    penalty = sum(_weights.get(f.severity, 0.1) for f in findings)
    return max(0.0, round(10.0 - penalty, 1))


# ─── Enrichment helpers ───────────────────────────────────────────────────────

def _json_from_llm(raw: str) -> Any:
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _enrich_structure_balance(enriched: Dict, findings: List[Finding]) -> Dict:
    """Genera clue e/o story_thread mancanti per bilanciare la struttura investigativa."""
    balance_issues = [f for f in findings if f.category == "balance"]
    if not balance_issues:
        return enriched

    title = enriched.get("title", "")
    genre = enriched.get("genre", "")
    premise = (enriched.get("premise") or "")[:300]
    hidden_truth = (enriched.get("hidden_truth") or enriched.get("core_truths") or "")
    if isinstance(hidden_truth, list):
        hidden_truth = "; ".join(str(h.get("statement", h) if isinstance(h, dict) else h) for h in hidden_truth[:2])

    threads = enriched.get("story_threads") or []
    clues = enriched.get("clues") or []
    actors = enriched.get("actors") or []
    locations = enriched.get("locations") or []

    thread_ids = {str(t.get("id", "")) for t in threads if t.get("id")}
    clues_per_thread: Dict[str, int] = {tid: 0 for tid in thread_ids}
    for cl in clues:
        tid = str(cl.get("thread_id") or "").strip()
        if tid in clues_per_thread:
            clues_per_thread[tid] += 1

    # Determina cosa manca
    needs_new_threads = len(threads) < 2
    threads_needing_clues = [tid for tid, cnt in clues_per_thread.items() if cnt < 2]
    has_orphan_clues = any(
        not str(cl.get("thread_id") or "").strip() or str(cl.get("thread_id") or "").strip() not in thread_ids
        for cl in clues
    )

    actor_summary = ", ".join(
        f"{a.get('name', '?')} ({a.get('role', '?')})" for a in actors[:5]
    )
    loc_summary = ", ".join(
        l.get("name", "?") for l in locations[:6] if not l.get("parent_location_id")
    )
    thread_summary = "\n".join(
        f"  - id={t.get('id')} titolo='{t.get('title') or t.get('question', '')}' "
        f"clues_attuali={clues_per_thread.get(t.get('id', ''), 0)}"
        for t in threads
    ) or "  (nessuna pista definita)"
    clue_summary = "\n".join(
        f"  - id={c.get('id')} label='{c.get('label', '')}' thread_id='{c.get('thread_id', '')}'"
        for c in clues[:10]
    ) or "  (nessun indizio)"

    task_lines = []
    if needs_new_threads:
        task_lines.append(
            "1. Crea 2-3 nuove piste investigative (story_threads) con domanda investigativa "
            "e risposta nascosta (true_answer). Ogni pista deve coprire un aspetto diverso della trama."
        )
    if threads_needing_clues or has_orphan_clues:
        task_lines.append(
            f"2. Genera indizi mancanti: ogni pista deve avere almeno 2 clue con thread_id valido. "
            f"Piste che ne hanno bisogno: {', '.join(threads_needing_clues) or 'tutte'}. "
            "Usa NPC e luoghi reali dell'avventura come fonte degli indizi."
        )
    if not task_lines:
        return enriched

    prompt = f"""Sei un game designer GURPS. Analizza questa avventura e completa la struttura investigativa.

AVVENTURA: {title}
GENERE: {genre}
PREMESSA: {premise}
VERITÀ NASCOSTA: {hidden_truth}
NPC: {actor_summary}
LOCATION ROOT: {loc_summary}

PISTE ATTUALI:
{thread_summary}

INDIZI ATTUALI:
{clue_summary}

COMPITO:
{chr(10).join(task_lines)}

Rispondi SOLO con questo JSON (non aggiungere altro testo):
{{
  "new_threads": [
    {{
      "id": "T_nuovo_1",
      "title": "Titolo pista",
      "question": "Domanda investigativa concreta",
      "true_answer": "Risposta canonica nascosta",
      "status": "hidden",
      "required_clues": ["nuovo_clue_1", "nuovo_clue_2"],
      "minimum_clues_to_deduce": 2,
      "parent_thread_ids": [],
      "linked_npcs": [],
      "linked_locations": []
    }}
  ],
  "new_clues": [
    {{
      "id": "nuovo_clue_1",
      "label": "Nome breve indizio",
      "text": "Descrizione concreta di cosa è l'indizio",
      "type": "physical_evidence | testimony | document | behavior | location_detail",
      "thread_id": "id_pista_esistente_o_nuova",
      "reveals": "Cosa suggerisce",
      "payoff": "Cosa permette di capire o sbloccare",
      "location": "Dove si trova / come si ottiene",
      "found": false
    }}
  ],
  "clue_thread_fixes": [
    {{"clue_id": "id_indizio_orfano", "thread_id": "id_pista_da_assegnare"}}
  ]
}}

REGOLE:
- new_threads: [] se non servono nuove piste
- new_clues: almeno 2 per ogni pista che ne ha meno di 2
- clue_thread_fixes: assegna thread_id agli indizi orfani
- Usa nomi di NPC e luoghi già esistenti nell'avventura come fonte degli indizi
- Ogni indizio deve essere fisicamente trovabile o dedotto da una situazione concreta"""

    try:
        raw = _llm(prompt, max_tokens=2048)
        result = _json_from_llm(raw)
    except Exception as e:
        print(f"[doctor] balance enrichment failed: {e}", file=sys.stderr)
        return enriched

    # Apply new_threads
    new_threads = result.get("new_threads") or []
    if new_threads:
        existing_ids = {str(t.get("id", "")) for t in (enriched.get("story_threads") or [])}
        added = [t for t in new_threads if str(t.get("id", "")) not in existing_ids]
        enriched["story_threads"] = list(enriched.get("story_threads") or []) + added
        print(f"[doctor] balance: added {len(added)} new thread(s)")

    # Apply new_clues
    new_clues = result.get("new_clues") or []
    if new_clues:
        existing_cids = {str(c.get("id", "")) for c in (enriched.get("clues") or [])}
        added_clues = [c for c in new_clues if str(c.get("id", "")) not in existing_cids]
        enriched["clues"] = list(enriched.get("clues") or []) + added_clues
        print(f"[doctor] balance: added {len(added_clues)} new clue(s)")

    # Apply clue_thread_fixes (assign thread_id to orphan clues)
    fixes = result.get("clue_thread_fixes") or []
    if fixes:
        fix_map = {str(f.get("clue_id", "")): str(f.get("thread_id", "")) for f in fixes if f.get("clue_id") and f.get("thread_id")}
        updated = []
        for cl in (enriched.get("clues") or []):
            cid = str(cl.get("id", ""))
            if cid in fix_map:
                cl = dict(cl)
                cl["thread_id"] = fix_map[cid]
            updated.append(cl)
        enriched["clues"] = updated
        print(f"[doctor] balance: fixed thread_id for {len(fix_map)} orphan clue(s)")

    return enriched


def _enrich_initial_hook(data: Dict) -> str:
    title   = data.get("title", "")
    genre   = data.get("genre", "")
    premise = (data.get("premise") or "")[:300]
    tone    = data.get("tone", "")
    actors  = [a.get("name", "") for a in data.get("actors", [])[:3]]
    actor_names = ", ".join(a for a in actors if a)

    prompt = (
        f"Avventura GURPS: {title}\nGenere: {genre} — Tono: {tone}\n"
        f"Premessa: {premise}\nNPC principali: {actor_names}\n\n"
        "Scrivi l'initial_hook: la scena di apertura con cui il GM introduce l'avventura. "
        "Deve essere concreto, coinvolgente, 3-4 frasi: dove si trovano i PG, cosa vedono/sentono, "
        "quale evento o NPC li trascina nell'avventura.\n"
        "Rispondi SOLO con una stringa JSON (tra doppie virgolette), senza markdown."
    )
    try:
        raw = _llm(prompt, max_tokens=512).strip()
        return json.loads(raw) if raw.startswith('"') else raw.strip('"')
    except Exception as e:
        print(f"[doctor] initial_hook failed: {e}", file=sys.stderr)
        return ""


def _enrich_npc(actor: Dict, context: str) -> Dict:
    name = actor.get("name", actor.get("id"))
    prompt = (
        f"Avventura: {context}\n\nNPC: {name} — ruolo: {actor.get('role')} "
        f"— obiettivo: {actor.get('goal')} — segreto: {actor.get('secret')}\n\n"
        "Genera SOLO questo JSON (non altri campi):\n"
        '{"pressure_response": {"low": "...", "medium": "...", "high": "...", "extreme": "..."},'
        '"reaction_table": {"se_minacciato": "...", "se_corrotto": "...", "se_i_pg_hanno_prove": "...", "se_alleato": "..."},'
        '"current_plan": "...", "fallback_plan": "..."}\n'
        "Sii specifico al personaggio. Niente testo generico."
    )
    try:
        enrichment = _json_from_llm(_llm(prompt, max_tokens=1024))
        return {**actor, **enrichment, "llm_enriched": True}
    except Exception as e:
        print(f"[doctor] NPC '{name}' enrichment failed: {e}", file=sys.stderr)
        return actor


def _enrich_clocks(clocks: List[Dict], context: str) -> List[Dict]:
    if not clocks:
        return clocks
    prompt = (
        f"Avventura: {context}\n\nClock da migliorare:\n"
        f"{json.dumps(clocks, ensure_ascii=False, indent=2)}\n\n"
        "Per ogni clock aggiungi:\n"
        "- steps: [{\"value\": N, \"label\": \"...\", \"effect\": \"...\"}] con almeno 4 step progressivi\n"
        "- resolution_condition: come i giocatori fermano il clock\n"
        "- discovery_hint: presagio narrativo ambiguo\n"
        "- ticks_per_failure: 2\n\n"
        "Non modificare id, label, max_value, clock_type.\n"
        "Restituisci SOLO la lista JSON aggiornata."
    )
    try:
        enriched = _json_from_llm(_llm(prompt, max_tokens=2048))
        if isinstance(enriched, list) and len(enriched) == len(clocks):
            return enriched
    except Exception as e:
        print(f"[doctor] clock enrichment failed: {e}", file=sys.stderr)
    return clocks


def _enrich_clues(clues: List[Dict], context: str) -> List[Dict]:
    needs = [c for c in clues if not c.get("payoff") or not c.get("hidden_implication")
             or not c.get("wrong_interpretations")]
    if not needs:
        return clues
    prompt = (
        f"Avventura: {context}\n\nIndizi da completare:\n"
        f"{json.dumps(needs, ensure_ascii=False, indent=2)}\n\n"
        "Per ogni indizio aggiungi i campi mancanti:\n"
        "- payoff: stringa (cosa rivela)\n"
        "- hidden_implication: stringa (significato nascosto)\n"
        "- wrong_interpretations: lista di 1-2 false interpretazioni\n\n"
        "Restituisci SOLO la lista JSON degli stessi indizi con i campi aggiunti."
    )
    try:
        enriched_list = _json_from_llm(_llm(prompt, max_tokens=2048))
        enriched_map = {c["id"]: c for c in enriched_list if "id" in c}
        return [enriched_map.get(c.get("id"), c) for c in clues]
    except Exception as e:
        print(f"[doctor] clue enrichment failed: {e}", file=sys.stderr)
        return clues


def _enrich_location_hierarchy(locations: List[Dict], context: str) -> List[Dict]:
    """Chiede all'AI di organizzare le location in una gerarchia a 2 livelli con parent_location_id."""
    if not locations:
        return locations
    loc_list = [{"id": l.get("id"), "name": l.get("name"), "description": (l.get("description") or "")[:80]} for l in locations]
    prompt = (
        f"Avventura: {context}\n\n"
        f"Location attuali:\n{json.dumps(loc_list, ensure_ascii=False, indent=2)}\n\n"
        "Organizza queste location in una gerarchia a 2 livelli:\n"
        "- Livello 0 (aree macroscopiche): 2-3 location con parent_location_id: \"\"\n"
        "- Livello 1 (sub-zone): le restanti, ciascuna con parent_location_id = id dell'area padre logica\n\n"
        "Se necessario puoi rinominare o accorpare location molto simili.\n"
        "Restituisci SOLO una lista JSON con TUTTI gli id originali, aggiungendo parent_location_id a ciascuno.\n"
        "Formato: [{\"id\": \"...\", \"parent_location_id\": \"\"}, ...]\n"
        "Non aggiungere altri campi."
    )
    try:
        result = _json_from_llm(_llm(prompt, max_tokens=800))
        if isinstance(result, list):
            parent_map = {item["id"]: item.get("parent_location_id", "") for item in result if "id" in item}
            updated = []
            for loc in locations:
                lid = loc.get("id")
                if lid in parent_map:
                    updated.append({**loc, "parent_location_id": parent_map[lid]})
                else:
                    updated.append(loc)
            return updated
    except Exception as e:
        print(f"[doctor] location hierarchy enrichment failed: {e}", file=sys.stderr)
    return locations


def _enrich_locations(locations: List[Dict], context: str) -> List[Dict]:
    """Arricchisce location vuote con description e tactical_map di base."""
    needs = [
        loc for loc in locations
        if not loc.get("description") and not loc.get("scene_description")
    ]
    if not needs:
        return locations
    prompt = (
        f"Avventura: {context}\n\nLocation da completare:\n"
        f"{json.dumps(needs, ensure_ascii=False, indent=2)}\n\n"
        "Per ogni location aggiungi:\n"
        "- description: 1-2 frasi che descrivono l'ambiente in modo evocativo e giocabile\n\n"
        "Non modificare id, name né altri campi.\n"
        "Restituisci SOLO la lista JSON aggiornata."
    )
    try:
        enriched_list = _json_from_llm(_llm(prompt, max_tokens=1024))
        if isinstance(enriched_list, list):
            enriched_map = {loc.get("id"): loc for loc in enriched_list if loc.get("id")}
            return [enriched_map.get(loc.get("id"), loc) for loc in locations]
    except Exception as e:
        print(f"[doctor] location enrichment failed: {e}", file=sys.stderr)
    return locations


# ─── Public API ───────────────────────────────────────────────────────────────

def _estimate_session_length(definition: Dict) -> str:
    """
    Estimate session length based on adventure complexity.

    Formula:
      base = 30 min
      + n_clues × 10 min
      + sum(clock max_value) × 5 min
      + n_npcs × 5 min
    """
    n_clues = len(definition.get("clues") or [])
    n_npcs = len(definition.get("actors") or [])
    clocks = definition.get("event_clocks") or []
    n_clock_segments = sum(
        int(c.get("max_value") or c.get("max") or 0) for c in clocks if isinstance(c, dict)
    )

    total_minutes = 30 + (n_clues * 10) + (n_clock_segments * 5) + (n_npcs * 5)

    if total_minutes < 90:
        return "1-2 ore"
    elif total_minutes < 150:
        return "2-3 ore"
    elif total_minutes < 210:
        return "3-4 ore"
    elif total_minutes < 270:
        return "4-5 ore"
    else:
        return "5+ ore"


def run_doctor(definition: Dict, do_enrich: bool = False) -> Dict:
    """
    Audit (and optionally enrich) an adventure definition.

    Returns:
      {
        score: float,
        findings: [{severity, category, entity_id, message, fix_hint}],
        estimated_session_length: str,       # e.g. "2-3 ore"
        enriched_definition: dict | None,   # only if do_enrich=True
        score_after: float | None,
      }
    """
    findings = audit(definition)
    current_score = score(findings)

    result: Dict[str, Any] = {
        "score": current_score,
        "findings": [
            {
                "severity":  f.severity,
                "category":  f.category,
                "entity_id": f.entity_id,
                "message":   f.message,
                "fix_hint":  f.fix_hint,
            }
            for f in findings
        ],
        "estimated_session_length": _estimate_session_length(definition),
        "enriched_definition": None,
    }

    if not do_enrich:
        return result

    categories = {f.category for f in findings}
    context = (
        f"{definition.get('title', '')} — {definition.get('genre', '')} "
        f"— {(definition.get('premise') or '')[:200]}"
    )
    enriched = dict(definition)

    # [BALANCE] Prima di tutto: correggi squilibri strutturali clue/thread
    if "balance" in categories:
        print("[doctor] fixing structural balance (clues/threads)")
        enriched = _enrich_structure_balance(enriched, findings)

    # initial_hook
    if not enriched.get("initial_hook"):
        print("[doctor] generating initial_hook")
        hook = _enrich_initial_hook(enriched)
        if hook:
            enriched["initial_hook"] = hook

    # NPCs
    if "npc" in categories:
        npc_ids = {f.entity_id for f in findings if f.category == "npc"}
        enriched["actors"] = [
            _enrich_npc(a, context) if a.get("id") in npc_ids else a
            for a in enriched.get("actors", [])
        ]

    # Clocks
    if "clock" in categories and enriched.get("event_clocks"):
        clock_ids = {f.entity_id for f in findings if f.category == "clock"}
        title = definition.get("title", "")
        if clock_ids - {title}:
            enriched["event_clocks"] = _enrich_clocks(enriched["event_clocks"], context)

    # Clues
    if "clue" in categories and enriched.get("clues"):
        enriched["clues"] = _enrich_clues(enriched["clues"], context)

    # Phantom thread references — crea stub story_threads per ID referenziati ma non definiti
    existing_thread_ids = {str(t.get("id") or "") for t in (enriched.get("story_threads") or [])}
    phantom_pids: Dict[str, List[str]] = {}
    for cl in (enriched.get("clues") or []):
        tid = str(cl.get("thread_id") or "").strip()
        if tid and tid not in existing_thread_ids:
            phantom_pids.setdefault(tid, []).append(str(cl.get("id") or "?"))
    for rv in (enriched.get("revelations") or []):
        tid = str(rv.get("thread_id") or "").strip()
        if tid and tid not in existing_thread_ids:
            phantom_pids.setdefault(tid, []).append(f"rev:{rv.get('id') or '?'}")
    if phantom_pids:
        threads_list = list(enriched.get("story_threads") or [])
        clue_by_id = {str(c.get("id")): c for c in (enriched.get("clues") or [])}
        rev_by_id = {str(r.get("id")): r for r in (enriched.get("revelations") or [])}
        for pid, refs in phantom_pids.items():
            # Cerca testo evocativo dalla prima clue/revelation collegata
            label = pid.replace("_", " ").replace("thread", "").strip().capitalize() or pid
            question = ""
            for ref in refs:
                if ref.startswith("rev:"):
                    rv = rev_by_id.get(ref[4:])
                    if rv and (rv.get("statement") or rv.get("payoff")):
                        question = str(rv.get("statement") or rv.get("payoff"))[:120]
                        break
                else:
                    cl = clue_by_id.get(ref)
                    if cl and (cl.get("label") or cl.get("payoff")):
                        question = f"Cosa rivela {cl.get('label') or cl.get('id')}?"
                        break
            stub = {
                "id": pid,
                "title": label,
                "question": question or f"Pista da chiarire: {label}",
                "true_answer": "",
                "clue_plan": [],
                "required_clues": [],
                "status": "hidden",
                "parent_thread_ids": [],
                "linked_npcs": [],
                "_recovered_phantom": True,  # marker per debug
            }
            threads_list.append(stub)
        enriched["story_threads"] = threads_list
        print(f"[doctor] recovered {len(phantom_pids)} phantom thread stub(s): {list(phantom_pids.keys())}")

    # Locations vuote
    if "location" in categories and enriched.get("locations"):
        locs = enriched["locations"]
        # Fix gerarchia orfane se nessuna ha parent_location_id oppure ci sono warning orfani
        orphan_ids = {f.entity_id for f in findings if f.category == "location" and "parent_location_id" in f.fix_hint}
        has_hierarchy = any(l.get("parent_location_id") for l in locs)
        if orphan_ids or (len(locs) >= 5 and not has_hierarchy):
            print("[doctor] reorganizing location hierarchy")
            locs = _enrich_location_hierarchy(locs, context)
        enriched["locations"] = _enrich_locations(locs, context)

    # Re-score
    new_findings = audit(enriched)
    enriched["_doctor_score"] = score(new_findings)

    result["enriched_definition"] = enriched
    result["score_after"] = enriched["_doctor_score"]
    return result
