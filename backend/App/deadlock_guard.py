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


def _find_relevant_npcs(definition: AdventureDefinition, revelation: Any) -> List[str]:
    """Returns names of up to 3 NPCs most relevant to the revelation thread."""
    rev_thread = getattr(revelation, "thread_id", "") or getattr(revelation, "id", "")
    npcs = list(getattr(definition, "npcs", []) or [])
    # Prefer NPCs in the same thread, then any non-antagonist NPC
    scored = []
    for npc in npcs:
        name = getattr(npc, "name", "") or (npc.get("name", "") if isinstance(npc, dict) else "")
        role = (getattr(npc, "role", "") or (npc.get("role", "") if isinstance(npc, dict) else "")).lower()
        if not name:
            continue
        score = 0
        npc_thread = getattr(npc, "thread_id", "") or (npc.get("thread_id", "") if isinstance(npc, dict) else "")
        if rev_thread and npc_thread == rev_thread:
            score += 3
        if role in ("witness", "informant", "survivor", "ally"):
            score += 2
        if role not in ("antagonist", "villain"):
            score += 1
        scored.append((score, name))
    scored.sort(key=lambda x: -x[0])
    return [name for _, name in scored[:3]]


def _parse_clue_json(raw: str, revelation_id: str) -> Optional[Dict[str, Any]]:
    """Parse Claude JSON response for a failforward clue."""
    text = raw.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    obj = json.loads(text)
    obj["id"] = f"failforward_{revelation_id}"
    obj["state"] = "available"
    obj["_injected"] = True
    obj["_failforward"] = True
    return obj


def _generate_failforward_clue(
    revelation: Any,
    destroyed_clue_ids: List[str],
    definition: AdventureDefinition,
) -> Dict[str, Any]:
    """L5: genera un failforward clue contestualizzato usando hidden_truth + top NPC.

    Livello 1: prompt ricco (Haiku) con hidden_truth + NPCs rilevanti + destroyed clue details
    Livello 2: prompt semplificato (solo rivelazione + NPC) se livello 1 fallisce
    Livello 3: fallback deterministico contestuale (usa NPC e location reali, non template generici)
    """
    title = getattr(definition, "title", "")
    genre = getattr(definition, "genre", "")
    premise = getattr(definition, "premise", "")[:200]
    hidden_truth = getattr(definition, "hidden_truth", "") or ""
    rev_statement = getattr(revelation, "statement", "")
    rev_payoff = getattr(revelation, "payoff", "")
    rev_id = getattr(revelation, "id", "revelation")

    # Raccogli dettagli sugli indizi distrutti
    destroyed_info = []
    for cid in (getattr(revelation, "required_clues", []) or []):
        if cid in destroyed_clue_ids:
            c = _find_clue_def(cid, definition)
            if c:
                destroyed_info.append(f'- "{getattr(c, "label", cid)}": {getattr(c, "reveals", "")}')
    destroyed_text = "\n".join(destroyed_info) if destroyed_info else "(prove non specificate)"

    # Top 3 NPC rilevanti
    relevant_npcs = _find_relevant_npcs(definition, revelation)
    npc_text = ", ".join(relevant_npcs) if relevant_npcs else "nessuno in particolare"

    # Location base dall'avventura
    locations = list(getattr(definition, "locations", []) or [])
    loc_names = [
        (getattr(l, "name", "") or (l.get("name", "") if isinstance(l, dict) else ""))
        for l in locations[:3]
    ]
    loc_names = [n for n in loc_names if n]
    fallback_location = loc_names[0] if loc_names else "un luogo dell'avventura"
    fallback_npc = relevant_npcs[0] if relevant_npcs else "un testimone"

    json_schema = f"""{{
  "id": "failforward_{rev_id}",
  "label": "nome breve dell'indizio (max 6 parole)",
  "type": "uno tra: witness_testimony, physical_evidence, document, rumor",
  "reveals": "cosa rivela questo indizio (1-2 frasi)",
  "source_location": "dove si trova (nome luogo o NPC)",
  "immediate_information": "cosa capiscono subito i giocatori",
  "hidden_implication": "significato più profondo che emerge dopo"
}}"""

    # Livello 1: prompt ricco
    prompt_l1 = f"""Avventura GURPS: {title} ({genre})
Premessa: {premise}
Verità nascosta centrale: {hidden_truth[:150] if hidden_truth else "(non specificata)"}

Rivelazione bloccata: {rev_statement}
Payoff narrativo: {rev_payoff}
NPC più rilevanti in scena: {npc_text}

Prove distrutte dall'antagonista:
{destroyed_text}

Un antagonista ha eliminato le prove. Genera UN SOLO indizio alternativo coerente con la verità centrale
dell'avventura. L'indizio deve coinvolgere uno degli NPC presenti, puntare a una location reale dell'avventura,
e aprire una strada alternativa per arrivare alla stessa verità senza contraddicarla.

Rispondi SOLO con JSON valido (nessun markdown):
{json_schema}"""

    try:
        raw = _claude_raw(prompt_l1, max_tokens=512)
        clue = _parse_clue_json(raw, rev_id)
        if clue:
            print(f"[deadlock_guard L1] failforward generato: '{clue.get('label')}'")
            return clue
    except Exception as e:
        print(f"[deadlock_guard L1] fallito: {e}")

    # Livello 2: prompt semplificato
    prompt_l2 = f"""Avventura: {title}. Rivelazione bloccata: {rev_statement}.
NPC disponibili: {npc_text}. Location: {fallback_location}.
Genera un indizio JSON alternativo (witness_testimony o physical_evidence) che porta alla stessa verità.
Solo JSON, nessun markdown: {json_schema}"""

    try:
        raw = _claude_raw(prompt_l2, max_tokens=350)
        clue = _parse_clue_json(raw, rev_id)
        if clue:
            print(f"[deadlock_guard L2] failforward generato: '{clue.get('label')}'")
            return clue
    except Exception as e:
        print(f"[deadlock_guard L2] fallito: {e}")

    # Livello 3: fallback deterministico contestuale (usa NPC e location reali)
    print(f"[deadlock_guard L3] uso fallback contestuale per '{rev_id}'")
    return {
        "id": f"failforward_{rev_id}",
        "label": f"Confessione di {fallback_npc}",
        "type": "witness_testimony",
        "reveals": rev_statement or "Qualcuno conosce la verità e decide di parlare.",
        "source_location": fallback_npc,
        "immediate_information": (
            f"{fallback_npc} approfitta di un momento riservato per avvicinarsi al gruppo con un'informazione "
            f"che non avrebbe dovuto condividere — qualcosa che aveva visto e taciuto per paura."
        ),
        "hidden_implication": hidden_truth[:120] if hidden_truth else "",
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
