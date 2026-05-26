"""
Clock Engine — advances event clocks based on roll outcomes and returns triggered events.
"""

from typing import Any, Dict, List, Optional, Tuple
from .runtime_models import AdventureDefinition, AdventureRuntimeState, EventClock


def _clock_entry(runtime_state: AdventureRuntimeState, clock_id: str) -> dict:
    return dict((runtime_state.clock_runtime or {}).get(clock_id) or {})


def _is_active(clock: EventClock, entry: dict) -> bool:
    if entry.get("resolved") or getattr(clock, "resolved", False):
        return False
    return bool(entry.get("active", clock.active))


def _ticks_for_outcome(clock: EventClock, outcome: str) -> int:
    """Return how many ticks this outcome adds to the clock."""
    outcome_low = (outcome or "").lower()
    if "fallimento" in outcome_low:
        return int(getattr(clock, "ticks_per_failure", 1) or 1)
    if "parziale" in outcome_low or "stretta misura" in outcome_low:
        return int(getattr(clock, "ticks_per_partial", 0) or 0)
    # success / critical — clock doesn't advance
    return int(getattr(clock, "ticks_per_success", 0) or 0)


def _steps_crossed(clock: EventClock, old_val: int, new_val: int) -> List[Dict]:
    """Return step dicts whose value threshold was crossed going from old_val to new_val."""
    crossed = []
    for step in (clock.steps or []):
        threshold = step.get("value") if isinstance(step, dict) else getattr(step, "value", None)
        if threshold is None:
            continue
        if old_val < threshold <= new_val:
            crossed.append(step if isinstance(step, dict) else step.__dict__)
    return crossed


def tick_clocks(
    outcome: str,
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Advance all active clocks based on the roll outcome.

    Returns:
      (clock_events, updated_clock_entries)
      - clock_events: list of {clock_id, label, old_value, new_value, steps_crossed, completed}
      - updated_clock_entries: list of {id, entry_dict} to persist in clock_runtime
    """
    if not definition or not definition.event_clocks:
        return [], []

    clock_events: List[Dict] = []
    updates: List[Dict] = []

    for clock in definition.event_clocks:
        entry = _clock_entry(runtime_state, clock.id)
        if not _is_active(clock, entry):
            continue

        ticks = _ticks_for_outcome(clock, outcome)
        if ticks == 0:
            continue

        old_val = int(entry.get("value") or 0)
        raw_new = old_val + ticks
        max_val = int(clock.max_value or 8)
        new_val = min(raw_new, max_val)

        if new_val == old_val:
            continue

        stepped = _steps_crossed(clock, old_val, new_val)
        completed = new_val >= max_val

        # Mark as discovered if it wasn't
        if not entry.get("discovered") and not clock.discovered:
            entry["discovered"] = True

        entry["value"] = new_val
        if completed:
            entry["resolved"] = False   # completed ≠ resolved (resolved = players stopped it)
            entry["completed"] = True

        updates.append({"id": clock.id, "entry": entry})

        clock_events.append({
            "clock_id": clock.id,
            "label": clock.label,
            "clock_type": getattr(clock, "clock_type", "narrative") or "narrative",
            "old_value": old_val,
            "new_value": new_val,
            "max_value": max_val,
            "steps_crossed": stepped,
            "completed": completed,
            "consequence": clock.consequence or "",
            "on_complete": getattr(clock, "on_complete", "") or "",
        })

    # Persist updates into runtime_state
    for u in updates:
        runtime_state.clock_runtime[u["id"]] = u["entry"]

    return clock_events, updates


def resolve_clock(
    clock_id: str,
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> bool:
    """Mark a clock as resolved (players stopped it in time). Returns True if found."""
    for clock in (definition.event_clocks or []):
        if clock.id == clock_id:
            entry = _clock_entry(runtime_state, clock_id)
            entry["resolved"] = True
            entry["active"] = False
            runtime_state.clock_runtime[clock_id] = entry
            return True
    return False


def format_clock_event_narrative(event: Dict) -> str:
    """Return a short GM-facing string describing what just happened to a clock."""
    label = event.get("label", "Clock")
    new_val = event.get("new_value", 0)
    max_val = event.get("max_value", 8)

    if event.get("completed"):
        consequence = event.get("consequence") or event.get("on_complete") or "conseguenze gravi"
        return f"⚠ CLOCK COMPLETATO: {label} ({new_val}/{max_val}) → {consequence}"

    parts = [f"↑ {label}: {new_val}/{max_val}"]
    for step in event.get("steps_crossed", []):
        effect = step.get("effect") or step.get("world_state_change") or step.get("scene_prompt") or step.get("label") or ""
        if effect:
            parts.append(f"  → {effect}")
    return "\n".join(parts)
