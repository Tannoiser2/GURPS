from __future__ import annotations

from .runtime_models import RuntimeClue


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
