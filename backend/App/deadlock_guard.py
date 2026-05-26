"""
Anti-deadlock / fail-forward guard.

After pressure_events fire and potentially destroy clues, this module checks
whether any unsolved revelation has become unreachable (all required clues
destroyed, none yet discovered). If so, it injects a Claude-generated
"failforward" clue into runtime_state.injected_clues so the LLM can
guide players toward it naturally.
"""

import json
from typing import Any, Dict, List, Optional

from .runtime_models import AdventureDefinition, AdventureRuntimeState
from .claude_service import _call_claude as _claude_raw


def _deadlocked_revelations(
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> List[Any]:
    """Return revelations that have no accessible required clues."""
    if not definition or not definition.revelations:
        return []

    destroyed = set(runtime_state.destroyed_clue_ids or [])
    discovered = set(runtime_state.discovered_clue_ids or [])
    injected_ids = {c.get("id") for c in (runtime_state.injected_clues or [])}

    deadlocked = []
    for revelation in definition.revelations:
        status = getattr(revelation, "status", "hidden")
        if status in ("resolved", "revealed"):
            continue

        required = list(getattr(revelation, "required_clues", []) or [])
        if not required:
            continue

        # If any required clue is already discovered, revelation is still reachable
        if any(cid in discovered for cid in required):
            continue

        # Accessible = not destroyed OR re-injected
        accessible = [cid for cid in required if cid not in destroyed or cid in injected_ids]
        if not accessible:
            # Also skip if a failforward clue for this revelation already exists
            failforward_id = f"failforward_{revelation.id}"
            if not any(c.get("id") == failforward_id for c in (runtime_state.injected_clues or [])):
                deadlocked.append(revelation)

    return deadlocked


def _find_clue_def(clue_id: str, definition: AdventureDefinition) -> Optional[Any]:
    for c in (definition.clues or []):
        if c.id == clue_id:
            return c
    return None


def _generate_failforward_clue(
    revelation: Any,
    destroyed_clue_ids: List[str],
    definition: AdventureDefinition,
) -> Dict[str, Any]:
    """Ask Claude (Haiku) to generate a contextually appropriate replacement clue."""
    title = getattr(definition, "title", "")
    genre = getattr(definition, "genre", "")
    premise = getattr(definition, "premise", "")[:200]
    rev_statement = getattr(revelation, "statement", "")
    rev_payoff = getattr(revelation, "payoff", "")

    # Gather info from the destroyed clues for context
    destroyed_info = []
    for cid in (getattr(revelation, "required_clues", []) or []):
        if cid in destroyed_clue_ids:
            c = _find_clue_def(cid, definition)
            if c:
                destroyed_info.append(f'- "{c.label}": {getattr(c, "reveals", "")}')

    destroyed_text = "\n".join(destroyed_info) if destroyed_info else "(nessun dettaglio)"

    prompt = f"""Avventura GURPS: {title} ({genre})
Premessa: {premise}

Rivelazione bloccata: {rev_statement}
Payoff: {rev_payoff}

Indizi distrutti che portavano a questa rivelazione:
{destroyed_text}

Un antagonista ha distrutto le prove. Genera UN SOLO indizio alternativo che permette
ai giocatori di arrivare comunque alla rivelazione attraverso una strada diversa.
L'indizio deve essere credibile nel contesto dell'avventura, non ovvio, e narrativamente
coerente con il fatto che qualcuno ha cercato di coprire le tracce.

Rispondi con JSON valido (solo l'oggetto, nessun markdown):
{{
  "id": "failforward_{revelation.id}",
  "label": "nome breve dell'indizio (max 6 parole)",
  "type": "uno tra: witness_testimony, physical_evidence, document, rumor",
  "reveals": "cosa rivela questo indizio (1-2 frasi)",
  "source_location": "dove si trova (nome luogo o NPC)",
  "immediate_information": "cosa capiscono subito i giocatori",
  "hidden_implication": "significato più profondo che emerge dopo"
}}"""

    try:
        raw = _claude_raw(prompt, max_tokens=512)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        clue = json.loads(raw.strip())
        clue["state"] = "available"
        clue["_injected"] = True
        clue["_failforward"] = True
        return clue
    except Exception as e:
        print(f"[deadlock_guard] Claude fallito, uso fallback statico: {e}")
        # Static fallback — still better than a dead end
        return {
            "id": f"failforward_{revelation.id}",
            "label": "Testimone anonimo",
            "type": "witness_testimony",
            "reveals": rev_statement or "Qualcuno sa la verità.",
            "source_location": "ignoto",
            "immediate_information": "Una voce anonima giunge ai personaggi con informazioni inaspettate.",
            "hidden_implication": "",
            "state": "available",
            "_injected": True,
            "_failforward": True,
        }


def check_and_fix_deadlocks(
    definition: AdventureDefinition,
    runtime_state: AdventureRuntimeState,
) -> List[Dict[str, Any]]:
    """
    Check for deadlocked revelations and inject failforward clues.
    Returns list of injected failforward clue dicts (empty if none needed).
    """
    deadlocked = _deadlocked_revelations(definition, runtime_state)
    if not deadlocked:
        return []

    injected = []
    destroyed = list(runtime_state.destroyed_clue_ids or [])

    for revelation in deadlocked:
        print(f"[deadlock_guard] Rivelazione bloccata: '{revelation.id}' — genero failforward clue")
        clue = _generate_failforward_clue(revelation, destroyed, definition)
        runtime_state.injected_clues.append(clue)
        injected.append(clue)
        print(f"[deadlock_guard] Iniettato: '{clue['label']}' @ {clue.get('source_location', '?')}")

    return injected
