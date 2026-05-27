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
    severity: str    # "critical" | "warning" | "info"
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
    for fld, sev, hint in [
        ("premise",           "critical", "Aggiungi una descrizione generale dell'avventura"),
        ("initial_hook",      "critical", "Aggiungi il gancio iniziale (scena d'apertura per i PG)"),
        ("actors",            "critical", "Aggiungi almeno gli NPC principali"),
        ("locations",         "warning",  "Aggiungi le location principali"),
        ("event_clocks",      "warning",  "Aggiungi almeno 1 clock per creare urgenza"),
        ("finale_conditions", "info",     "Definisci le condizioni di vittoria/sconfitta"),
    ]:
        if not data.get(fld):
            findings.append(Finding(sev, "structure", title, f"Campo '{fld}' mancante", hint))

    if not data.get("clues") and not data.get("story_threads"):
        findings.append(Finding("warning", "structure", title,
            "Nessun indizio né thread narrativo",
            "Aggiungi clues o story_threads per guidare l'investigazione"))

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
        for fld in ("goal", "current_plan", "fallback_plan"):
            if not a.get(fld):
                findings.append(Finding("info", "npc", aid,
                    f"NPC '{name}': '{fld}' mancante", f"Aggiungi {fld}"))

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
            findings.append(Finding("info", "clock", cid,
                f"Clock '{label}': discovery_hint mancante",
                "Aggiungi un presagio narrativo ambiguo che segnala il pericolo"))

    return findings


def _clue_rules(clues: List[Dict], thread_ids: Set[str]) -> List[Finding]:
    findings = []
    for cl in clues:
        cid = cl.get("id", "?")
        label = cl.get("label", cid)

        for fld, hint in [
            ("payoff",              "cosa rivela narrativamente quando scoperta"),
            ("hidden_implication",  "significato nascosto oltre l'evidenza diretta"),
            ("wrong_interpretations", "1-2 false interpretazioni plausibili"),
        ]:
            if not cl.get(fld):
                findings.append(Finding("info", "clue", cid,
                    f"Indizio '{label}': '{fld}' mancante", hint))

        # thread_id esistente
        tid = str(cl.get("thread_id") or "").strip()
        if tid and thread_ids and tid not in thread_ids:
            findings.append(Finding("warning", "clue", cid,
                f"Indizio '{label}': thread_id '{tid}' non corrisponde a nessun thread",
                "Correggi thread_id o crea il thread mancante"))

    return findings


def _thread_rules(threads: List[Dict], clue_ids: Set[str]) -> List[Finding]:
    findings = []
    all_thread_ids = _ids(threads)

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
            findings.append(Finding("info", "thread", tid,
                f"Thread '{label}': nessun indizio associato",
                "Collega almeno 1 clue tramite thread_id o clue_plan"))

        # risposta canonica mancante
        if not t.get("true_answer") and not t.get("answer"):
            findings.append(Finding("info", "thread", tid,
                f"Thread '{label}': true_answer/answer mancante",
                "Definisci la risposta canonica nascosta al tavolo"))

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
            findings.append(Finding("info", "location", lid,
                f"Location '{name}': completamente vuota (nessun NPC, indizio né descrizione)",
                "Aggiungi description, un NPC o un indizio"))

        # Zona calda senza tactical_map
        if loc.get("has_combat_potential") or loc.get("contains_actors"):
            if not has_tmap:
                findings.append(Finding("info", "location", lid,
                    f"Location '{name}': potenziale combattimento ma tactical_map assente",
                    "Aggiungi tactical_map con enabled:true, layout e features"))
            elif has_tmap:
                # tactical_map presente ma incompleta
                if not tmap.get("features"):
                    findings.append(Finding("info", "location", lid,
                        f"Location '{name}': tactical_map senza features (coperture/elementi)",
                        "Aggiungi features: ['copertura', 'ostacolo', ...]"))
                if not tmap.get("hazards"):
                    findings.append(Finding("info", "location", lid,
                        f"Location '{name}': tactical_map senza hazards (rischi ambientali)",
                        "Aggiungi hazards: ['terreno difficile', ...]"))
                if not tmap.get("layout"):
                    findings.append(Finding("info", "location", lid,
                        f"Location '{name}': tactical_map senza layout",
                        "Specifica layout: 'room' | 'narrow' | 'open'"))

        # contains_loot ma nessun item definito
        if loc.get("contains_loot") and not loc.get("loot") and not loc.get("items"):
            findings.append(Finding("info", "location", lid,
                f"Location '{name}': contains_loot=true ma nessun item definito",
                "Aggiungi items: [...] alla location oppure rimuovi contains_loot"))

    return findings


