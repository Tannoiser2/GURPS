from __future__ import annotations

from typing import Any

from .narrative_archetypes import ARCHETYPE_LIBRARY, get_archetype


def _score_candidate(archetype: str, features: dict[str, Any]) -> float:
    score = 0.0
    if archetype == "room_keyed_dungeon":
        score += min(0.7, (features.get("room_count", 0) / 10) * 0.7)
        score += 0.2 if features.get("has_dungeon") else 0
    if archetype == "investigation_graph":
        score += min(0.6, (features.get("clue_count", 0) / 8) * 0.6)
        score += 0.2 if features.get("has_investigation") else 0
    if archetype == "faction_sandbox":
        score += min(0.7, (features.get("faction_density", 0) / 3) * 0.7)
        score += 0.2 if features.get("has_sandbox") else 0
    if archetype == "heist":
        score += 0.75 if features.get("has_heist") else 0
    if archetype == "survival_escape":
        score += 0.65 if features.get("has_survival") else 0
    if archetype == "military_operation":
        score += 0.75 if features.get("has_military") else 0
    if archetype == "horror_survival":
        score += 0.55 if features.get("has_horror") else 0
    if archetype == "romance_drama":
        score += 0.65 if features.get("has_romance") else 0
    if archetype == "ritual_countdown":
        score += 0.65 if features.get("has_ritual") else 0
    if archetype == "wilderness_sandbox":
        score += 0.65 if features.get("has_wilderness") else 0
    return min(0.98, score)


def rank_archetype_candidates(features: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for archetype_id in ARCHETYPE_LIBRARY:
        score = _score_candidate(archetype_id, features)
        if score > 0:
            candidates.append({"id": archetype_id, "score": round(score, 2)})
    if not candidates:
        candidates.append({"id": "investigation_graph", "score": 0.5})
    return sorted(candidates, key=lambda c: c["score"], reverse=True)


def merge_archetypes(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    primary = candidates[0] if candidates else {"id": "investigation_graph", "score": 0.5}
    secondary = [c["id"] for c in candidates[1:4] if c["score"] >= 0.35]
    archetype = get_archetype(primary["id"])
    return {
        "primary_archetype": primary["id"],
        "secondary_archetypes": secondary,
        "confidence": primary["score"],
        "reason": f"Matched runtime signals for {primary['id']}",
        "definition": archetype,
    }


def detect_archetypes_from_pdf_structure(source_mode: str, extracted_structure: dict[str, Any], genre: str = "", text_features: dict | None = None) -> dict[str, Any]:
    detected = (extracted_structure or {}).get("detected_structure") or {}
    counts = (extracted_structure or {}).get("counts") or {}
    blob = f"{genre} {text_features or ''}".lower()
    features = {
        "room_count": counts.get("rooms", 0),
        "clue_count": counts.get("clues", 0),
        "faction_density": 3 if detected.get("has_factions") else 0,
        "combat_density": counts.get("encounters", 0),
        "has_dungeon": detected.get("has_dungeon"),
        "has_investigation": detected.get("has_investigation"),
        "has_wilderness": detected.get("has_wilderness"),
        "has_heist": detected.get("has_heist"),
        "has_military": detected.get("has_military"),
        "has_sandbox": detected.get("has_sandbox"),
        "has_survival": any(w in blob for w in ("survival", "fuga", "escape")),
        "has_horror": any(w in blob for w in ("horror", "mystery", "malediz", "paura")),
        "has_romance": "romance" in blob,
        "has_ritual": any(w in blob for w in ("ritual", "rituale", "altare")),
    }
    ranked = rank_archetype_candidates(features)
    result = merge_archetypes(ranked)
    if source_mode in {"pdf_import", "pdf_import_fallback"}:
        result["structure_authority"] = "label_only_do_not_compress"
    return result


def detect_archetypes_from_ai_prompt(text: str, genre: str = "") -> dict[str, Any]:
    low = f"{text or ''} {genre or ''}".lower()
    features = {
        "room_count": 0,
        "clue_count": 3 if any(w in low for w in ("mistero", "indagine", "clue", "indizi")) else 0,
        "faction_density": 3 if any(w in low for w in ("fazioni", "politic", "gilda")) else 0,
        "has_dungeon": any(w in low for w in ("dungeon", "cripta", "catacomb")),
        "has_investigation": any(w in low for w in ("mistero", "indagine", "detective")),
        "has_wilderness": any(w in low for w in ("viaggio", "foresta", "wilderness")),
        "has_heist": any(w in low for w in ("heist", "furto", "colpo")),
        "has_military": any(w in low for w in ("military", "militare", "ww2", "operazione")),
        "has_sandbox": any(w in low for w in ("sandbox", "fazioni")),
        "has_survival": any(w in low for w in ("survival", "sopravviv", "fuga")),
        "has_horror": any(w in low for w in ("horror", "paura", "maledizione")),
        "has_romance": any(w in low for w in ("romance", "amore", "relazione")),
        "has_ritual": any(w in low for w in ("ritual", "rituale")),
    }
    return merge_archetypes(rank_archetype_candidates(features))
