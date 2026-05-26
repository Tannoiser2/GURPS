from __future__ import annotations

from .runtime_models import AdventureRuntime
from .world_reaction_engine import generate_world_reactions


_INVESTIGATIVE_WORDS = {
    "cerca", "cerco", "indaga", "indagare", "esamina", "esaminare", "legge",
    "leggere", "interroga", "interrogare", "osserva", "analizza", "decifra",
    "studia", "ispeziona", "controlla", "traccia", "segue",
}


def _action_is_investigative(player_action: str, skill: str = "") -> bool:
    blob = f"{player_action} {skill}".lower()
    return (
        any(w in blob for w in _INVESTIGATIVE_WORDS)
        or any(w in blob for w in ["investig", "perce", "decifr", "cultura"])
    )


def _compute_clock_tick(prerolled: dict) -> int:
    """Quanti tick avanza il threat_level questo turno.
    Solo i fallimenti fanno avanzare la pressione: il successo parziale è
    'ce l'hai fatta con complicazioni', non un fallimento."""
    success = bool(prerolled.get("success", True))
    margin = int(prerolled.get("margin", 0))
    critical = bool(prerolled.get("critical", False))

    if not success:
        return 2 if (critical or margin <= -5) else 1
    return 0


def _select_clue(
    runtime: AdventureRuntime,
    game_state_data: dict,
    player_action: str,
    skill: str,
    success: bool,
) -> tuple[str | None, str]:
    """Seleziona deterministicamente UN indizio su cui agire. Ritorna (clue_id | None, motivo)."""
    found = set(game_state_data.get("clues_found") or [])
    progress = game_state_data.get("clue_progress") or {}

    current_name = ""
    map_state = game_state_data.get("map_state") or {}
    if map_state:
        node = (map_state.get("nodes") or {}).get(map_state.get("current_node_id")) or {}
        current_name = str(node.get("name") or "")

    hidden = [c for c in runtime.clues if c.id not in found and c.state != "discovered"]
    if not hidden:
        return None, "tutti gli indizi trovati"

    # Filtra per location corrente se possibile
    local = []
    if current_name:
        local = [
            c for c in hidden
            if c.source_location and (
                c.source_location.lower() in current_name.lower()
                or current_name.lower() in c.source_location.lower()
            )
        ]

    # Pool: locale se disponibile, altrimenti globale
    pool = local if local else (hidden if _action_is_investigative(player_action, skill) else [])
    if not pool:
        return None, "azione non investigativa fuori location, nessun indizio forzato"

    # Ordine: prima i più vicini al completamento (ticks alti), poi i required
    def _sort_key(c):
        ticks = int(((progress.get(c.id) or {}).get("ticks") or c.progress_ticks or 0))
        return (-ticks, not c.is_required)

    clue = sorted(pool, key=_sort_key)[0]
    ticks = int(((progress.get(clue.id) or {}).get("ticks") or clue.progress_ticks or 0))

    if success and ticks >= 1:
        return clue.id, f"completamento indizio canonico [{clue.id}]"
    return clue.id, f"avanzamento indizio canonico [{clue.id}]"


def _npcs_to_introduce(runtime: AdventureRuntime, game_state_data: dict) -> list[str]:
    """Determina quali NPC devono apparire questo turno per pressione narrativa."""
    threat_level = int(game_state_data.get("threat_level") or 0)
    threat_max = max(1, max((c.max_value for c in runtime.event_clocks), default=8))
    threat_pct = threat_level / threat_max

    candidates = []
    for actor in runtime.actors:
        if actor.status != "unintroduced":
            continue
        p = actor.agenda_pressure
        # Soglie: più alta la pressione dell'NPC, prima entra in scena
        if p >= 3 and threat_pct >= 0.20:
            candidates.append((0, actor.id))
        elif p >= 2 and threat_pct >= 0.35:
            candidates.append((1, actor.id))
        elif p >= 1 and threat_pct >= 0.55:
            candidates.append((2, actor.id))
        elif threat_pct >= 0.75:
            candidates.append((3, actor.id))

    candidates.sort()
    # Massimo 1 NPC introdotto per turno
    return [npc_id for _, npc_id in candidates[:1]]


def _clock_runtime_value(clock_id: str, game_state_data: dict) -> int:
    """Valore corrente del clock dal runtime (contatore proprio, indipendente da threat_level)."""
    rt = game_state_data.get("clock_runtime") or {}
    return int((rt.get(clock_id) or {}).get("value") or 0)


def _clock_is_discovered(clock: AdventureRuntime, game_state_data: dict) -> bool:
    """True se i giocatori sanno già di questo clock."""
    if getattr(clock, "discovered", False):
        return True
    rt = game_state_data.get("clock_runtime") or {}
    return bool((rt.get(clock.id) or {}).get("discovered", False))


