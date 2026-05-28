"""A3: Adventure creation wizard — step-by-step logic.

Separato da main.py per testabilità. main.py chiama queste funzioni
e le espone come endpoint FastAPI.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

WIZARD_STEPS = ["title", "premise", "npcs", "clocks", "clues"]

WIZARD_STEP_SCHEMA = {
    "title": {
        "fields": ["title", "genre"],
        "description": "Titolo e genere dell'avventura",
        "required": ["title", "genre"],
        "example": {"title": "Il Caso della Villa Rossa", "genre": "investigation"},
    },
    "premise": {
        "fields": ["premise", "hidden_truth", "win_condition", "threat_description"],
        "description": "Premessa, verità nascosta, condizione di vittoria e minaccia",
        "required": ["premise", "hidden_truth", "win_condition"],
        "example": {
            "premise": "Un nobile è stato trovato morto. La famiglia chiede discrezione.",
            "hidden_truth": "La figlia ha avvelenato il padre per proteggere il suo amante.",
            "win_condition": "Scoprire il colpevole e consegnarlo alle autorità.",
            "threat_description": "Il vero assassino sta coprendo le sue tracce.",
        },
    },
    "npcs": {
        "fields": ["npcs"],
        "description": "Lista NPC (min 2): id, name, role, goal, location, attitude",
        "required": ["npcs"],
        "example": {"npcs": [
            {"id": "npc_1", "name": "Elena Rossi", "role": "witness", "goal": "Proteggere il segreto di famiglia", "location": "Villa Rossa", "attitude": "neutral"},
            {"id": "npc_2", "name": "Ispettore Ferrara", "role": "ally", "goal": "Chiudere il caso rapidamente", "location": "Commissariato", "attitude": "friendly"},
        ]},
    },
    "clocks": {
        "fields": ["clocks"],
        "description": "Lista clock (min 1): id, label, max_value, consequence, clock_type",
        "required": ["clocks"],
        "example": {"clocks": [
            {"id": "clock_1", "label": "Prove distrutte", "max_value": 6, "consequence": "L'assassino brucia tutti gli indizi", "clock_type": "terminal_defeat"},
        ]},
    },
    "clues": {
        "fields": ["clues", "threads"],
        "description": "Lista indizi (min 3) e thread narrativi (min 1)",
        "required": ["clues", "threads"],
        "example": {
            "clues": [
                {"id": "clue_1", "label": "Lettera avvelenata", "type": "document", "thread_id": "thread_1",
                 "source_location": "Studio del nobile", "reveals": "Qualcuno ha usato arsenico."},
            ],
            "threads": [
                {"id": "thread_1", "question": "Chi ha avvelenato il nobile?",
                 "required_clues": ["clue_1"], "minimum_clues_to_deduce": 1, "payoff": "La figlia confessa."},
            ],
        },
    },
}

# In-memory draft store {draft_id: dict}
_drafts: dict[str, dict] = {}


def validate_step(step: str, data: dict) -> list[str]:
    """Valida i dati di uno step. Restituisce lista di errori (vuota se OK)."""
    if step not in WIZARD_STEPS:
        return [f"Step sconosciuto: {step}. Validi: {WIZARD_STEPS}"]

    schema = WIZARD_STEP_SCHEMA[step]
    errors: list[str] = []
    for req in schema["required"]:
        if req not in data or not data[req]:
            errors.append(f"Campo obbligatorio mancante: '{req}'")

    if errors:
        return errors

    if step == "npcs":
        npcs = data.get("npcs") or []
        if len(npcs) < 2:
            errors.append("Servono almeno 2 NPC")
        for i, npc in enumerate(npcs):
            if not npc.get("id") or not npc.get("name"):
                errors.append(f"NPC #{i+1}: 'id' e 'name' sono obbligatori")

    elif step == "clocks":
        clocks = data.get("clocks") or []
        if not clocks:
            errors.append("Serve almeno 1 clock")
        for i, ck in enumerate(clocks):
            if not ck.get("id") or not ck.get("label"):
                errors.append(f"Clock #{i+1}: 'id' e 'label' sono obbligatori")

    elif step == "clues":
        clues = data.get("clues") or []
        threads = data.get("threads") or []
        if len(clues) < 3:
            errors.append("Servono almeno 3 indizi")
        if not threads:
            errors.append("Serve almeno 1 thread narrativo")

    return errors


def apply_step(draft_id: str, step: str, data: dict) -> dict:
    """Applica i dati di uno step alla bozza. Restituisce la risposta wizard."""
    errors = validate_step(step, data)
    if errors:
        return {"draft_id": draft_id, "step": step, "validation_errors": errors, "completed": False, "next_step": None, "draft_preview": {}}

    did = draft_id or str(uuid.uuid4())[:8]
    draft = dict(_drafts.get(did) or {})
    draft["_updated"] = datetime.now(timezone.utc).isoformat()

    if step == "title":
        draft["title"] = data["title"]
        draft["genre"] = data["genre"]
    elif step == "premise":
        draft["premise"] = data["premise"]
        draft["hidden_truth"] = data["hidden_truth"]
        draft["win_condition"] = data["win_condition"]
        draft["threat_description"] = data.get("threat_description", "")
    elif step == "npcs":
        draft["actors"] = data["npcs"]
    elif step == "clocks":
        draft["event_clocks"] = data["clocks"]
    elif step == "clues":
        draft["clues"] = data["clues"]
        draft["story_threads"] = data["threads"]

    completed_steps = list(set(draft.get("_completed_steps") or []) | {step})
    draft["_completed_steps"] = completed_steps
    _drafts[did] = draft

    step_idx = WIZARD_STEPS.index(step)
    next_step = WIZARD_STEPS[step_idx + 1] if step_idx + 1 < len(WIZARD_STEPS) else None
    all_done = set(WIZARD_STEPS) <= set(completed_steps)

    return {
        "draft_id": did,
        "step": step,
        "next_step": next_step,
        "completed": all_done,
        "validation_errors": [],
        "draft_preview": {k: v for k, v in draft.items() if not k.startswith("_")},
    }


def get_draft(draft_id: str) -> dict | None:
    """Recupera una bozza per id. Restituisce None se non trovata."""
    draft = _drafts.get(draft_id)
    if not draft:
        return None
    completed = draft.get("_completed_steps") or []
    return {
        "draft_id": draft_id,
        "draft": {k: v for k, v in draft.items() if not k.startswith("_")},
        "completed_steps": completed,
        "missing_steps": [s for s in WIZARD_STEPS if s not in completed],
        "ready_to_compile": set(WIZARD_STEPS) <= set(completed),
    }


def pop_draft(draft_id: str) -> dict | None:
    """Rimuove e restituisce una bozza (usato dopo compilazione)."""
    return _drafts.pop(draft_id, None)


def draft_as_raw(draft_id: str) -> dict | None:
    """Converte la bozza nel formato raw per compile_from_raw_structure."""
    draft = _drafts.get(draft_id)
    if not draft:
        return None
    missing = [s for s in WIZARD_STEPS if s not in (draft.get("_completed_steps") or [])]
    if missing:
        return None
    raw = {k: v for k, v in draft.items() if not k.startswith("_")}
    raw["source_mode"] = "wizard"
    return raw
