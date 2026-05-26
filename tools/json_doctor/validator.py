"""
Schema validation for adventure JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple


REQUIRED_TOP_LEVEL = ["id", "title", "genre", "actors", "locations", "clues", "event_clocks"]
ACTOR_REQUIRED = ["id", "name", "role"]
CLOCK_REQUIRED = ["id", "label", "max_value"]
CLUE_REQUIRED = ["id", "label", "type"]
LOCATION_REQUIRED = ["id", "name"]


def _unwrap(data: dict) -> dict:
    """Extract adventure_definition if the file uses the compiled wrapper format."""
    if "adventure_definition" in data:
        return data["adventure_definition"]
    return data


def validate_file(path: Path) -> Tuple[bool, List[str]]:
    """
    Validate a single adventure JSON file.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # 1. Parse JSON
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON non valido: {e}"]
    except Exception as e:
        return False, [f"Errore lettura file: {e}"]

    data = _unwrap(raw)

    # 2. Top-level required fields
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Campo mancante: '{field}'")

    # 3. Actors
    for i, actor in enumerate(data.get("actors", [])):
        for field in ACTOR_REQUIRED:
            if field not in actor:
                errors.append(f"actors[{i}]: campo '{field}' mancante")

    # 4. Clocks
    for i, clock in enumerate(data.get("event_clocks", [])):
        for field in CLOCK_REQUIRED:
            if field not in clock:
                errors.append(f"event_clocks[{i}]: campo '{field}' mancante")
        max_val = clock.get("max_value", 0)
        if not isinstance(max_val, int) or max_val <= 0:
            errors.append(f"event_clocks[{i}]: max_value deve essere intero positivo")

    # 5. Clues
    for i, clue in enumerate(data.get("clues", [])):
        for field in CLUE_REQUIRED:
            if field not in clue:
                errors.append(f"clues[{i}]: campo '{field}' mancante")

    # 6. Locations
    for i, loc in enumerate(data.get("locations", [])):
        for field in LOCATION_REQUIRED:
            if field not in loc:
                errors.append(f"locations[{i}]: campo '{field}' mancante")

    # 7. ID uniqueness
    actor_ids = [a.get("id") for a in data.get("actors", []) if "id" in a]
    if len(actor_ids) != len(set(actor_ids)):
        errors.append("ID duplicati in actors")

    clue_ids = [c.get("id") for c in data.get("clues", []) if "id" in c]
    if len(clue_ids) != len(set(clue_ids)):
        errors.append("ID duplicati in clues")

    return len(errors) == 0, errors