def _per_clock_ticks(runtime: AdventureRuntime, prerolled: dict) -> dict[str, int]:
    """Calcola quanti tick avanza ogni clock singolo in base all'esito del tiro."""
    success = bool(prerolled.get("success", True))
    critical = bool(prerolled.get("critical", False))
    margin = int(prerolled.get("margin", 0))
    outcome = str(prerolled.get("outcome") or "").lower()
    is_partial = "parziale" in outcome

    result: dict[str, int] = {}
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        if not success:
            base = getattr(clock, "ticks_per_failure", 1)
            result[clock.id] = base + 1 if (critical or margin <= -5) else base
        elif is_partial:
            result[clock.id] = getattr(clock, "ticks_per_partial", 1)
        else:
            result[clock.id] = getattr(clock, "ticks_per_success", 0)
    return result


def _clock_is_resolved(clock, game_state_data: dict) -> bool:
    """True se i giocatori hanno già risolto questo clock trovando tutti gli indizi di risoluzione."""
    if getattr(clock, "resolved", False):
        return True
    rt = game_state_data.get("clock_runtime") or {}
    return bool((rt.get(clock.id) or {}).get("resolved", False))


def _check_clock_triggers(runtime: AdventureRuntime, game_state_data: dict, per_clock_ticks: dict[str, int]) -> list[dict]:
    """Calcola quali clock raggiungono il massimo dopo i tick di questo turno (contatori propri)."""
    triggers = []
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        if _clock_is_resolved(clock, game_state_data):
            continue
        current = _clock_runtime_value(clock.id, game_state_data)
        tick = per_clock_ticks.get(clock.id, 0)
        new_value = current + tick
        if new_value >= clock.max_value > current:
            triggers.append({
                "clock_id": clock.id,
                "label": clock.label,
                "consequence": clock.consequence,
                "on_complete": clock.on_complete,
                "discovered": _clock_is_discovered(clock, game_state_data),
                "clock_type": getattr(clock, "clock_type", "narrative"),
            })
    return triggers


def _clock_step_reactions(runtime: AdventureRuntime, game_state_data: dict, per_clock_ticks: dict[str, int]) -> list[dict]:
    reactions = []
    for clock in runtime.event_clocks:
        if not clock.active or not clock.steps:
            continue
        current = _clock_runtime_value(clock.id, game_state_data)
        tick = per_clock_ticks.get(clock.id, 0)
        if tick <= 0:
            continue
        for value in range(current + 1, min(current + tick, clock.max_value) + 1):
            step = next((s for s in clock.steps if int(s.get("step") or 0) == value), None)
            if not step:
                continue
            reactions.append({
                "clock_id": clock.id,
                "clock_label": clock.label,
                "step": value,
                "discovered": _clock_is_discovered(clock, game_state_data),
                "world_state_change": step.get("world_state_change") or step.get("event") or "",
                "scene_prompt": step.get("scene_prompt") or "",
                "possible_player_response": step.get("possible_player_response") or "",
            })
    return reactions


def _auto_discover_clocks(runtime: AdventureRuntime, game_state_data: dict, just_found_clues: list[str]) -> list[dict]:
    """Se un indizio appena trovato è la chiave di scoperta di un clock, lo svela ai giocatori."""
    just_found = set(just_found_clues)
    discoveries = []
    for clock in runtime.event_clocks:
        if not clock.active or _clock_is_discovered(clock, game_state_data):
            continue
        disc_clue = getattr(clock, "discovery_clue_id", "") or ""
        if disc_clue and disc_clue in just_found:
            discoveries.append({
                "clock_id": clock.id,
                "label": clock.label,
                "current_value": _clock_runtime_value(clock.id, game_state_data),
                "max_value": clock.max_value,
                "consequence": clock.consequence,
                "discovery_clue_id": disc_clue,
            })
    return discoveries


