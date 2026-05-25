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
    """Quanti tick avanza il clock questo turno — decisione del motore, non dell'AI."""
    success = bool(prerolled.get("success", True))
    margin = int(prerolled.get("margin", 0))
    outcome = str(prerolled.get("outcome") or "").lower()
    critical = bool(prerolled.get("critical", False))

    if not success:
        return 2 if (critical or margin <= -5) else 1
    if "parziale" in outcome:
        return 1
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


def _check_clock_triggers(runtime: AdventureRuntime, game_state_data: dict, clock_tick: int) -> list[dict]:
    """Calcola quali clock raggiungono il massimo dopo i tick di questo turno."""
    threat_level = int(game_state_data.get("threat_level") or 0)
    triggers = []
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        new_value = threat_level + clock_tick
        if new_value >= clock.max_value > threat_level:
            triggers.append({
                "clock_id": clock.id,
                "label": clock.label,
                "consequence": clock.consequence,
                "on_complete": clock.on_complete,
            })
    return triggers


def _clock_step_reactions(runtime: AdventureRuntime, game_state_data: dict, clock_tick: int) -> list[dict]:
    if clock_tick <= 0:
        return []
    threat_level = int(game_state_data.get("threat_level") or 0)
    reactions = []
    for clock in runtime.event_clocks:
        if not clock.active or not clock.steps:
            continue
        for value in range(threat_level + 1, min(threat_level + clock_tick, clock.max_value) + 1):
            step = next((s for s in clock.steps if int(s.get("step") or 0) == value), None)
            if not step:
                continue
            reactions.append({
                "clock_id": clock.id,
                "clock_label": clock.label,
                "step": value,
                "world_state_change": step.get("world_state_change") or step.get("event") or "",
                "scene_prompt": step.get("scene_prompt") or "",
                "possible_player_response": step.get("possible_player_response") or "",
            })
    return reactions


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

    clock_tick = _compute_clock_tick(prerolled)
    clue_id, clue_reason = _select_clue(runtime, game_state_data, player_action, skill, success)
    npcs_to_introduce = _npcs_to_introduce(runtime, game_state_data)
    clock_triggers = _check_clock_triggers(runtime, game_state_data, clock_tick)
    clock_step_reactions = _clock_step_reactions(runtime, game_state_data, clock_tick)

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
    for t in clock_triggers:
        events.append(f"CLOCK COMPLETO [{t['label']}]: {t['consequence'] or t['on_complete']}.")
    for reaction in clock_step_reactions:
        events.append(f"CLOCK STEP [{reaction['clock_label']} {reaction['step']}]: {reaction['world_state_change']}.")
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

    return {
        "proposed_updates": {
            "clue_progress": clue_progress_update,
            "clues_found": clues_found_update,
            "npc_updates": npc_updates[:3],
            "new_threads": [],
            "closed_threads": [],
            "threat_increase": clock_tick,
            "location_access": [],
            "objective_progress": 0,
        },
        "events": events,
        "ready_threads": ready,
        "clock_summary": "; ".join(f"{c.label} {c.value}/{c.max_value}" for c in runtime.event_clocks),
        # Campi strutturati per il director
        "clock_tick": clock_tick,
        "selected_clue_id": clue_id,
        "selected_clue_reason": clue_reason,
        "npcs_to_introduce": npcs_to_introduce,
        "clock_triggers": clock_triggers,
        "clock_step_reactions": clock_step_reactions,
        "world_reactions": world_reactions,
    }
