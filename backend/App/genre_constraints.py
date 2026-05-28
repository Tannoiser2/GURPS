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
        "tone_instruction": (
            "Registro narrativo: stile sobrio e analitico. "
            "Descrizioni ambientali brevi e precise. "
            "Dialoghi NPC con sottotesti nascosti — l'NPC non dice tutto ciò che sa. "
            "Escalation tramite dettagli incongruenti, non azioni esplosive."
        ),
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
        "tone_instruction": (
            "Registro narrativo: dark fantasy atmosferico. "
            "Aggettivi visivi e sensoriali (pietra umida, luce vacillante, odore di cenere). "
            "Ogni stanza ha un elemento di pericolo latente. "
            "Il soprannaturale è reale e tangibile — non metaforico."
        ),
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
        "tone_instruction": (
            "Registro narrativo: stile urgente e asciutto. "
            "Frasi corte. Conteggio risorse esplicito. "
            "Il tempo è il nemico principale — ogni turno conta. "
            "Nessuna scena decorativa: ogni elemento narrativo ha una funzione di sopravvivenza."
        ),
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
        "tone_instruction": (
            "Registro narrativo: dark fantasy investigativo con tensione rurale. "
            "Atmosfera di paura collettiva e superstizione. "
            "La verità è umana, non soprannaturale — suggerisci il mostro, mantieni l'ambiguità. "
            "Dialoghi carichi di paura e sospetto reciproco tra i personaggi."
        ),
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
        "tone_instruction": (
            "Registro narrativo: stile epico e sensoriale. "
            "Descrizioni ricche di colore, suono, movimento. "
            "Gli NPC parlano con un tono eroico o popolare — mai moderno. "
            "La magia e il pericolo sono concreti e visibili nel mondo."
        ),
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["ambush", "chase", "guardian attack", "curse intensifies"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["sci-fi genre shift", "cosmic apocalypse without trigger"],
    },
    "mystery_horror": {
        "id": "mystery_horror",
        "tone": "mystery horror",
        "tone_instruction": (
            "Registro narrativo: horror cosmico e psicologico. "
            "Frasi brevi nei momenti di paura. Aggettivi viscerali (freddo umido, buio pesante, silenzio assoluto). "
            "L'orrore cresce per accumulo — non per esplosione. "
            "Mantieni sempre qualcosa di non detto o non visto."
        ),
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["fear spike", "witness panic", "haunting sign"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["cosmic finale without clues", "monster truth revealed too early"],
    },
    "sci_fi": {
        "id": "sci_fi",
        "tone": "science fiction",
        "tone_instruction": (
            "Registro narrativo: tecnico e controlato con tensione latente. "
            "Terminologia tecnica plausibile (pressione, protocollo, sequenza). "
            "L'ambiente reagisce alle azioni del gruppo — sistemi, allarmi, interfacce. "
            "Il pericolo è procedurale e logico, non magico."
        ),
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["system alert", "decompression warning", "security response"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["magic genre shift", "planet destroyed without clock"],
    },
    "ww2": {
        "id": "ww2",
        "tone": "war drama",
        "tone_instruction": (
            "Registro narrativo: war drama sobrio e morale. "
            "Enfasi su costi umani, incertezza tattica e scelte difficili. "
            "Gli NPC hanno paure e motivazioni realistiche — niente eroismi facili. "
            "Ogni vittoria ha un prezzo: mostralo esplicitamente."
        ),
        "max_default_tier": 4,
        "allowed_escalations": DEFAULT_ALLOWED + ["patrol alerted", "shelling nearby", "route compromised"],
        "forbidden_escalations": DEFAULT_FORBIDDEN + ["supernatural apocalypse without canon"],
    },
    "detective_classico": {
        "id": "detective_classico",
        "tone": "classic detective",
        "tone_instruction": (
            "Registro narrativo: giallo classico, stile freddo e razionale. "
            "Dialoghi taglienti e dialettici — ogni NPC ha qualcosa da nascondere. "
            "Le prove parlano da sole: lascia che i giocatori deducano, non spiegare. "
            "Ogni NPC ha un alibi, un movente o una bugia: rendila percepibile nel tono."
        ),
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
        "tone_instruction": "",
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
        if profile.get("tone_instruction"):
            merged["tone_instruction"] = profile["tone_instruction"]
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