def simulate_world_state(
    runtime: AdventureRuntime,
    *,
    player_action: str,
    prerolled: dict | None,
    game_state_data: dict,
) -> dict:
    """Decide conseguenze minime prima della narrazione AI, usando solo elementi canonici."""
    prerolled = prerolled or {}
    success = bool(prerolled.get("success", True))
    outcome = str(prerolled.get("outcome") or "").lower()
    skill = str(prerolled.get("skill") or "")

    # Per compatibilità: _compute_clock_tick dà il tick "generico" usato da threat_level
    clock_tick = _compute_clock_tick(prerolled)
    # Clock indipendenti: ogni clock ha il proprio contatore
    per_clock = _per_clock_ticks(runtime, prerolled)
    clue_id, clue_reason = _select_clue(runtime, game_state_data, player_action, skill, success)
    npcs_to_introduce = _npcs_to_introduce(runtime, game_state_data)
    clock_triggers = _check_clock_triggers(runtime, game_state_data, per_clock)
    clock_step_reactions = _clock_step_reactions(runtime, game_state_data, per_clock)

    progress = game_state_data.get("clue_progress") or {}
    found = set(game_state_data.get("clues_found") or [])

    clue_progress_update: list[dict] = []
    clues_found_update: list[str] = []

    if clue_id:
        ticks = int(((progress.get(clue_id) or {}).get("ticks") or 0))
        if success and ticks >= 1:
            clues_found_update.append(clue_id)
        else:
            label = next((c.label for c in runtime.clues if c.id == clue_id), clue_id)
            clue_progress_update.append({
                "clue_id": clue_id,
                "note": f"Avanzamento verso: {label}",
                "ticks": 1,
            })

    found_after = found | set(clues_found_update)
    # Scoperta automatica di clock: se un indizio trovato ora svela un clock nascosto
    newly_discovered_clocks = _auto_discover_clocks(runtime, game_state_data, clues_found_update)
    # Auto-risoluzione: se tutti gli indizi di risoluzione di un clock sono stati trovati, il clock si ferma
    auto_resolved_clocks: list[dict] = []
    for clock in runtime.event_clocks:
        if not clock.active or _clock_is_resolved(clock, game_state_data):
            continue
        res_clues = getattr(clock, "resolution_clues", []) or []
        if res_clues and all(cid in found_after for cid in res_clues):
            auto_resolved_clocks.append({
                "clock_id": clock.id,
                "label": clock.label,
                "clock_type": getattr(clock, "clock_type", "narrative"),
                "resolution_condition": getattr(clock, "resolution_condition", "") or "",
            })

    ready = []
    for rev in runtime.revelations:
        if rev.status == "revealed" or not rev.required_clues:
            continue
        minimum = min(2, max(1, len(rev.required_clues)))
        if len([cid for cid in rev.required_clues if cid in found_after]) >= minimum:
            ready.append(rev.thread_id or rev.id)

    events: list[str] = []
    if clock_tick > 0:
        events.append(f"Clock avanza di {clock_tick} tick questo turno.")
    if not success:
        events.append("Fallimento: costo narrativo concreto obbligatorio.")
    elif "parziale" in outcome:
        events.append("Successo parziale: progresso incompleto con costo latente.")
    if clue_id:
        if clues_found_update:
            events.append(f"Prova canonica [{clue_id}] completata: narra come viene ottenuta.")
        else:
            events.append(f"Indizio [{clue_id}] avanza di 1 tick: progresso parziale, non ancora prova.")
    if npcs_to_introduce:
        events.append(f"NPC da introdurre in questa scena: {', '.join(npcs_to_introduce)}.")
    for r in auto_resolved_clocks:
        ctype = r.get("clock_type", "narrative")
        cond = r.get("resolution_condition") or "trovando tutti gli indizi necessari"
        if ctype == "terminal_defeat":
            events.append(f"CLOCK SVENTATO [{r['label']}] (terminal_defeat): i giocatori hanno trovato tutti gli indizi e fermato il conto alla rovescia in tempo! Narra la risoluzione drammatica come salvezza all'ultimo momento.")
        elif ctype == "terminal_victory":
            events.append(f"CLOCK COMPLETATO CON VITTORIA [{r['label']}]: i giocatori hanno raggiunto la condizione di vittoria ({cond}). L'avventura si conclude con il loro trionfo.")
        else:
            events.append(f"CLOCK RISOLTO [{r['label']}]: i giocatori hanno fermato questo conto alla rovescia ({cond}). Il pericolo immediato passa.")
    for disc in newly_discovered_clocks:
        remaining = disc["max_value"] - disc["current_value"]
        events.append(
            f"CLOCK SVELATO [{disc['label']}]: i giocatori scoprono che esiste questo conto alla rovescia. "
            f"Valore attuale {disc['current_value']}/{disc['max_value']} — restano {remaining} segmenti prima che: {disc['consequence']}. "
            "Narra la rivelazione in modo drammatico."
        )
    for t in clock_triggers:
        ctype = t.get("clock_type", "narrative")
        if ctype == "terminal_defeat":
            events.append(f"CLOCK TERMINALE [{t['label']}] — SCONFITTA: {t['consequence'] or t['on_complete']}. Questo è l'ultimo turno dell'avventura. story_over=true, victory=false.")
        elif ctype == "terminal_victory":
            events.append(f"CLOCK TERMINALE [{t['label']}] — VITTORIA: {t['consequence'] or t['on_complete']}. Questo è l'ultimo turno dell'avventura. story_over=true, victory=true.")
        elif ctype == "escalation":
            events.append(f"CLOCK ESCALATION [{t['label']}]: {t['consequence'] or t['on_complete']}. La minaccia scala massivamente — threat_increase +3.")
        elif t.get("discovered"):
            events.append(f"CLOCK COMPLETO [{t['label']}] (noto ai giocatori): {t['consequence'] or t['on_complete']}.")
        else:
            events.append(f"CLOCK COMPLETO [{t['label']}] (silente — i giocatori non sapevano): {t['consequence'] or t['on_complete']}. Narra la conseguenza come evento improvviso, non come 'countdown scaduto'.")
    for reaction in clock_step_reactions:
        if reaction.get("discovered"):
            events.append(f"CLOCK STEP [{reaction['clock_label']} {reaction['step']}]: {reaction['world_state_change']}.")
        else:
            # Clock nascosto: dai solo il segnale ambiguo dal campo discovery_hint o scene_prompt
            hint = reaction.get("scene_prompt") or reaction.get("world_state_change") or ""
            if hint:
                events.append(f"SEGNALE AMBIGUO (clock nascosto {reaction['clock_label']}): {hint} — narra in modo misterioso, senza rivelare il clock.")
    if ready:
        events.append(f"Piste pronte alla deduzione: {', '.join(ready)}.")
    actor_agendas = [
        {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "goal": a.goal,
            "pressure_response": a.pressure_response,
        }
        for a in runtime.actors
    ]
    current_location = {}
    map_state = game_state_data.get("map_state") or {}
    if map_state:
        current_location = (map_state.get("nodes") or {}).get(map_state.get("current_node_id")) or {}
    world_reactions = generate_world_reactions(
        player_action_result=prerolled,
        clock_state={
            "clock_step_reactions": clock_step_reactions,
            "threat_level": int(game_state_data.get("threat_level") or 0) + clock_tick,
        },
        npc_agendas=actor_agendas,
        current_location=current_location,
    )
    for reaction in world_reactions[:2]:
        events.append(f"REAZIONE MONDO [{reaction['type']}]: {reaction['world_state_change']}.")

    npc_updates = [
        {
            "id": npc_id,
            "status": "introduced",
            "arc_status": "introduced",
            "note": "Il runtime lo introduce per pressione narrativa coerente con la sua agenda.",
        }
        for npc_id in npcs_to_introduce
    ]
    for reaction in world_reactions:
        npc_id = reaction.get("npc_id")
        if reaction.get("type") == "npc_pressure_response" and npc_id:
            npc_updates.append({
                "id": npc_id,
                "status": "active",
                "arc_status": "active",
                "note": reaction.get("world_state_change", ""),
            })
            break

    # Costruisce clock_updates: avanza il valore di ogni clock nel runtime
    auto_resolved_ids = {r["clock_id"] for r in auto_resolved_clocks}
    clock_updates = []
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        tick = per_clock.get(clock.id, 0)
        current = _clock_runtime_value(clock.id, game_state_data)
        entry: dict = {"id": clock.id, "delta": tick}
        if any(d["clock_id"] == clock.id for d in newly_discovered_clocks):
            entry["discovered"] = True
        if clock.id in auto_resolved_ids:
            entry["resolved"] = True
        clock_updates.append(entry)

    def _clock_display_value(c) -> int:
        return _clock_runtime_value(c.id, game_state_data)

    return {
        "proposed_updates": {
            "clue_progress": clue_progress_update,
            "clues_found": clues_found_update,
            "npc_updates": npc_updates[:3],
            "new_threads": [],
            "closed_threads": [],
            "threat_increase": clock_tick,
            "clock_updates": clock_updates,
            "location_access": [],
            "objective_progress": 0,
        },
        "events": events,
        "ready_threads": ready,
        "clock_summary": "; ".join(
            f"{c.label} {_clock_display_value(c)}/{c.max_value}"
            + (" [scoperto]" if _clock_is_discovered(c, game_state_data) else " [nascosto]")
            for c in runtime.event_clocks
        ),
        # Campi strutturati per il director
        "clock_tick": clock_tick,
        "per_clock_ticks": per_clock,
        "selected_clue_id": clue_id,
        "selected_clue_reason": clue_reason,
        "npcs_to_introduce": npcs_to_introduce,
        "clock_triggers": clock_triggers,
        "clock_step_reactions": clock_step_reactions,
        "world_reactions": world_reactions,
        "newly_discovered_clocks": newly_discovered_clocks,
        "auto_resolved_clocks": auto_resolved_clocks,
    }
