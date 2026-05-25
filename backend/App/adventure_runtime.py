from __future__ import annotations

from .runtime_models import (
    ActorState,
    AdventureRuntime,
    EventClock,
    FinaleCondition,
    HiddenTruth,
    LocationState,
    Objective,
    PressureSystem,
    Revelation,
    RuntimeClue,
)
from .genre_constraints import get_genre_profile


def _norm_id(value: str, fallback: str) -> str:
    value = str(value or "").strip()
    return value or fallback


def _profile_for(adventure: dict) -> str:
    blob = " ".join(str(adventure.get(k, "")) for k in ["genre", "detected_genre", "environment_type", "premise", "title"]).lower()
    if any(w in blob for w in ["rituale", "cripta", "dungeon", "catacomb", "sacrario"]):
        return "ritual_dungeon"
    if any(w in blob for w in ["fuga", "survival", "sopravviv", "evacu"]):
        return "survival_escape"
    if any(w in blob for w in ["insegu", "caccia", "braccat"]):
        return "pursuit_thriller"
    if any(w in blob for w in ["orrore", "malediz", "horror", "sangue"]):
        return "escalating_horror"
    if any(w in blob for w in ["colpo", "furto", "heist", "sabot"]):
        return "heist"
    return "investigation_graph"


def build_adventure_runtime(adventure: dict, game_state_data: dict | None = None) -> AdventureRuntime:
    """Converte la bibbia esistente in un runtime dichiarativo senza cambiare il formato pubblico."""
    game_state_data = game_state_data or {}
    found_ids = set(game_state_data.get("clues_found") or [])
    progress = game_state_data.get("clue_progress") or {}
    resolved_threads = set(game_state_data.get("resolved_threads") or [])
    locations_raw = [l for l in (adventure.get("locations") or []) if isinstance(l, dict)]
    npcs_raw = [n for n in (adventure.get("npcs") or []) if isinstance(n, dict)]
    clues_raw = [c for c in (adventure.get("clues") or []) if isinstance(c, dict)]
    threads_raw = [t for t in (adventure.get("story_threads") or []) if isinstance(t, dict)]
    canon = adventure.get("adventure_canon") or {}

    clues: list[RuntimeClue] = []
    for idx, raw in enumerate(clues_raw, start=1):
        cid = _norm_id(raw.get("id"), f"clue_{idx}")
        ticks = int((progress.get(cid) or {}).get("ticks", 0) or 0)
        state = "discovered" if cid in found_ids or raw.get("found") else ("partial" if ticks > 0 else "hidden")
        clues.append(RuntimeClue(
            id=cid,
            label=raw.get("label") or raw.get("text") or cid,
            type=raw.get("type") or "physical_evidence",
            thread_id=raw.get("thread_id") or "",
            source_location=raw.get("source_location") or raw.get("location") or "",
            reveals=raw.get("reveals") or "",
            payoff=raw.get("payoff") or "",
            state=state,
            progress_ticks=ticks,
            is_required=bool(raw.get("is_required", True)),
        ))

    locations: list[LocationState] = []
    for idx, raw in enumerate(locations_raw, start=1):
        lid = _norm_id(raw.get("id"), f"loc_{idx}")
        lname = raw.get("name") or lid
        contains_clues = [
            c.id for c in clues
            if c.source_location and (
                c.source_location.lower() in str(lname).lower()
                or str(lname).lower() in c.source_location.lower()
            )
        ]
        locations.append(LocationState(
            id=lid,
            name=lname,
            description=raw.get("description") or "",
            status="visited" if raw.get("visited") else "known",
            contains_clues=contains_clues,
            tactical_map=raw.get("tactical_map") or {},
        ))

    actors: list[ActorState] = []
    for idx, raw in enumerate(npcs_raw, start=1):
        nid = _norm_id(raw.get("id"), f"npc_{idx}")
        agenda = raw.get("npc_agenda") or {}
        raw_status = agenda.get("arc_status") or raw.get("status") or "unintroduced"
        status = {
            "alive": "active",
            "neutral": "active",
            "hidden": "unintroduced",
        }.get(str(raw_status), str(raw_status))
        if status not in {"unintroduced", "active", "exposed", "resolved", "dead", "missing"}:
            status = "active"
        actors.append(ActorState(
            id=nid,
            name=raw.get("name") or nid,
            role=agenda.get("role") or raw.get("role") or "neutral",
            location_id=raw.get("location_id") or raw.get("location") or "",
            status=status,
            goal=agenda.get("goal") or raw.get("goal") or "",
            secret=agenda.get("secret") or raw.get("secret") or "",
            agenda_pressure=int(raw.get("threat_to_player") or 0),
        ))

    revelations: list[Revelation] = []
    for idx, raw in enumerate(threads_raw, start=1):
        tid = _norm_id(raw.get("id"), f"T{idx}")
        required = raw.get("required_clues") or []
        if isinstance(required, int):
            required = [c.id for c in clues if c.thread_id == tid][:required]
        discovered = [cid for cid in required if cid in found_ids]
        minimum = int(raw.get("minimum_clues_to_deduce") or min(2, max(1, len(required) or 1)))
        status = "revealed" if tid in resolved_threads else ("available" if len(discovered) >= minimum else "hidden")
        revelations.append(Revelation(
            id=f"rev_{tid}",
            thread_id=tid,
            statement=raw.get("true_answer") or raw.get("answer") or raw.get("question") or tid,
            required_clues=list(required),
            status=status,
            payoff=raw.get("payoff") or raw.get("purpose") or "",
        ))

    objective = adventure.get("win_condition") or adventure.get("objective") or "Completare la missione."
    threat_max = int(adventure.get("threat_max_turns") or 8)
    threat_now = int(game_state_data.get("threat_level") or 0)
    runtime_profile = _profile_for(adventure)
    genre = adventure.get("genre") or adventure.get("detected_genre") or ""
    genre_profile = get_genre_profile([runtime_profile], genre)
    runtime = AdventureRuntime(
        id=str(adventure.get("id") or adventure.get("title") or "runtime"),
        title=adventure.get("title") or "",
        genre=genre,
        runtime_profile=runtime_profile,
        tone=adventure.get("tone") or adventure.get("atmosphere") or "",
        premise=adventure.get("premise") or "",
        initial_hook=adventure.get("initial_hook") or adventure.get("premise") or "",
        hidden_truths=[HiddenTruth(
            id="truth_core",
            statement=canon.get("core_truth") or adventure.get("hidden_truth") or "",
            reveal_clues=list(canon.get("required_clues") or [c.id for c in clues if c.is_required][:3]),
            reveal_rule=adventure.get("hidden_truth_reveal_rule") or "quando le rivelazioni richieste sono disponibili",
        )],
        objective_stack=[Objective(id="main", label=objective, status="active")],
        locations=locations,
        actors=actors,
        revelations=revelations,
        clues=clues,
        event_clocks=[EventClock(
            id="main_threat",
            label=adventure.get("threat_description") or "Minaccia principale",
            value=threat_now,
            max_value=threat_max,
            consequence=adventure.get("threat_description") or "",
            active=bool(adventure.get("has_time_pressure", True)),
        )],
        pressure_systems=[PressureSystem(
            id="threat",
            label="Pressione missione",
            value=threat_now,
            max_value=threat_max,
            description=adventure.get("threat_description") or "",
        )],
        finale_conditions=[FinaleCondition(
            id="finale_main",
            label=objective,
            required_threads=[r.thread_id for r in revelations if r.thread_id],
            required_clues=list(canon.get("required_clues") or [c.id for c in clues if c.is_required]),
            status="available" if any(r.status == "revealed" for r in revelations) else "locked",
        )],
        genre_profile=genre_profile,
        source_mode=adventure.get("source_mode") or "raw_text",
        archetype_profile=adventure.get("archetype_profile") or {},
        preservation_policy=adventure.get("preservation_policy") or {},
        allow_runtime_expansion=bool(canon.get("allow_runtime_expansion") or adventure.get("allow_runtime_expansion")),
    )
    return runtime


