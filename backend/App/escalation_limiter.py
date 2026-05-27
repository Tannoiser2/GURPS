from __future__ import annotations

from .genre_constraints import get_genre_profile, is_escalation_allowed

TIER_NAMES = {
    0: "color",
    1: "minor_complication",
    2: "cost_or_delay",
    3: "pressure_increase",
    4: "danger_scene",
    5: "major_event",
    6: "terminal_event",
}

# Descrizioni narrative per tier — iniettate nel prompt del Director
# così Claude sa esattamente cosa può narrare a ogni livello.
TIER_DESCRIPTIONS = {
    0: (
        "TIER 0 — COLOR: dettaglio atmosferico, NPC che si sposta, oggetto che cambia stato. "
        "Nessuna conseguenza meccanica. Nessun pericolo. Solo texture."
    ),
    1: (
        "TIER 1 — COMPLICAZIONE MINORE: piccolo ostacolo superabile, un NPC che si irrigidisce, "
        "una porta chiusa, un documento incompleto. Nessuna perdita reale. Zero threat_increase."
    ),
    2: (
        "TIER 2 — COSTO O RITARDO: il personaggio ottiene qualcosa ma paga un prezzo: "
        "tempo perso, risorsa consumata, NPC che diventa meno collaborativo, accesso parziale. "
        "threat_increase=0. Nessun allarme, nessun nemico."
    ),
    3: (
        "TIER 3 — AUMENTO PRESSIONE: qualcosa va storto in modo visibile — allarme locale, "
        "NPC che si chiude, copertura compromessa, clock che avanza di 1. "
        "threat_increase=1. Nessun combattimento diretto, nessun ferimento grave."
    ),
    4: (
        "TIER 4 — SCENA PERICOLOSA: nemico che attacca, trappola scattata, inseguimento, "
        "confronto fisico. activate_combat ammesso. Ferite possibili. "
        "Ogni combattimento non-finale deve avere una via di uscita."
    ),
    5: (
        "TIER 5 — EVENTO MAGGIORE: rivelazione devastante, tradimento di un alleato, "
        "location distrutta, antagonista che si manifesta, clock completato. "
        "Solo con explicit_trigger o clock completato."
    ),
    6: (
        "TIER 6 — EVENTO TERMINALE: fine avventura, vittoria o sconfitta definitiva. "
        "Solo con finale_condition soddisfatta E explicit_trigger o clock completato."
    ),
}

OUTCOME_DEFAULT_TIER = {
    "critico": 2,
    "critical_success": 2,
    "successo pieno": 2,
    "success": 2,
    "successo parziale": 3,
    "partial_success": 3,
    "fallimento": 3,
    "failure": 3,
    "fallimento critico": 4,
    "critical_failure": 4,
}

PASSIVE_INTENTS = {"investigation", "observation", "technical", "medical", "social", "stealth", "survival", "generic"}
TIER_5_EVENTS = {"major_event", "final_revelation", "location_destroyed", "murder", "betrayal", "boss_sign"}
TIER_6_EVENTS = {"story_over", "finale", "game_over", "party_death", "death_group", "boss_release", "apocalypse", "world_destroyed"}


def _outcome_key(roll_outcome: str | dict | None) -> str:
    if isinstance(roll_outcome, dict):
        roll_outcome = roll_outcome.get("outcome") or ("critical_failure" if roll_outcome.get("critical") and not roll_outcome.get("success") else "")
    text = str(roll_outcome or "").strip().lower()
    if "fallimento critico" in text or "critical_failure" in text:
        return "fallimento critico"
    if "critico" in text or "critical_success" in text:
        return "critico"
    if "parziale" in text or "partial" in text:
        return "successo parziale"
    if "fall" in text or "failure" in text:
        return "fallimento"
    if "success" in text or "successo" in text:
        return "successo pieno"
    return "successo pieno"


