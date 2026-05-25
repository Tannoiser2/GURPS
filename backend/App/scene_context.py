"""Scene-aware visibility helpers.

Pure functions that filter a compiled adventure runtime down to what is
*actually present* in the player's current scene. Today's compile produces
typed clues, actor agendas and location metadata that already carry the
relationship info (``clue.source_location``, ``actor.location_id``,
``state.current_scene_id``) but no shared utility consumes it — every caller
duplicates ad-hoc matching, and most don't filter at all.

This module gives the rest of the pipeline three functions:

    visible_clues_at(runtime, definition, scene_id) -> list[RuntimeClue]
    present_actors_at(runtime, definition, scene_id) -> list[ActorState]
    actions_for_scene(runtime, definition, scene_id) -> list[dict]

The match is forgiving: case-insensitive, whitespace-collapsed, and tolerant
of prefix/suffix wrapping that occurs when the LLM tags a clue with a wider
name than the canonical location id (e.g. ``"Torre - Stanza 4"`` matches a
location named ``"Stanza 4"``).
"""
from __future__ import annotations

from typing import Iterable

from .runtime_models import (
    ActorState,
    AdventureDefinition,
    AdventureRuntimeState,
    LocationState,
    RuntimeClue,
)


_VERB_TEMPLATES = {
    "physical_evidence": "Esaminare",
    "document": "Leggere",
    "testimony": "Interrogare su",
    "scene_observation": "Osservare attentamente",
    "forensic": "Analizzare",
    "contradiction": "Confrontare le versioni di",
}


def _norm(value: str | None) -> str:
    return " ".join(str(value or "").lower().split())


def _scene_aliases(definition: AdventureDefinition, scene_id: str) -> set[str]:
    """All the names a clue / actor might use to reference this scene.

    The compiler stores three kinds of identifiers per location (``id``,
    ``name``, ``original_section``) and the LLM extractors tend to use
    ``name`` while regex extraction tends to keep ``id``. We accept both
    plus a normalised form.
    """
    aliases: set[str] = set()
    if not scene_id:
        return aliases
    aliases.add(_norm(scene_id))
    for loc in definition.locations:
        if loc.id != scene_id and loc.name != scene_id:
            continue
        for value in (loc.id, loc.name, loc.original_section):
            normalised = _norm(value)
            if normalised:
                aliases.add(normalised)
    return aliases


def _matches_scene(candidate: str, aliases: set[str]) -> bool:
    norm = _norm(candidate)
    if not norm or not aliases:
        return False
    if norm in aliases:
        return True
    # Forgiving match: any alias appears as a substring of candidate or
    # vice-versa. Catches "Torre - Stanza 4" ↔ "Stanza 4" cases.
    for alias in aliases:
        if alias and (alias in norm or norm in alias):
            return True
    return False


def visible_clues_at(
    runtime: AdventureRuntimeState | None,
    definition: AdventureDefinition,
    scene_id: str | None = None,
) -> list[RuntimeClue]:
    """Return clues whose ``source_location`` matches the current scene.

    A clue with empty ``source_location`` is treated as *global* and shown
    everywhere — the alternative (hide forever) would be worse for legacy
    compiled adventures.
    """
    target = scene_id or (runtime.current_scene_id if runtime else None)
    if not target:
        return list(definition.clues)
    aliases = _scene_aliases(definition, target)
    out: list[RuntimeClue] = []
    for clue in definition.clues:
        if not clue.source_location:
            out.append(clue)
            continue
        if _matches_scene(clue.source_location, aliases):
            out.append(clue)
    return out


def present_actors_at(
    runtime: AdventureRuntimeState | None,
    definition: AdventureDefinition,
    scene_id: str | None = None,
) -> list[ActorState]:
    """Return actors whose ``location_id`` matches the current scene.

    Actors without a location are treated as off-stage and excluded — unlike
    clues, off-stage NPCs should not show up automatically.
    """
    target = scene_id or (runtime.current_scene_id if runtime else None)
    if not target:
        return list(definition.actors)
    aliases = _scene_aliases(definition, target)
    return [a for a in definition.actors if a.location_id and _matches_scene(a.location_id, aliases)]


