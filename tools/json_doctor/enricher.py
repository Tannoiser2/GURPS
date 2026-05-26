"""
AI-powered enrichment for adventure JSON files.
Uses Claude to fill in missing fields based on audit findings.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

from .rules import Finding

# Try to import anthropic; graceful degradation if not installed
try:
    import anthropic
    _CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    _MODEL = "claude-sonnet-4-5"
    _HAS_CLAUDE = True
except ImportError:
    _HAS_CLAUDE = False


def _call_claude(prompt: str, system: str = "") -> str:
    if not _HAS_CLAUDE:
        raise RuntimeError("anthropic package non installato. Esegui: pip install anthropic")
    messages = [{"role": "user", "content": prompt}]
    response = _CLIENT.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=system or "Sei un game designer GURPS esperto. Rispondi SOLO con JSON valido, senza markdown.",
        messages=messages,
    )
    return response.content[0].text.strip()


def _enrich_npc(actor: Dict, adventure_context: str) -> Dict:
    """Fill missing NPC fields using Claude."""
    name = actor.get("name", actor.get("id", "NPC"))
    goal = actor.get("goal", "")
    secret = actor.get("secret", "")
    role = actor.get("role", "neutral")

    prompt = f"""Contesto avventura: {adventure_context}

NPC da arricchire:
- Nome: {name}
- Ruolo: {role}
- Obiettivo: {goal}
- Segreto: {secret}
- Piano attuale: {actor.get("current_plan", "")}

Genera un JSON con SOLO questi campi (non modificare gli altri):
{{
  "pressure_response": {{
    "low": "comportamento quando pressure 0-2",
    "medium": "comportamento quando pressure 3-5",
    "high": "comportamento quando pressure 6-8",
    "extreme": "comportamento quando pressure 9+"
  }},
  "reaction_table": {{
    "se_minacciato": "reazione specifica a {name}",
    "se_corrotto_o_pagato": "reazione specifica",
    "se_i_pg_hanno_prove": "reazione specifica",
    "se_alleato": "reazione specifica"
  }},
  "current_plan": "piano specifico basato su contesto",
  "fallback_plan": "piano B se il principale fallisce"
}}

Sii specifico al personaggio e all'avventura. Non usare testo generico."""

    try:
        raw = _call_claude(prompt)
        # Extract JSON even if Claude wraps it
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        enrichment = json.loads(raw.strip())
        return {**actor, **enrichment, "llm_enriched": True}
    except Exception as e:
        print(f"  [warn] Enrichment NPC '{name}' fallito: {e}", file=sys.stderr)
        return actor


def _enrich_clocks(clocks: List[Dict], adventure_context: str) -> List[Dict]:
    """Fill missing clock fields using Claude."""
    if not clocks:
        return clocks

    prompt = f"""Contesto avventura: {adventure_context}

Clock da migliorare:
{json.dumps(clocks, ensure_ascii=False, indent=2)}

Per ogni clock, genera steps narrativi progressivi e resolution_condition chiara.
Restituisci SOLO la lista JSON aggiornata dei clock con:
- steps: lista di {{"value": N, "label": "descrizione", "effect": "effetto narrativo"}} (almeno 4 step)
- resolution_condition: stringa che spiega come i giocatori fermano il clock
- discovery_hint: presagio narrativo del clock (ambiguo, non diretto)
- ticks_per_failure: 2 (di default)

Non modificare id, label, max_value, clock_type o altri campi."""

    try:
        raw = _call_claude(prompt)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        enriched = json.loads(raw.strip())
        if isinstance(enriched, list) and len(enriched) == len(clocks):
            return enriched
        return clocks
    except Exception as e:
        print(f"  [warn] Enrichment clock fallito: {e}", file=sys.stderr)
        return clocks


def _enrich_resources(data: Dict, adventure_context: str) -> List[Dict]:
    """Generate resources appropriate for the adventure genre."""
    genre = data.get("genre", "")
    title = data.get("title", "")

    prompt = f"""Avventura: {title}
Genere: {genre}
Contesto: {adventure_context}

Genera un array JSON di risorse appropriate per questa avventura.
Ogni risorsa ha:
{{
  "id": "snake_case_id",
  "label": "Nome Leggibile",
  "value": N,      // valore iniziale
  "max_value": N   // massimo
}}

Esempi tipici per genere horror: sanity (10), light (6), morale (8)
Per thriller: time (12), evidence (0), heat (0)
Per fantasy: food (10), gold (50), reputation (5)

Restituisci SOLO l'array JSON, 2-4 risorse appropriate al contesto."""

    try:
        raw = _call_claude(prompt)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        resources = json.loads(raw.strip())
        if isinstance(resources, list):
            return resources
        return []
    except Exception as e:
        print(f"  [warn] Enrichment resources fallito: {e}", file=sys.stderr)
        return []