def compute_allowed_escalation_tier(
    roll_outcome: str | dict | None,
    action_intent: str | None,
    runtime_profile: str | None,
    active_clocks: list[dict] | None = None,
    scene_context: dict | None = None,
    genre_profile: dict | None = None,
    investigation_progress: int = 0,
) -> int:
    """Il Director usa questa funzione per fissare il tetto massimo del renderer.

    investigation_progress:
      > 0  → progressi questa sessione (indizi trovati, thread risolti) — riduce tier
      < 0  → turni di stallo consecutivi — aumenta tier (pressione narrativa)
      = 0  → neutro
    """
    profile = genre_profile or get_genre_profile([runtime_profile] if runtime_profile else [], None)
    tier = OUTCOME_DEFAULT_TIER.get(_outcome_key(roll_outcome), 3)
    tier = min(tier, int(profile.get("max_default_tier", 4)))

    intent = str(action_intent or "").lower()
    if intent in PASSIVE_INTENTS:
        tier = min(tier, 3 if intent != "stealth" else 4)
    if intent == "combat":
        tier = max(tier, 4)

    # ── Soft escalation: modifica tier in base ai progressi investigativi ─────
    if investigation_progress > 0:
        # I giocatori stanno avanzando → frena la pressione
        # Un indizio trovato in questo turno: abbassa tier di 1 (min 1)
        tier = max(1, tier - 1)
    elif investigation_progress <= -3:
        # Tre o più turni di stallo consecutivi → aumenta leggermente la pressione
        # per spingere i giocatori verso una svolta narrativa
        tier = min(int(profile.get("max_default_tier", 4)), tier + 1)

    scene_context = scene_context or {}
    active_clocks = active_clocks or []
    explicit_trigger = bool(scene_context.get("explicit_trigger") or scene_context.get("director_authorization"))
    finale_condition = bool(scene_context.get("finale_condition") or scene_context.get("finale_condition_met"))
    completed_clock = bool(scene_context.get("completed_clock") or any(c.get("completed") for c in active_clocks if isinstance(c, dict)))

    if explicit_trigger or completed_clock:
        tier = max(tier, 5)
    if finale_condition and (explicit_trigger or completed_clock):
        tier = 6
    if tier >= 6 and not (finale_condition or completed_clock or explicit_trigger):
        tier = 5
    if intent in PASSIVE_INTENTS and tier >= 6 and not finale_condition:
        tier = 4
    return max(0, min(6, int(tier)))


def classify_event_tier(state_update: dict | str | None, narrative_text_optional: str = "") -> int:
    if isinstance(state_update, str):
        blob = state_update
        update = {}
    else:
        update = state_update or {}
        blob = " ".join(str(x) for x in [
            update.get("major_event"),
            update.get("major_events"),
            update.get("blocked_event"),
            update.get("event_type"),
            narrative_text_optional,
        ])
    low = blob.lower()
    if update.get("story_over") or update.get("victory") or any(term in low for term in TIER_6_EVENTS):
        return 6
    if any(term in low for term in TIER_5_EVENTS):
        return 5
    if update.get("activate_combat") or update.get("combat_scene") or "ambush" in low or "agguato" in low:
        return 4
    if int(update.get("threat_increase") or 0) > 0 or "clock" in low or "pressure" in low:
        return 3
    if update.get("clue_progress") or update.get("location_access") or update.get("objective_progress"):
        return 2
    if update.get("npc_updates") or update.get("discovered_facts"):
        return 1
    return 0


def downgrade_event_to_allowed_tier(blocked_event: dict | str | None, allowed_tier: int, genre_profile: dict | None = None) -> dict:
    profile = genre_profile or {}
    allowed = profile.get("allowed_escalations") or []
    note = allowed[0] if allowed else TIER_NAMES.get(max(0, allowed_tier), "bounded consequence")
    if allowed_tier >= 4 and is_escalation_allowed("danger_scene", profile):
        return {
            "threat_increase": 1,
            "activate_combat": False,
            "combat_scene": None,
            "downgraded_events": [{"blocked": str(blocked_event), "replacement": "danger warning / enemy movement", "tier": 4}],
        }
    if allowed_tier >= 3:
        return {
            "threat_increase": 1,
            "downgraded_events": [{"blocked": str(blocked_event), "replacement": "pressure_increase", "tier": 3}],
        }
    if allowed_tier >= 2:
        return {
            "threat_increase": 0,
            "objective_progress": 1,
            "downgraded_events": [{"blocked": str(blocked_event), "replacement": "cost_or_delay", "tier": 2}],
        }
    return {
        "threat_increase": 0,
        "downgraded_events": [{"blocked": str(blocked_event), "replacement": note, "tier": max(0, allowed_tier)}],
    }