def _resource_rules(resources: list, genre: str, title: str) -> List[Finding]:
    if not resources:
        horror = ("horror", "cosmic", "thriller", "survival", "western")
        sev = "warning" if any(h in genre.lower() for h in horror) else "info"
        return [Finding(sev, "resource", title,
            "Nessuna risorsa definita (sanità, morale, luce, tempo...)",
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
                    findings.append(Finding("info", "equipment", aid,
                        f"NPC '{name}': item '{item_str}' non riconosciuto dal catalogo",
                        "Verifica il nome o aggiungilo a data_items.py / data_weapons.py"))

    # ── Controlli item nelle location ─────────────────────────────────────────
    for itm in loc_items:
        iid = itm.get("id") or itm.get("name") or "?"
        iname = itm.get("name", iid)

        # skill_bonuses con skill sconosciute
        if weapon_check_available:
            for skill_name, bonus in (itm.get("skill_bonuses") or {}).items():
                if skill_name not in VALID_SKILLS:
                    findings.append(Finding("info", "equipment", str(iid),
                        f"Item '{iname}': skill_bonus su skill sconosciuta '{skill_name}'",
                        f"Skill valide: ricerca, investigare, percezione, furtivita, ..."))

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
            findings.append(Finding("info", "equipment", item_name,
                f"Item chiave '{item_name}' non referenziato in nessun thread né clue",
                "Collega l'oggetto a un thread o clue che ne usi il ritrovamento"))

    # ── Items negli aventura-level key_items ──────────────────────────────────
    for ki in data.get("key_items", []):
        if not isinstance(ki, dict):
            continue
        kiname = ki.get("name") or ki.get("id") or "?"
        if not ki.get("dove") and not ki.get("location") and not ki.get("where"):
            findings.append(Finding("info", "equipment", str(kiname),
                f"Key item '{kiname}': posizione (dove) non specificata",
                "Aggiungi 'dove': 'nome_location' per il posizionamento narrativo"))

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
    findings.extend(_thread_rules(data.get("story_threads", []), clue_ids))
    findings.extend(_location_rules(data.get("locations", []), actor_by_loc, clue_by_loc))
    findings.extend(_resource_rules(
        data.get("resources", []),
        data.get("genre", ""),
        data.get("title", data.get("id", "?")),
    ))
    findings.extend(_equipment_rules(data))
    return findings


def score(findings: List[Finding]) -> float:
    penalty = sum({"critical": 1.5, "warning": 0.5, "info": 0.1}[f.severity] for f in findings)
    return max(0.0, round(10.0 - penalty, 1))


# ─── Enrichment helpers ───────────────────────────────────────────────────────

def _json_from_llm(raw: str) -> Any:
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


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

def run_doctor(definition: Dict, do_enrich: bool = False) -> Dict:
    """
    Audit (and optionally enrich) an adventure definition.

    Returns:
      {
        score: float,
        findings: [{severity, category, entity_id, message, fix_hint}],
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

    # Locations vuote
    if "location" in categories and enriched.get("locations"):
        enriched["locations"] = _enrich_locations(enriched["locations"], context)

    # Re-score
    new_findings = audit(enriched)
    enriched["_doctor_score"] = score(new_findings)

    result["enriched_definition"] = enriched
    result["score_after"] = enriched["_doctor_score"]
    return result