def _enrich_clues(clues: List[Dict], adventure_context: str) -> List[Dict]:
    """Fill missing clue fields using Claude."""
    if not clues:
        return clues

    # Only process clues with missing fields to save API calls
    needs_enrichment = [
        c for c in clues
        if not c.get("payoff") or not c.get("hidden_implication") or not c.get("wrong_interpretations")
    ]

    if not needs_enrichment:
        return clues

    prompt = f"""Contesto avventura: {adventure_context}

Indizi da completare (solo quelli con campi mancanti):
{json.dumps(needs_enrichment, ensure_ascii=False, indent=2)}

Per ogni indizio, aggiungi i campi mancanti:
- payoff: cosa rivela narrativamente (stringa)
- hidden_implication: significato nascosto che i giocatori non capiscono subito
- wrong_interpretations: lista di 1-2 false interpretazioni possibili

Restituisci SOLO la lista JSON aggiornata degli stessi indizi (stesso ordine, stessi id)."""

    try:
        raw = _call_claude(prompt)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        enriched_list = json.loads(raw.strip())
        # Merge back into original list
        enriched_map = {c["id"]: c for c in enriched_list if "id" in c}
        return [enriched_map.get(c.get("id"), c) for c in clues]
    except Exception as e:
        print(f"  [warn] Enrichment clues fallito: {e}", file=sys.stderr)
        return clues


def _enrich_initial_hook(data: Dict) -> str:
    """Generate an initial_hook from premise, actors and tone."""
    title = data.get("title", "")
    genre = data.get("genre", "")
    premise = data.get("premise", "")[:300]
    tone = data.get("tone", "")
    actors = [a.get("name", "") for a in data.get("actors", [])[:3]]
    actor_names = ", ".join(a for a in actors if a)

    prompt = f"""Avventura GURPS: {title}
Genere: {genre}
Tono: {tone}
Premessa: {premise}
NPC principali: {actor_names}

Scrivi un initial_hook: la scena di apertura con cui il GM presenta l'avventura ai giocatori.
Deve essere concreto, coinvolgente, 2-4 frasi. Include dove si trovano i personaggi, cosa vedono o sentono, e quale evento o persona li trascina nell'avventura.
Restituisci SOLO una stringa JSON (non un oggetto, solo la stringa tra virgolette)."""

    try:
        raw = _call_claude(prompt, system="Sei un game designer GURPS esperto. Rispondi SOLO con una stringa JSON valida.")
        raw = raw.strip()
        if raw.startswith('"') and raw.endswith('"'):
            return json.loads(raw)
        return raw.strip('"')
    except Exception as e:
        print(f"  [warn] Generazione initial_hook fallita: {e}", file=sys.stderr)
        return ""


def enrich(data: Dict, findings: List[Finding], dry_run: bool = False) -> Dict:
    """
    Enrich an adventure JSON based on audit findings.
    Returns the enriched data dict.
    """
    categories = {f.category for f in findings}
    severity_has = lambda sev: any(f.severity == sev for f in findings)

    context = f"{data.get('title', '')} — {data.get('genre', '')} — {data.get('premise', '')[:200]}"

    result = dict(data)

    # Structure enrichment — initial_hook
    if not result.get("initial_hook") and not dry_run:
        print(f"  → Generazione initial_hook")
        hook = _enrich_initial_hook(result)
        if hook:
            result["initial_hook"] = hook

    # NPC enrichment
    if "npc" in categories and not dry_run:
        actors = result.get("actors", [])
        npc_findings = [f for f in findings if f.category == "npc"]
        affected_ids = {f.entity_id for f in npc_findings}
        enriched_actors = []
        for actor in actors:
            if actor.get("id") in affected_ids:
                print(f"  → Arricchimento NPC: {actor.get('name', actor.get('id'))}")
                enriched_actors.append(_enrich_npc(actor, context))
            else:
                enriched_actors.append(actor)
        result["actors"] = enriched_actors

    # Clock enrichment
    if "clock" in categories and not dry_run:
        clock_findings = [f for f in findings if f.category == "clock" and f.entity_id != data.get("title")]
        if clock_findings and result.get("event_clocks"):
            print(f"  → Arricchimento {len(result['event_clocks'])} clock(s)")
            result["event_clocks"] = _enrich_clocks(result["event_clocks"], context)

    # Resource enrichment
    if "resource" in categories and not result.get("resources") and not dry_run:
        print(f"  → Generazione risorse")
        result["resources"] = _enrich_resources(result, context)

    # Clue enrichment
    if "clue" in categories and not dry_run:
        if result.get("clues"):
            print(f"  → Arricchimento {len(result['clues'])} indizi")
            result["clues"] = _enrich_clues(result["clues"], context)

    return result
