from __future__ import annotations

from .runtime_models import AdventureRuntime
from .escalation_limiter import compute_allowed_escalation_tier
from .genre_constraints import get_genre_profile
from .scene_context import present_actors_at, visible_clues_at


def make_director_decision(
    runtime: AdventureRuntime,
    simulation: dict,
    *,
    prerolled: dict | None = None,
    current_scene_id: str | None = None,
) -> dict:
    """Trasforma lo stato simulato in una direttiva singola e concreta per il renderer AI."""
    prerolled = prerolled or {}
    success = bool(prerolled.get("success", True))
    ready = simulation.get("ready_threads") or []
    clue_id = simulation.get("selected_clue_id")
    npcs_to_introduce = simulation.get("npcs_to_introduce") or []
    clock_tick = int(simulation.get("clock_tick") or 0)
    clock_triggers = simulation.get("clock_triggers") or []
    action_intent = str(prerolled.get("intent") or "")
    genre_profile = runtime.genre_profile.model_dump() if hasattr(runtime.genre_profile, "model_dump") else (runtime.genre_profile or {})
    if not genre_profile:
        genre_profile = get_genre_profile([runtime.runtime_profile], runtime.genre)
    allowed_tier = compute_allowed_escalation_tier(
        prerolled,
        action_intent,
        runtime.runtime_profile,
        active_clocks=[{"completed": bool(clock_triggers), "tick": clock_tick}],
        scene_context={
            "completed_clock": bool(clock_triggers),
            "finale_condition_met": any(f.status == "satisfied" for f in runtime.finale_conditions),
        },
        genre_profile=genre_profile,
    )
    primary_archetype = (runtime.archetype_profile or {}).get("primary_archetype") or runtime.runtime_profile
    archetype_bias = {
        "investigation_graph": "Bias archetipo: privilegia indizi, deduzioni, testimoni e conflitti sociali; evita combattimenti gratuiti.",
        "room_keyed_dungeon": "Bias archetipo: privilegia esplorazione stanza, accessi, rischi, risorse e mappa.",
        "heist": "Bias archetipo: privilegia security response, heat, route choices e risorse di estrazione.",
        "survival_escape": "Bias archetipo: privilegia route, safe node, risorse, pericolo e ritirata possibile.",
        "horror_survival": "Bias archetipo: privilegia dread, informazione parziale e costi locali senza catastrofi non autorizzate.",
        "romance_drama": "Bias archetipo: privilegia relazione, scelta emotiva, segreti personali e conseguenze sociali.",
        "military_operation": "Bias archetipo: privilegia obiettivi tattici, terreno, forze, vincoli e tempo.",
        "faction_sandbox": "Bias archetipo: privilegia agende di fazione, eventi offscreen e cambi di alleanza.",
    }.get(primary_archetype, "")

    # Gerarchia di priorità: clock completo > deduzione pronta > NPC > indizio > fallimento > idle
    if clock_triggers:
        t = clock_triggers[0]
        scene_directive = (
            f"CLOCK COMPLETO [{t['label']}]: la conseguenza si manifesta ora. "
            f"Narra: {t['consequence'] or t['on_complete']}. Non è evitabile."
        )
    elif ready:
        rev = next((r for r in runtime.revelations if (r.thread_id or r.id) == ready[0]), None)
        statement = rev.statement if rev else ready[0]
        scene_directive = (
            f"Offri una scena di deduzione sulla pista '{ready[0]}': {statement}. "
            f"Non aprire nuovi filoni prima di aver chiuso questa."
        )
    elif npcs_to_introduce:
        npc_id = npcs_to_introduce[0]
        actor = next((a for a in runtime.actors if a.id == npc_id), None)
        if actor:
            scene_directive = (
                f"Introduci l'attore canonico '{actor.name}' ({actor.role}) in questa scena. "
                f"Obiettivo dell'NPC: {actor.goal or 'non dichiarato'}."
            )
        else:
            scene_directive = f"Introduci l'NPC canonico '{npc_id}' in questa scena."
    elif clue_id:
        clue = next((c for c in runtime.clues if c.id == clue_id), None)
        label = clue.label if clue else clue_id
        found_update = simulation.get("proposed_updates", {}).get("clues_found") or []
        if found_update:
            scene_directive = (
                f"Narra l'ottenimento definitivo dell'indizio canonico [{clue_id}]: {label}. "
                f"Il personaggio lo recupera, legge o conferma in modo chiaro."
            )
        else:
            scene_directive = (
                f"Fai progredire l'indizio canonico [{clue_id}]: {label}. "
                f"Solo avanzamento parziale — non ancora prova completa."
            )
    elif not success:
        scene_directive = (
            "Narra un costo narrativo concreto: non bloccare la storia, "
            "ma imponi una conseguenza visibile (allarme, ferita, PNG che si chiude, accesso bloccato)."
        )
    else:
        scene_directive = (
            "Muovi un elemento canonico: NPC che cambia posizione, "
            "clock che si fa sentire nel mondo, o location che rivela qualcosa di nuovo."
        )

    final_directive = f"{scene_directive} {archetype_bias}".strip()

    # Elementi canonici visibili nella scena corrente (per vincoli di visibilità F4)
    scene_clues: list[dict] = []
    scene_actors: list[dict] = []
    if current_scene_id:
        for c in visible_clues_at(None, runtime, current_scene_id):  # type: ignore[arg-type]
            if c.state not in {"discovered", "spent"}:
                scene_clues.append({"id": c.id, "label": c.label, "type": c.type or ""})
        for a in present_actors_at(None, runtime, current_scene_id):  # type: ignore[arg-type]
            if a.status not in {"dead", "captured", "resolved"}:
                scene_actors.append({"id": a.id, "name": a.name, "role": a.role or ""})

    return {
        "scene_directive": final_directive,
        "director_notes": simulation.get("events") or [],
        "renderer_priorities": [final_directive],  # backward compat
        "state_updates_required": simulation.get("proposed_updates", {}),
        "runtime_profile": runtime.runtime_profile,
        "genre_profile": genre_profile,
        "allowed_escalation_tier": allowed_tier,
        "allowed_escalation_types": list(genre_profile.get("allowed_escalations") or []),
        "forbidden_escalation_types": list(genre_profile.get("forbidden_escalations") or []),
        "reason": (
            f"Roll={prerolled.get('outcome','?')}; intent={action_intent or '?'}; "
            f"profile={runtime.runtime_profile}; archetype={primary_archetype}; clock_triggers={len(clock_triggers)}"
        ),
        "director_authorization": allowed_tier >= 5 and bool(clock_triggers),
        # Strutturati
        "selected_clue_id": clue_id,
        "npcs_to_introduce": npcs_to_introduce,
        "clock_tick": clock_tick,
        "clock_triggers": clock_triggers,
        "ready_threads": ready,
        "scene_clues": scene_clues,
        "scene_actors": scene_actors,
        "current_scene_id": current_scene_id or "",
    }


