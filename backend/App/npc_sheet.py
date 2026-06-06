"""Scheda GURPS deterministica di base per gli NPC (nessuna chiamata AI).

Condiviso tra il compilatore (popola ActorState) e l'engine (costruisce i
WorldNPC a runtime), così ogni PNG ha attributi, una skill principale e stat
di combattimento — affrontabile meccanicamente, non solo descrizione narrativa.
"""
from __future__ import annotations


def threat_from_role(role: str) -> int:
    """Stima il livello di minaccia (0-3) dal ruolo narrativo."""
    low = (role or "").lower()
    if "antagon" in low or "boss" in low:
        return 3
    if "red" in low or "guard" in low:
        return 2
    if role == "ally" or "alle" in low or "ally" in low:
        return 0
    return 1


def baseline_npc_gurps(role: str, threat: int) -> dict:
    """Scheda GURPS di base scalata sul threat (0 = civile inerme … 3 = boss)."""
    t = max(0, min(3, int(threat)))
    fo, de, in_, sa, skill = {
        0: (10, 10, 11, 10, 10),
        1: (10, 11, 11, 10, 12),
        2: (11, 12, 10, 11, 13),
        3: (12, 13, 12, 12, 14),
    }[t]
    low = (role or "").lower()
    if any(k in low for k in ("antagon", "boss", "guard", "soldier", "minacc", "nemic")):
        primary = "combattere"
    elif any(k in low for k in ("medic", "alle", "ally", "guaritore")):
        primary = "primo soccorso"
    elif any(k in low for k in ("test", "witness", "neutr", "civil")):
        primary = "osservare"
    else:
        primary = "combattere"
    return {
        "gurps_fo": fo, "gurps_de": de, "gurps_in": in_, "gurps_sa": sa,
        "gurps_skills": {primary: skill, "osservare": 10 + t, "schivare": 8 + t},
        "gurps_advantages": (["Riflessi da Combattimento"] if t >= 3 else []),
        "combat_hp": fo, "combat_max_hp": fo, "combat_dr": (1 if t >= 2 else 0),
        "combat_attack_skill": skill, "combat_active_defense": 8 + t // 2,
        "combat_damage_dice": ("1d-2" if t == 0 else "1d-1" if t == 1 else "1d"),
        "combat_damage_type": "cr",
    }
