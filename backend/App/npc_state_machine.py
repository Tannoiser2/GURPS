"""
NPC State Machine — tracks agenda_pressure per NPC and resolves current behavior.

Pressure is incremented when clues about an NPC are discovered.
The current behavior band is injected as a small context block into the master turn prompt.

pressure_events in ActorState define deterministic actions that fire when
pressure crosses a threshold:
  - destroy_clue   : marks a clue as destroyed, optionally creates a replacement
  - move_clue      : moves a clue to a new location (NPC fled, left things behind)
  - eliminate_npc  : sets another NPC status to dead/missing, optionally creates evidence
  - scare_npc      : marks another NPC as hostile/uncooperative
  - create_clue    : injects a brand-new clue into the adventure
"""

from typing import Any, Dict, List, Optional, Tuple
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
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Increment pressure for an NPC.
    Returns (new_pressure, fired_events).
    """
    actor_def = next((a for a in (definition.actors or []) if a.id == actor_id), None)
    if not actor_def:
        return 0, []

    entry = _actor_entry(runtime_state, actor_id)
    base_pressure = int(getattr(actor_def, "agenda_pressure", 0) or 0)
    old_pressure = int(entry.get("pressure", base_pressure))
    new_pressure = min(old_pressure + delta, 10)
    entry["pressure"] = new_pressure
    runtime_state.actor_runtime[actor_id] = entry

    fired = fire_pressure_events(actor_id, old_pressure, new_pressure, definition, runtime_state)
    return new_pressure, fired


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
    all_fired_events = []
    seen_actors = set()
    for clue_id in newly_discovered_clue_ids:
        for actor_id in clue_actor_map.get(clue_id, []):
            if actor_id in seen_actors:
                continue
            seen_actors.add(actor_id)
            new_pressure, fired = increment_pressure(actor_id, 1, definition, runtime_state)
            changed.append((actor_id, new_pressure))
            all_fired_events.extend(fired)

    return changed, all_fired_events


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


# ─────────────────────────────────────────────
# Pressure events execution
# ─────────────────────────────────────────────

def _already_triggered(event: dict, runtime_state: AdventureRuntimeState, event_key: str) -> bool:
    return bool((runtime_state.flags or {}).get(f"pe_triggered_{event_key}"))


def _mark_triggered(event: dict, runtime_state: AdventureRuntimeState, event_key: str) -> None:
    runtime_state.flags[f"pe_triggered_{event_key}"] = True


def fire_pressure_events(
    actor_id: str,
    old_pressure: int,
    new_pressure: int,
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> List[Dict[str, Any]]:
    """
    Check if any pressure_events on the actor should fire given the pressure increase.
    Executes them and returns a list of fired event dicts (for logging and frontend notification).
    """
    actor_def = next((a for a in (definition.actors or []) if a.id == actor_id), None)
    if not actor_def:
        return []

    events = getattr(actor_def, "pressure_events", []) or []
    fired = []

    for i, event in enumerate(events):
        threshold = int(event.get("at_pressure", 999))
        if not (old_pressure < threshold <= new_pressure):
            continue

        event_key = f"{actor_id}_{i}_{threshold}"
        if _already_triggered(event, runtime_state, event_key):
            continue

        action = event.get("action", "")
        result = _execute_event(action, event, actor_id, definition, runtime_state)
        if result is not None:
            _mark_triggered(event, runtime_state, event_key)
            fired.append({
                "actor_id": actor_id,
                "actor_name": actor_def.name,
                "action": action,
                "at_pressure": threshold,
                "narration": event.get("narration", ""),
                **result,
            })
            print(f"[npc_event] {actor_def.name} @ p{threshold}: {action} → {result}")

    return fired


def _execute_event(
    action: str,
    event: dict,
    source_actor_id: str,
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> Optional[Dict[str, Any]]:
    """Execute a single pressure event. Returns a result dict or None on failure."""

    if action == "destroy_clue":
        clue_id = event.get("clue_id", "")
        if not clue_id:
            return None
        if clue_id not in runtime_state.destroyed_clue_ids:
            runtime_state.destroyed_clue_ids.append(clue_id)
        # Remove from partial/discovered so it's treated as gone
        if clue_id in runtime_state.partial_clue_ids:
            runtime_state.partial_clue_ids.remove(clue_id)
        result: Dict[str, Any] = {"destroyed_clue_id": clue_id}
        # Inject replacement clue if provided
        replacement = event.get("replacement_clue")
        if replacement and isinstance(replacement, dict) and replacement.get("id"):
            replacement["_injected"] = True
            replacement.setdefault("state", "available")
            replacement.setdefault("type", "physical_evidence")
            if not any(c.get("id") == replacement["id"] for c in runtime_state.injected_clues):
                runtime_state.injected_clues.append(replacement)
            result["replacement_clue_id"] = replacement["id"]
        return result

    if action == "move_clue":
        clue_id = event.get("clue_id", "")
        new_location = event.get("new_location", "")
        if not clue_id:
            return None
        # Find the clue in definition and record location override in flags
        runtime_state.flags[f"clue_location_{clue_id}"] = new_location
        return {"moved_clue_id": clue_id, "new_location": new_location}

    if action == "eliminate_npc":
        target_id = event.get("target_id", "")
        if not target_id:
            return None
        entry = dict((runtime_state.actor_runtime or {}).get(target_id) or {})
        new_status = event.get("new_status", "dead")
        entry["status"] = new_status
        runtime_state.actor_runtime[target_id] = entry
        result = {"eliminated_npc_id": target_id, "new_status": new_status}
        # Inject evidence clue
        evidence = event.get("creates_clue")
        if evidence and isinstance(evidence, dict) and evidence.get("id"):
            evidence["_injected"] = True
            evidence.setdefault("state", "available")
            evidence.setdefault("type", "physical_evidence")
            if not any(c.get("id") == evidence["id"] for c in runtime_state.injected_clues):
                runtime_state.injected_clues.append(evidence)
            result["evidence_clue_id"] = evidence["id"]
        return result

    if action == "scare_npc":
        target_id = event.get("target_id", "")
        if not target_id:
            return None
        entry = dict((runtime_state.actor_runtime or {}).get(target_id) or {})
        entry["attitude"] = event.get("new_attitude", "hostile")
        entry["scared_by"] = source_actor_id
        runtime_state.actor_runtime[target_id] = entry
        return {"scared_npc_id": target_id, "new_attitude": entry["attitude"]}

    if action == "create_clue":
        new_clue = event.get("clue", {})
        if not new_clue or not new_clue.get("id"):
            return None
        new_clue["_injected"] = True
        new_clue.setdefault("state", "available")
        new_clue.setdefault("type", "physical_evidence")
        if not any(c.get("id") == new_clue["id"] for c in runtime_state.injected_clues):
            runtime_state.injected_clues.append(new_clue)
        return {"created_clue_id": new_clue["id"]}

    return None
