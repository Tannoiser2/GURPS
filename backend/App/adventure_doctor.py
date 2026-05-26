"""
Adventure Doctor — audit and AI-powered enrichment for adventure definitions.
Mirrors tools/json_doctor but runs inside the backend using claude_service.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .claude_service import _call_claude as _claude_raw  # reuse existing Claude client


def _llm(prompt: str, max_tokens: int = 1024) -> str:
    """Call the active LLM with a prompt string."""
    return _claude_raw(prompt, max_tokens=max_tokens)


# ─────────────────────────────────────────────
# Findings
# ─────────────────────────────────────────────

@dataclass
class Finding:
    severity: str   # "critical" | "warning" | "info"
    category: str   # "npc" | "clock" | "resource" | "clue" | "structure"
    entity_id: str
    message: str
    fix_hint: str = ""


# ─────────────────────────────────────────────
# Audit rules
# ─────────────────────────────────────────────

def _actor_rules(actors: List[Dict]) -> List[Finding]:
    findings = []
    for a in actors:
        aid = a.get("id", "?")
        name = a.get("name", aid)
        pr = a.get("pressure_response", {})
        if not pr or len(pr) < 2:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': pressure_response assente o incompleto",
                "Aggiungi livelli low/medium/high/extreme"))
        rt = a.get("reaction_table", {})
        if not rt or len(rt) < 2:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': reaction_table assente o incompleto",
                "Aggiungi almeno 2 situazioni"))
        if a.get("role") in ("villain", "antagonist") and a.get("agenda_pressure", 0) < 5:
            findings.append(Finding("warning", "npc", aid,
                f"NPC '{name}': agenda_pressure troppo bassa per un antagonista",
                "Imposta 7-9"))
        for fld in ("goal", "current_plan", "fallback_plan"):
            if not a.get(fld):
                findings.append(Finding("info", "npc", aid,
                    f"NPC '{name}': {fld} mancante", f"Aggiungi {fld}"))
    return findings


def _clock_rules(clocks: List[Dict]) -> List[Finding]:
    findings = []
    for c in clocks:
        cid = c.get("id", "?")
        label = c.get("label", cid)
        if len(c.get("steps", [])) < 3:
            findings.append(Finding("warning", "clock", cid,
                f"Clock '{label}': meno di 3 step narrativi",
                "Aggiungi almeno 4 step con effetti progressivi"))
        if not c.get("resolution_condition"):
            findings.append(Finding("warning", "clock", cid,
                f"Clock '{label}': resolution_condition mancante",
                "Spiega come fermare il clock"))
        if not c.get("discovery_hint"):
            findings.append(Finding("info", "clock", cid,
                f"Clock '{label}': discovery_hint mancante",
                "Aggiungi un presagio narrativo"))
    return findings


def _resource_rules(resources: List, genre: str, title: str) -> List[Finding]:
    if not resources:
        horror = ("horror", "cosmic", "thriller", "survival")
        sev = "warning" if any(h in genre.lower() for h in horror) else "info"
        return [Finding(sev, "resource", title,
            f"Nessuna risorsa definita", "Considera sanità, luce, morale, tempo")]
    return []


def _clue_rules(clues: List[Dict]) -> List[Finding]:
    findings = []
    for cl in clues:
        cid = cl.get("id", "?")
        label = cl.get("label", cid)
        for fld, hint in [
            ("payoff", "cosa rivela narrativamente"),
            ("hidden_implication", "significato nascosto"),
            ("wrong_interpretations", "false interpretazioni"),
        ]:
            if not cl.get(fld):
                findings.append(Finding("info", "clue", cid,
                    f"Indizio '{label}': {fld} mancante", hint))
    return findings


def _structure_rules(data: Dict) -> List[Finding]:
    findings = []
    title = data.get("title", data.get("id", "?"))
    for fld, sev, hint in [
        ("premise", "critical", "Aggiungi una descrizione generale"),
        ("initial_hook", "critical", "Aggiungi il gancio iniziale"),
        ("actors", "critical", "Aggiungi almeno gli NPC principali"),
        ("locations", "warning", "Aggiungi le location principali"),
        ("event_clocks", "warning", "Aggiungi almeno 1 clock per l'urgenza"),
        ("finale_conditions", "info", "Definisci le condizioni di vittoria/sconfitta"),
    ]:
        val = data.get(fld)
        if not val:
            findings.append(Finding(sev, "structure", title,
                f"Campo '{fld}' mancante", hint))
    if not data.get("clues") and not data.get("story_threads"):
        findings.append(Finding("warning", "structure", title,
            "Nessun indizio né thread narrativo", "Aggiungi clues o story_threads"))
    return findings


def audit(data: Dict) -> List[Finding]:
    findings = []
    findings.extend(_structure_rules(data))
    findings.extend(_actor_rules(data.get("actors", [])))
    findings.extend(_clock_rules(data.get("event_clocks", [])))
    findings.extend(_resource_rules(
        data.get("resources", []),
        data.get("genre", ""),
        data.get("title", data.get("id", "?")),
    ))
    findings.extend(_clue_rules(data.get("clues", [])))
    return findings


def score(findings: List[Finding]) -> float:
    penalty = sum({"critical": 1.5, "warning": 0.5, "info": 0.1}[f.severity] for f in findings)
    return max(0.0, round(10.0 - penalty, 1))


# ─────────────────────────────────────────────
# Enrichment helpers
# ─────────────────────────────────────────────

def _json_from_llm(raw: str) -> Any:
    """Strip markdown fences and parse JSON."""
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _enrich_initial_hook(data: Dict) -> str:
    title = data.get("title", "")
    genre = data.get("genre", "")
    premise = (data.get("premise") or "")[:300]
    tone = data.get("tone", "")
    actors = [a.get("name", "") for a in data.get("actors", [])[:3]]
    actor_names = ", ".join(a for a in actors if a)

    prompt = f"""Avventura GURPS: {title}