def current_location(
    definition: AdventureDefinition,
    scene_id: str | None,
) -> LocationState | None:
    if not scene_id:
        return definition.locations[0] if definition.locations else None
    for loc in definition.locations:
        if loc.id == scene_id or loc.name == scene_id:
            return loc
    aliases = _scene_aliases(definition, scene_id)
    for loc in definition.locations:
        if _matches_scene(loc.id, aliases) or _matches_scene(loc.name, aliases):
            return loc
    return None


def actions_for_scene(
    runtime: AdventureRuntimeState | None,
    definition: AdventureDefinition,
    scene_id: str | None = None,
    *,
    max_actions: int = 8,
) -> list[dict]:
    """Build a player-facing action list grounded in the current scene.

    Each entry has ``label``, ``kind`` (clue/actor/move/explore), and the
    underlying ``target_id`` so the runtime can link back to a real clue or
    actor when the player picks it. Actions are sourced in priority order:

    1. ``clue.possible_actions[0]`` for each visible clue (full LLM-generated
       phrasing — already verbose and idiomatic).
    2. ``"Avvicinare {actor.name}: <goal hint>"`` for each present actor.
    3. ``"Spostarsi verso {exit_loc.name}"`` for known exits.
    4. ``"Esplora attivamente {scene.name}"`` as a fallback when nothing
       else surfaces — never let the action list be empty.
    """
    target = scene_id or (runtime.current_scene_id if runtime else None)
    scene = current_location(definition, target)
    out: list[dict] = []

    for clue in visible_clues_at(runtime, definition, target):
        if clue.state == "discovered" or clue.state == "spent":
            continue
        label: str = ""
        if clue.possible_actions:
            label = str(clue.possible_actions[0]).strip()
        if not label:
            verb = _VERB_TEMPLATES.get(clue.type, "Indagare su")
            label = f"{verb} {clue.label}".strip()
        out.append({
            "label": label[:160],
            "kind": "clue",
            "target_id": clue.id,
            "skill_hint": _skill_hint_for_clue_type(clue.type),
        })
        if len(out) >= max_actions:
            return out

    for actor in present_actors_at(runtime, definition, target):
        if actor.status in {"dead", "captured", "resolved"}:
            continue
        hint = (actor.goal or actor.secret or "").strip()
        suffix = f": {hint[:60]}" if hint else ""
        out.append({
            "label": f"Avvicinare {actor.name}{suffix}",
            "kind": "actor",
            "target_id": actor.id,
            "skill_hint": "Diplomacy" if actor.role in {"ally", "patron", "witness"} else "Intimidation",
        })
        if len(out) >= max_actions:
            return out

    if scene:
        for exit_name in (scene.exits or [])[:3]:
            target_loc = next(
                (l for l in definition.locations if l.name == exit_name or l.id == exit_name),
                None,
            )
            label_target = target_loc.name if target_loc else exit_name
            out.append({
                "label": f"Spostarsi verso {label_target}",
                "kind": "move",
                "target_id": target_loc.id if target_loc else exit_name,
                "skill_hint": None,
            })
            if len(out) >= max_actions:
                return out

    if not out and scene:
        out.append({
            "label": f"Esplora attivamente {scene.name}",
            "kind": "explore",
            "target_id": scene.id,
            "skill_hint": "Observation",
        })

    return out


def _skill_hint_for_clue_type(clue_type: str) -> str | None:
    return {
        "physical_evidence": "Observation",
        "document": "Research",
        "testimony": "Diplomacy",
        "scene_observation": "Observation",
        "forensic": "Forensics",
        "contradiction": "Detect Lies",
    }.get(clue_type)


__all__ = [
    "visible_clues_at",
    "present_actors_at",
    "actions_for_scene",
    "current_location",
]
