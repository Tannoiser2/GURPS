"""
NPC State Machine — tracks agenda_pressure per NPC and resolves current behavior.

Pressure is incremented when clues about an NPC are discovered.
The current behavior band is injected as a small context block into the master turn prompt.
Nothing is removed from the existing prompt — this is purely additive.
"""

from typing import Dict, List, Optional, Tuple
from .runtime_models import AdventureDefinition, AdventureRuntimeState


# Pressure bands — map pressure value to key in pressure_response
def _pressure_band(pressure: int) -> str:
    if pressure >= 9:
        return "extreme"
    if pressure >= 6:
        return "high"
    if pressure >= 3:
        return "medium"
    return "low"


def _actor_entry(runtime_state: AdventureRuntimeState, actor_id: str) -> dict:
    return dict((runtime_state.actor_runtime or {}).get(actor_id) or {})


def increment_pressure(
    actor_id: str,
    delta: int,
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> int:
    """Increment pressure for an NPC. Returns new pressure value."""
    actor_def = next((a for a in (definition.actors or []) if a.id == actor_id), None)
    if not actor_def:
        return 0

    entry = _actor_entry(runtime_state, actor_id)
    base_pressure = int(getattr(actor_def, "agenda_pressure", 0) or 0)
    current = int(entry.get("pressure", base_pressure))
    new_pressure = min(current + delta, 10)
    entry["pressure"] = new_pressure
    runtime_state.actor_runtime[actor_id] = entry
    return new_pressure


def update_pressure_from_clues(
    newly_discovered_clue_ids: List[str],
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> List[Tuple[str, int]]:
    """
    For each newly discovered clue, find NPCs it's about and increment their pressure.
    Returns list of (actor_id, new_pressure) for changed NPCs.
    """
    if not newly_discovered_clue_ids or not definition:
        return []

    # Build clue → actor index from definition
    clue_actor_map: Dict[str, List[str]] = {}
    for actor in (definition.actors or []):
        for clue_id in (actor.knows or []):
            clue_actor_map.setdefault(clue_id, []).append(actor.id)

    # Also check clues that have actor IDs in their source or thread IDs matching actor IDs
    for clue in (definition.clues or []):
        cid = clue.id
        # If clue id contains an actor id fragment, link it
        for actor in (definition.actors or []):
            actor_fragment = actor.id.replace("actor_", "").replace("npc_", "")
            if actor_fragment and actor_fragment in cid:
                clue_actor_map.setdefault(cid, [])
                if actor.id not in clue_actor_map[cid]:
                    clue_actor_map[cid].append(actor.id)

    changed = []
    seen_actors = set()
    for clue_id in newly_discovered_clue_ids:
        for actor_id in clue_actor_map.get(clue_id, []):
            if actor_id in seen_actors:
                continue
            seen_actors.add(actor_id)
            new_pressure = increment_pressure(actor_id, 1, definition, runtime_state)
            changed.append((actor_id, new_pressure))

    return changed


def build_npc_pressure_context(
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> str:
    """
    Build a compact context block describing current NPC behavior for injection
    into the master turn prompt. Only includes NPCs with non-trivial pressure
    or non-default behavior.
    """
    if not definition or not definition.actors:
        return ""

    lines = []
    for actor in definition.actors:
        entry = _actor_entry(runtime_state, actor.id)
        base_pressure = int(getattr(actor, "agenda_pressure", 0) or 0)
        current_pressure = int(entry.get("pressure", base_pressure))
        band = _pressure_band(current_pressure)

        pressure_response = getattr(actor, "pressure_response", {}) or {}
        if not pressure_response:
            continue

        behavior = pressure_response.get(band) or pressure_response.get("low") or ""
        if not behavior:
            continue

        # Only inject if pressure is non-trivial OR actor is antagonist/villain
        role = getattr(actor, "role", "neutral") or "neutral"
        is_antagonist = role in ("villain", "antagonist")
        if current_pressure < 1 and not is_antagonist:
            continue

        band_label = {"low": "tranquillo", "medium": "allertato", "high": "in movimento", "extreme": "disperato"}[band]
        lines.append(
            f"- {actor.name} [pressione {current_pressure}/10 — {band_label}]: {behavior}"
        )

    if not lines:
        return ""

    return "\nSTATO NPC (comportamento attuale):\n" + "\n".join(lines)