Genere: {genre} — Tono: {tone}
Premessa: {premise}
NPC principali: {actor_names}

Scrivi l'initial_hook: la scena di apertura con cui il GM introduce l'avventura.
Deve essere concreto, coinvolgente, 3-4 frasi: dove si trovano i PG, cosa vedono/sentono, quale evento o NPC li trascina nell'avventura.
Rispondi SOLO con una stringa JSON (tra doppie virgolette), senza markdown."""

    try:
        raw = _llm(prompt, max_tokens=512).strip()
        if raw.startswith('"'):
            return json.loads(raw)
        return raw.strip('"')
    except Exception as e:
        print(f"[doctor] initial_hook generation failed: {e}", file=sys.stderr)
        return ""


def _enrich_npc(actor: Dict, context: str) -> Dict:
    name = actor.get("name", actor.get("id"))
    prompt = f"""Avventura: {context}

NPC: {name} — ruolo: {actor.get("role")} — obiettivo: {actor.get("goal")} — segreto: {actor.get("secret")}

Genera SOLO questo JSON (non altri campi):
{{
  "pressure_response": {{"low": "...", "medium": "...", "high": "...", "extreme": "..."}},
  "reaction_table": {{"se_minacciato": "...", "se_corrotto": "...", "se_i_pg_hanno_prove": "...", "se_alleato": "..."}},
  "current_plan": "...",
  "fallback_plan": "..."
}}
Sii specifico al personaggio. Niente testo generico."""

    try:
        enrichment = _json_from_llm(_llm(prompt, max_tokens=1024))
        return {**actor, **enrichment, "llm_enriched": True}
    except Exception as e:
        print(f"[doctor] NPC '{name}' enrichment failed: {e}", file=sys.stderr)
        return actor


def _enrich_clocks(clocks: List[Dict], context: str) -> List[Dict]:
    if not clocks:
        return clocks
    prompt = f"""Avventura: {context}