def runtime_prompt_context(runtime: AdventureRuntime) -> str:
    clocks = "; ".join(f"{c.label}={c.value}/{c.max_value}" for c in runtime.event_clocks) or "nessuno"
    hidden = "; ".join(h.statement for h in runtime.hidden_truths if h.statement) or "non dichiarata"
    available_revs = [r for r in runtime.revelations if r.status == "available"]
    partial_clues = [c for c in runtime.clues if c.state == "partial"]
    hidden_clues = [c for c in runtime.clues if c.state == "hidden"]
    return (
        "\nRUNTIME STATE-DRIVEN:"
        f"\n- Profilo runtime: {runtime.runtime_profile}"
        f"\n- Source mode: {runtime.source_mode}"
        f"\n- Archetipo: {(runtime.archetype_profile or {}).get('primary_archetype') or 'non dichiarato'}"
        f"\n- Profilo genere: {runtime.genre_profile.id} | tono: {runtime.genre_profile.tone}"
        f"\n- Verita canonica: {hidden}"
        f"\n- Clock attivi: {clocks}"
        f"\n- Rivelazioni disponibili: {'; '.join(r.statement for r in available_revs) or 'nessuna'}"
        f"\n- Indizi parziali: {'; '.join(f'[{c.id}] {c.label}' for c in partial_clues) or 'nessuno'}"
        f"\n- Prossimi indizi nascosti: {'; '.join(f'[{c.id}] {c.label} @ {c.source_location}' for c in hidden_clues[:4]) or 'nessuno'}"
        "\n- Regola: la AI deve renderizzare questo stato, non inventare nuove verita."
    )
