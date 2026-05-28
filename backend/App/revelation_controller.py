from __future__ import annotations

from .runtime_models import RuntimeClue

# ─── N4: Revelation pacing control ───────────────────────────────────────────
# Previene revelation-dump (>2 rivelazioni in un turno) e sessioni stagnanti.

_PACING_RECENT_TURNS = 3   # finestra temporale per "recente"
_DUMP_THRESHOLD = 2         # max rivelazioni accettabili in un singolo turno


def pacing_score(canonical_log: list[dict], current_turn: int) -> dict:
    """Calcola la velocità delle rivelazioni recenti.

    Restituisce:
        score:             0.0 (sessione lenta) → 1.0 (troppo rapida)
        recent_revelations: numero di thread_closed negli ultimi N turni
        label:             "slow" | "normal" | "fast" | "dump"
    """
    recent_window = max(1, current_turn - _PACING_RECENT_TURNS)
    recent_revelations = sum(
        1 for ev in (canonical_log or [])
        if ev.get("type") == "thread_closed" and int(ev.get("turn", 0)) >= recent_window
    )
    this_turn_revelations = sum(
        1 for ev in (canonical_log or [])
        if ev.get("type") == "thread_closed" and int(ev.get("turn", 0)) == current_turn
    )

    if this_turn_revelations >= _DUMP_THRESHOLD:
        label = "dump"
        score = 1.0
    elif recent_revelations == 0:
        label = "slow"
        score = 0.0
    elif recent_revelations == 1:
        label = "normal"
        score = 0.4
    else:
        label = "fast"
        score = min(1.0, 0.5 + 0.2 * (recent_revelations - 1))

    return {
        "score": score,
        "label": label,
        "recent_revelations": recent_revelations,
        "this_turn_revelations": this_turn_revelations,
    }


def suggest_revelation_timing(pacing: dict, available_revelations: int) -> str:
    """Restituisce la direttiva timing per il Director.

    "now"  → pubblica la prossima revelation (sessione lenta o normale)
    "wait" → aspetta un turno (sessione veloce ma non critica)
    "hold" → blocca per anti-dump (troppo recente)
    """
    if available_revelations <= 0:
        return "wait"
    label = pacing.get("label", "normal")
    if label == "dump":
        return "hold"
    if label == "fast":
        return "wait"
    return "now"


def clue_payoff_payload(clue: RuntimeClue | dict) -> dict:
    """Layer esplicito di payoff per UI, validator e Master AI."""
    data = clue.model_dump() if hasattr(clue, "model_dump") else dict(clue or {})
    return {
        "clue_id": data.get("id"),
        "immediate_information": data.get("immediate_information") or data.get("label") or "",
        "hidden_implication": data.get("hidden_implication") or data.get("reveals") or "",
        "unlocks": data.get("unlocks") or [],
        "possible_actions": data.get("possible_actions") or [],
        "wrong_interpretations": data.get("wrong_interpretations") or [],
    }


def ready_to_deduce(thread: dict, discovered_clues: set[str]) -> bool:
    required = list(thread.get("required_clues") or [])
    minimum = int(thread.get("minimum_clues_to_deduce") or min(2, max(1, len(required))))
    return len([cid for cid in required if cid in discovered_clues]) >= minimum
