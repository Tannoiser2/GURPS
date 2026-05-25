from __future__ import annotations

from copy import deepcopy


DEFAULT_ALLOWED = [
    "atmosphere",
    "minor_complication",
    "cost_or_delay",
    "pressure_increase",
    "partial_clue",
    "npc_suspicion",
    "enemy_alerted",
    "danger_scene",
]

DEFAULT_FORBIDDEN = [
    "apocalypse",
    "world ending",
    "world_destroyed",
    "black sun",
    "cosmic doom",
    "city destroyed",
    "region permanently doomed",
    "untriggered game over",
    "party_death",
    "boss_release",
    "finale without conditions",
    "genre_shift",
]

GENRE_PROFILES: dict[str, dict] = {
    "investigation_graph": {
        "id": "investigation_graph",
        "tone": "mystery investigation",
        "max_default_tier": 4,
        "allowed_escalations": [
            "witness disappears",
            "suspect lies",
            "new contradiction",
            "pressure clock advances",
            "partial clue",
            "false lead",
            "social fallout",
            "enemy alerted",
        ],
        "forbidden_escalations": [
            "mystery solved before threshold",
            "villain revealed without clue threshold",
            "case ends from one failed roll",
            "untriggered massacre",
            *DEFAULT_FORBIDDEN,
        ],
    },
    "ritual_dungeon": {
        "id": "ritual_dungeon",
        "tone": "dark fantasy dungeon",
        "max_default_tier": 5,
        "allowed_escalations": [
            "trap activation",
            "guardian attack",
            "ritual clock advances",
            "boss signs awaken",
            "room changes state",
            "curse intensifies",
            "danger scene",
        ],
        "forbidden_escalations": [
            "boss fully awakens without trigger",
            "ritual completes without clock",
            "party death cutscene",
            "finale without conditions",
            *DEFAULT_FORBIDDEN,
        ],
    },
    "survival_escape": {
        "id": "survival_escape",
        "tone": "survival pressure",
        "max_default_tier": 4,
        "allowed_escalations": [
            "resource loss",
            "route blocked",
            "hunter gains distance",
            "injury",
            "weather worsens",
            "safe node compromised",
            "pressure increase",
        ],
        "forbidden_escalations": [
            "instant death without direct lethal risk",
            "escape impossible from one failure",
            "entire map destroyed without clock",
            *DEFAULT_FORBIDDEN,
        ],
    },
    "false_monster_investigation": {
        "id": "false_monster_investigation",
        "tone": "dark fantasy investigation",
        "max_default_tier": 4,
        "allowed_escalations": [
            "public panic",
            "false accusation",
            "targeted murder",
            "ambush",
            "chase",
            "NPC betrayal",
            "wolf attack",
            "orc encounter",
            "social suspicion",
            "clue loss with alternate path",
        ],
        "forbidden_escalations": [
            "apocalypse",
            "black sun",
            "world ending",
            "cosmic resurrection",
            "city destroyed",
            "region permanently doomed",
            "untriggered game over",
            *DEFAULT_FORBIDDEN,
        ],
    },
}

GENRE_KEYWORDS: dict[str, dict] = {
    "fantasy": {
        "id": "fantasy",
        "tone": "fantasy adventure",
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["ambush", "chase", "guardian attack", "curse intensifies"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["sci-fi genre shift", "cosmic apocalypse without trigger"],
    },
    "mystery_horror": {
        "id": "mystery_horror",
        "tone": "mystery horror",
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["fear spike", "witness panic", "haunting sign"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["cosmic finale without clues", "monster truth revealed too early"],
    },
    "sci_fi": {
        "id": "sci_fi",
        "tone": "science fiction",
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["system alert", "decompression warning", "security response"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["magic genre shift", "planet destroyed without clock"],
    },
    "ww2": {
        "id": "ww2",
        "tone": "war drama",
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["patrol alerted", "shelling nearby", "route compromised"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["supernatural apocalypse without canon"],
    },
    "detective_classico": {
        "id": "detective_classico",
        "tone": "classic detective",
        "max_default_tier": 3,
        "allowed_escalations": DEFAULT_ALLOWED + ["suspect lies", "alibi pressure", "evidence contested"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["massacre from one roll", "villain revealed without evidence"],
    },
}

TERMINAL_REQUIREMENTS = ["finale_condition", "completed_clock", "explicit_trigger", "director_authorization"]


def get_genre_profile(runtime_profiles: list[str] | str | None = None, genre: str | None = None) -> dict:
    profiles = [runtime_profiles] if isinstance(runtime_profiles, str) else list(runtime_profiles or [])
    merged = {
        "id": profiles[0] if profiles else (genre or "generic"),
        "tone": "genre-consistent adventure",
        "allowed_escalations": list(DEFAULT_ALLOWED),
        "forbidden_escalations": list(DEFAULT_FORBIDDEN),
        "terminal_events_require": list(TERMINAL_REQUIREMENTS),
        "max_default_tier": 4,
    }
    for key in profiles + ([genre] if genre else []):
        profile = GENRE_PROFILES.get(str(key)) or GENRE_KEYWORDS.get(str(key))
        if not profile:
            continue
        merged["id"] = profile.get("id", merged["id"])
        merged["tone"] = profile.get("tone", merged["tone"])
        merged["max_default_tier"] = min(int(merged.get("max_default_tier", 4)), int(profile.get("max_default_tier", 4)))
        merged["allowed_escalations"] = list(dict.fromkeys(merged["allowed_escalations"] + profile.get("allowed_escalations", [])))
        merged["forbidden_escalations"] = list(dict.fromkeys(merged["forbidden_escalations"] + profile.get("forbidden_escalations", [])))
    return deepcopy(merged)


def get_forbidden_escalations(genre_profile: dict | None) -> list[str]:
    return list((genre_profile or {}).get("forbidden_escalations") or DEFAULT_FORBIDDEN)


def is_escalation_allowed(event_type: str, genre_profile: dict | None) -> bool:
    event = str(event_type or "").lower()
    forbidden = [str(x).lower() for x in get_forbidden_escalations(genre_profile)]
    return not any(term and term in event for term in forbidden)