Clock da migliorare:
{json.dumps(clocks, ensure_ascii=False, indent=2)}

Per ogni clock aggiungi:
- steps: [{{"value": N, "label": "...", "effect": "..."}}] con almeno 4 step progressivi
- resolution_condition: come i giocatori fermano il clock
- discovery_hint: presagio narrativo ambiguo
- ticks_per_failure: 2

Non modificare id, label, max_value, clock_type.
Restituisci SOLO la lista JSON aggiornata."""

    try:
        enriched = _json_from_llm(_llm(prompt, max_tokens=2048))
        if isinstance(enriched, list) and len(enriched) == len(clocks):
            return enriched
    except Exception as e:
        print(f"[doctor] clock enrichment failed: {e}", file=sys.stderr)
    return clocks


def _enrich_clues(clues: List[Dict], context: str) -> List[Dict]:
    needs = [c for c in clues if not c.get("payoff") or not c.get("hidden_implication") or not c.get("wrong_interpretations")]
    if not needs:
        return clues
    prompt = f"""Avventura: {context}

Indizi da completare:
{json.dumps(needs, ensure_ascii=False, indent=2)}

Per ogni indizio aggiungi i campi mancanti:
- payoff: stringa (cosa rivela)
- hidden_implication: stringa (significato nascosto)
- wrong_interpretations: lista di 1-2 false interpretazioni

Restituisci SOLO la lista JSON degli stessi indizi con i campi aggiunti."""

    try:
        enriched_list = _json_from_llm(_llm(prompt, max_tokens=2048))
        enriched_map = {c["id"]: c for c in enriched_list if "id" in c}
        return [enriched_map.get(c.get("id"), c) for c in clues]
    except Exception as e:
        print(f"[doctor] clue enrichment failed: {e}", file=sys.stderr)
        return clues


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def run_doctor(definition: Dict, do_enrich: bool = False) -> Dict:
    """
    Audit (and optionally enrich) an adventure definition.

    Returns:
      {
        score: float,
        findings: [{severity, category, entity_id, message, fix_hint}],
        enriched_definition: dict | None,  # only if do_enrich=True
      }
    """
    findings = audit(definition)
    current_score = score(findings)

    result: Dict[str, Any] = {
        "score": current_score,
        "findings": [
            {"severity": f.severity, "category": f.category,
             "entity_id": f.entity_id, "message": f.message, "fix_hint": f.fix_hint}
            for f in findings
        ],
        "enriched_definition": None,
    }

    if not do_enrich:
        return result

    categories = {f.category for f in findings}
    context = f"{definition.get('title', '')} — {definition.get('genre', '')} — {(definition.get('premise') or '')[:200]}"
    enriched = dict(definition)

    # initial_hook
    if not enriched.get("initial_hook"):
        print("[doctor] generating initial_hook")
        hook = _enrich_initial_hook(enriched)
        if hook:
            enriched["initial_hook"] = hook

    # NPCs
    if "npc" in categories:
        npc_ids = {f.entity_id for f in findings if f.category == "npc"}
        enriched["actors"] = [
            _enrich_npc(a, context) if a.get("id") in npc_ids else a
            for a in enriched.get("actors", [])
        ]

    # Clocks
    if "clock" in categories and enriched.get("event_clocks"):
        clock_ids = {f.entity_id for f in findings if f.category == "clock"}
        title = definition.get("title", "")
        if clock_ids - {title}:  # exclude structure-level findings
            enriched["event_clocks"] = _enrich_clocks(enriched["event_clocks"], context)

    # Clues
    if "clue" in categories and enriched.get("clues"):
        enriched["clues"] = _enrich_clues(enriched["clues"], context)

    # Re-score after enrichment
    new_findings = audit(enriched)
    enriched["_doctor_score"] = score(new_findings)

    result["enriched_definition"] = enriched
    result["score_after"] = enriched["_doctor_score"]
    return result