def director_prompt_context(decision: dict) -> str:
    directive = decision.get("scene_directive") or "renderizza lo stato corrente"
    notes = "; ".join(decision.get("director_notes") or []) or "nessuna nota"
    required = decision.get("state_updates_required") or {}
    allowed_tier = int(decision.get("allowed_escalation_tier", 3))
    allowed_types = decision.get("allowed_escalation_types") or []
    forbidden_types = decision.get("forbidden_escalation_types") or []

    clue_id = decision.get("selected_clue_id")
    npcs = decision.get("npcs_to_introduce") or []
    clock_tick = int(decision.get("clock_tick") or 0)
    triggers = decision.get("clock_triggers") or []
    ready = decision.get("ready_threads") or []
    scene_clues = decision.get("scene_clues") or []
    scene_actors = decision.get("scene_actors") or []
    current_scene_id = decision.get("current_scene_id") or ""

    lines = [
        "\nNARRATIVE DIRECTOR — ISTRUZIONI VINCOLANTI:",
        f"DIRETTIVA SCENA: {directive}",
        f"MAX ESCALATION TIER: {allowed_tier}. Il renderer non puo superarlo.",
        f"ESCALATION CONSENTITE: {', '.join(allowed_types[:10]) or 'solo conseguenze locali'}",
        f"ESCALATION VIETATE: {', '.join(forbidden_types[:12]) or 'nessuna dichiarata'}",
    ]
    if current_scene_id:
        if scene_clues:
            clue_list = "; ".join(f"{c['label']} [{c['id']}]" for c in scene_clues[:8])
            lines.append(f"INDIZI PRESENTI IN SCENA ({current_scene_id}): {clue_list}")
        else:
            lines.append(f"INDIZI PRESENTI IN SCENA ({current_scene_id}): nessuno disponibile in questa location")
        if scene_actors:
            actor_list = "; ".join(f"{a['name']} ({a['role']}) [{a['id']}]" for a in scene_actors[:6])
            lines.append(f"NPC PRESENTI IN SCENA: {actor_list}")
        else:
            lines.append(f"NPC PRESENTI IN SCENA: nessuno fisicamente qui ora")
        lines.append(
            "REGOLA VISIBILITÀ: non narrare indizi o NPC assenti da questa lista come fisicamente presenti. "
            "Elementi non in lista possono essere menzionati solo come lontani, voci o ricordi."
        )
    if clue_id:
        found_update = required.get("clues_found") or []
        clue_type = "OTTENIMENTO DEFINITIVO" if found_update else "AVANZAMENTO PARZIALE"
        lines.append(f"INDIZIO MOTORE [{clue_type}]: usa solo id={clue_id}. Non creare altri indizi.")
    if npcs:
        lines.append(f"NPC DA INTRODURRE: {', '.join(npcs)}. Devono comparire fisicamente in scena.")
    if clock_tick > 0:
        lines.append(f"CLOCK +{clock_tick}: la minaccia cresce — fallo sentire nel tono e nel contesto.")
    if triggers:
        lines.append(
            f"CLOCK COMPLETO — conseguenza narrativa obbligatoria: "
            f"{triggers[0]['consequence'] or triggers[0]['on_complete']}"
        )
    if ready:
        lines.append(f"PISTE PRONTE: {', '.join(ready)}. Non aprire nuovi filoni prima di offrire deduzione.")
    lines.append(f"Note stato: {notes}")
    lines.append(f"State updates decisi dal motore: {required}")
    lines.append(f"Motivo limite escalation: {decision.get('reason','')}")
    lines.append("La AI aggiunge dettagli narrativi, ma NON può contraddire queste istruzioni.")

    return "\n".join(lines)
