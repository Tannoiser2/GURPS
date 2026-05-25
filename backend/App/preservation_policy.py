from __future__ import annotations

from typing import Any


def build_preservation_policy(source_mode: str, extracted_structure: dict[str, Any] | None = None, archetype_profile: dict | None = None) -> dict[str, Any]:
    structure = (extracted_structure or {}).get("detected_structure") or {}
    is_pdf = source_mode in {"pdf_import", "pdf_import_fallback"}
    policy = {
        "preserve_rooms": bool(is_pdf and structure.get("has_room_keys")),
        "preserve_all_clues": bool(is_pdf and structure.get("has_investigation")),
        "preserve_factions": bool(is_pdf and structure.get("has_factions")),
        "preserve_timeline": bool(is_pdf and structure.get("has_timeline")),
        "preserve_encounters": bool(is_pdf and (structure.get("has_dungeon") or structure.get("has_military"))),
        "preserve_random_tables": bool(is_pdf and structure.get("has_random_tables")),
        "preserve_maps": bool(is_pdf),
        "allow_inferred_missing_elements": True,
        "forbid_structural_compression": bool(is_pdf),
        "preserve_original_structure": bool(is_pdf),
        "source_mode": source_mode,
        "reason": "PDF = preserve before shaping" if is_pdf else "AI/raw = archetype before filling",
    }
    if source_mode == "manual_json":
        policy.update({
            "preserve_rooms": True,
            "preserve_all_clues": True,
            "preserve_factions": True,
            "preserve_timeline": True,
            "forbid_structural_compression": True,
            "allow_inferred_missing_elements": False,
            "reason": "manual_json = validate and normalize only",
        })
    return policy


def should_preserve_collection(policy: dict[str, Any], collection: str) -> bool:
    mapping = {
        "rooms": "preserve_rooms",
        "locations": "preserve_rooms",
        "clues": "preserve_all_clues",
        "factions": "preserve_factions",
        "events": "preserve_timeline",
        "encounters": "preserve_encounters",
        "tables": "preserve_random_tables",
    }
    return bool((policy or {}).get(mapping.get(collection, "")))
