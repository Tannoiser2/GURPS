from __future__ import annotations

from .escalation_limiter import classify_event_tier, downgrade_event_to_allowed_tier
from .genre_constraints import get_genre_profile, is_escalation_allowed


def merge_engine_and_ai_updates(engine_updates: dict | None, ai_updates: dict | None) -> dict:
    """Gli update deterministici del motore hanno precedenza; l'AI puo solo aggiungere campi validati dopo."""
    engine_updates = engine_updates or {}
    ai_updates = ai_updates or {}
    merged = dict(ai_updates)
    list_merge_keys = [
        "clue_progress",
        "clues_found",
        "npc_updates",
        "closed_threads",
        "location_access",
        "objective_updates",
        "revelation_updates",
        "actor_updates",
        "faction_updates",
        "clock_updates",
        "pressure_updates",
        "resource_updates",
        "finale_updates",
        "truth_updates",
    ]
    for key in list_merge_keys:
        values = []
        for item in (engine_updates.get(key) or []) + (ai_updates.get(key) or []):
            if item not in values:
                values.append(item)
        merged[key] = values
    merged["new_threads"] = []
    merged["threat_increase"] = max(int(engine_updates.get("threat_increase") or 0), int(ai_updates.get("threat_increase") or 0))
    merged["objective_progress"] = max(int(engine_updates.get("objective_progress") or 0), int(ai_updates.get("objective_progress") or 0))
    for key, value in engine_updates.items():
        if key not in merged or key in {"activate_combat", "combat_over", "story_over", "victory"} and value:
            merged[key] = value
    return merged


def validate_ai_state_updates(
    updates: dict | None,
    *,
    director_decision: dict | None = None,
    genre_profile: dict | None = None,
    prerolled: dict | None = None,
    narrative_text: str = "",
    finale_condition_met: bool = False,
) -> dict:
    """Applica l'autorita del Director: il renderer non puo superare il tier concesso."""
    su = dict(updates or {})
    director_decision = director_decision or {}
    profile = genre_profile or director_decision.get("genre_profile") or get_genre_profile(
        [director_decision.get("runtime_profile")] if director_decision.get("runtime_profile") else [],
        None,
    )
    allowed_tier = int(director_decision.get("allowed_escalation_tier", profile.get("max_default_tier", 4)) or 3)
    allowed_types = list(director_decision.get("allowed_escalation_types") or profile.get("allowed_escalations") or [])
    forbidden_types = list(director_decision.get("forbidden_escalation_types") or profile.get("forbidden_escalations") or [])

    blocked: list[str] = list(su.get("blocked_major_events") or su.get("blocked_state_updates") or [])
    downgraded: list[dict] = list(su.get("downgraded_events") or [])
    proposed_tier = classify_event_tier(su, narrative_text)
    roll_intent = str((prerolled or {}).get("intent") or "").lower()
    passive_action = bool((prerolled or {}).get("non_combat_action")) or roll_intent in {
        "investigation", "observation", "technical", "medical", "social", "stealth", "survival", "generic"
    }
    explicit_trigger = bool(su.get("explicit_trigger") or su.get("finale_condition_met") or director_decision.get("explicit_trigger"))
    director_authorized_major = bool(director_decision.get("director_authorization") or director_decision.get("authorized_major_event"))
    completed_clock = bool(director_decision.get("clock_triggers"))
    terminal_allowed = bool(finale_condition_met or su.get("finale_condition_met") or explicit_trigger or completed_clock)

    raw_event = " ".join(str(x) for x in [su.get("major_event"), su.get("major_events"), narrative_text]).lower()
    forbidden_hit = next((term for term in forbidden_types if str(term).lower() and str(term).lower() in raw_event), "")
    if forbidden_hit or not is_escalation_allowed(raw_event, profile):
        blocked.append(forbidden_hit or "forbidden_genre_event")

    if proposed_tier > allowed_tier:
        blocked.append(f"tier_{proposed_tier}_over_allowed_{allowed_tier}")
    if proposed_tier >= 5 and not director_authorized_major and not explicit_trigger and not completed_clock:
        blocked.append("major_event_without_director_authorization")
    if proposed_tier >= 6 and not terminal_allowed:
        blocked.append("terminal_event_without_finale_condition")
    if passive_action and proposed_tier >= 6 and not terminal_allowed:
        blocked.append("passive_action_terminal_event")

    if blocked:
        replacement = downgrade_event_to_allowed_tier(su.get("major_event") or blocked, min(allowed_tier, 4), profile)
        su["story_over"] = False
        su["victory"] = False
        su["major_event"] = None
        su["major_events"] = []
        if "activate_combat" in replacement:
            su["activate_combat"] = bool(replacement.get("activate_combat"))
            su["combat_scene"] = replacement.get("combat_scene")
        su["threat_increase"] = max(int(su.get("threat_increase") or 0), int(replacement.get("threat_increase") or 0))
        if "objective_progress" in replacement:
            su["objective_progress"] = max(int(su.get("objective_progress") or 0), int(replacement["objective_progress"]))
        downgraded.extend(replacement.get("downgraded_events") or [])
        su["needs_alternative_narration"] = True
        su["narration_constraints"] = "Evento fuori tier o fuori genere: renderizzare solo una conseguenza entro il tier concesso."

    su["allowed_escalation_tier"] = allowed_tier
    su["allowed_escalation_types"] = allowed_types
    su["forbidden_escalation_types"] = forbidden_types
    su["blocked_major_events"] = sorted({str(x) for x in blocked if str(x).strip()})
    su["downgraded_events"] = downgraded
    su["director_reason"] = director_decision.get("reason") or director_decision.get("scene_directive") or ""
    return su


def validate_runtime_integrity(adventure: dict) -> list[str]:
    warnings: list[str] = []
    thread_ids = {str(t.get("id")) for t in adventure.get("story_threads", []) if isinstance(t, dict) and t.get("id")}
    for clue in adventure.get("clues", []) or []:
        if isinstance(clue, dict) and clue.get("thread_id") and clue.get("thread_id") not in thread_ids:
            warnings.append(f"clue {clue.get('id')} references missing thread {clue.get('thread_id')}")
    if not adventure.get("adventure_canon"):
        warnings.append("missing adventure_canon")
    return warnings
