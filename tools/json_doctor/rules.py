"""
Audit rules for adventure JSON files.
Each rule returns a list of Finding objects.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    severity: str          # "critical" | "warning" | "info"
    category: str          # "npc" | "clock" | "resource" | "clue" | "structure" | "runtime"
    entity_id: str         # which object is affected
    message: str
    fix_hint: str = ""


def _actor_rules(actors: List[Dict]) -> List[Finding]:
    findings = []
    for a in actors:
        aid = a.get("id", "?")
        name = a.get("name", aid)

        pr = a.get("pressure_response", {})
        if not pr or len(pr) < 2:
            findings.append(Finding(
                "warning", "npc", aid,
                f"NPC '{name}': pressure_response assente o insufficiente (<2 livelli)",
                "Aggiungi chiavi 'low'/'medium'/'high'/'extreme' con comportamenti specifici"
            ))

        rt = a.get("reaction_table", {})
        if not rt or len(rt) < 2:
            findings.append(Finding(
                "warning", "npc", aid,
                f"NPC '{name}': reaction_table assente o insufficiente",
                "Aggiungi modificatori situazionali (es. 'se_minacciato', 'se_corrotto', ecc.)"
            ))

        ap = a.get("agenda_pressure", 0)
        role = a.get("role", "")
        if role in ("villain", "antagonist") and ap < 5:
            findings.append(Finding(
                "warning", "npc", aid,
                f"NPC '{name}' (antagonista): agenda_pressure={ap} troppo basso",
                "Imposta agenda_pressure 7-9 per antagonisti"
            ))

        if not a.get("goal"):
            findings.append(Finding(
                "info", "npc", aid,
                f"NPC '{name}': goal mancante",
                "Aggiungi un obiettivo narrativo esplicito"
            ))

        if not a.get("current_plan"):
            findings.append(Finding(
                "info", "npc", aid,
                f"NPC '{name}': current_plan mancante",
                "Aggiungi il piano attuale dell'NPC"
            ))

        if not a.get("fallback_plan"):
            findings.append(Finding(
                "info", "npc", aid,
                f"NPC '{name}': fallback_plan mancante",
                "Aggiungi cosa fa l'NPC se il piano principale fallisce"
            ))

    return findings


def _clock_rules(clocks: List[Dict]) -> List[Finding]:
    findings = []
    for c in clocks:
        cid = c.get("id", "?")
        label = c.get("label", cid)

        steps = c.get("steps", [])
        max_val = c.get("max_value", 8)
        if len(steps) < 3:
            findings.append(Finding(
                "warning", "clock", cid,
                f"Clock '{label}': solo {len(steps)} step su {max_val} — escalation piatta",
                "Aggiungi almeno 3-4 step con effetti narrativi progressivi"
            ))

        tpf = c.get("ticks_per_failure", 1)
        if tpf < 2:
            findings.append(Finding(
                "info", "clock", cid,
                f"Clock '{label}': ticks_per_failure={tpf} — avanza lentamente su fallimento",
                "Considera ticks_per_failure=2 per tensione realistica"
            ))

        if not c.get("resolution_condition"):
            findings.append(Finding(
                "warning", "clock", cid,
                f"Clock '{label}': resolution_condition mancante",
                "Spiega come i giocatori possono fermare il clock"
            ))

        if not c.get("discovery_hint"):
            findings.append(Finding(
                "info", "clock", cid,
                f"Clock '{label}': discovery_hint mancante",
                "Aggiungi un indizio narrativo che presagisce il clock"
            ))

    return findings


def _resource_rules(resources: List[Dict], genre: str, title: str) -> List[Finding]:
    findings = []
    if not resources:
        horror_genres = ("horror", "cosmic_horror", "thriller", "survival")
        if any(h in genre.lower() for h in horror_genres):
            findings.append(Finding(
                "warning", "resource", title,
                f"Avventura horror/thriller '{title}' senza sistemi di risorse",
                "Aggiungi risorse come sanità mentale, luce, morale, tempo"
            ))
        else:
            findings.append(Finding(
                "info", "resource", title,
                f"Avventura '{title}' senza risorse — ok se non tematico",
                "Valuta se aggiungere risorse (tempo, denaro, alleati)"
            ))
    return findings


def _clue_rules(clues: List[Dict]) -> List[Finding]:
    findings = []
    for cl in clues:
        cid = cl.get("id", "?")
        label = cl.get("label", cid)

        if not cl.get("payoff"):
            findings.append(Finding(
                "info", "clue", cid,
                f"Indizio '{label}': payoff mancante",
                "Specifica cosa rivela narrativamente questo indizio"
            ))

        if not cl.get("hidden_implication"):
            findings.append(Finding(
                "info", "clue", cid,
                f"Indizio '{label}': hidden_implication mancante",
                "Aggiungi l'implicazione nascosta (ciò che i giocatori non capiscono subito)"
            ))

        if not cl.get("wrong_interpretations"):
            findings.append(Finding(
                "info", "clue", cid,
                f"Indizio '{label}': wrong_interpretations mancante",
                "Aggiungi 1-2 false interpretazioni possibili per creare suspense"
            ))

    return findings


def _structure_rules(data: Dict) -> List[Finding]:
    findings = []
    title = data.get("title", data.get("id", "?"))

    if not data.get("premise"):
        findings.append(Finding("critical", "structure", title, "premise mancante", "Aggiungi una descrizione generale dell'avventura"))

    if not data.get("initial_hook"):
        findings.append(Finding("critical", "structure", title, "initial_hook mancante", "Aggiungi il gancio iniziale per i giocatori"))

    if not data.get("actors"):
        findings.append(Finding("critical", "structure", title, "actors vuoto — nessun NPC definito", "Aggiungi almeno gli NPC principali"))

    if not data.get("locations"):
        findings.append(Finding("warning", "structure", title, "locations vuoto", "Aggiungi le location principali"))

    if not data.get("clues") and not data.get("story_threads"):
        findings.append(Finding("warning", "structure", title, "nessun indizio né thread narrativo", "Aggiungi almeno 3-5 clues o story_threads"))

    if not data.get("event_clocks"):
        findings.append(Finding("warning", "clock", title, "nessun event_clock definito", "Aggiungi almeno 1 clock per creare urgenza"))

    if not data.get("finale_conditions"):
        findings.append(Finding("info", "structure", title, "finale_conditions mancante", "Definisci le condizioni di vittoria/sconfitta"))

    return findings


def audit(data: Dict) -> List[Finding]:
    """Run all rules against an adventure JSON and return findings."""
    findings = []
    findings.extend(_structure_rules(data))
    findings.extend(_actor_rules(data.get("actors", [])))
    findings.extend(_clock_rules(data.get("event_clocks", [])))
    findings.extend(_resource_rules(
        data.get("resources", []),
        data.get("genre", ""),
        data.get("title", data.get("id", "?"))
    ))
    findings.extend(_clue_rules(data.get("clues", [])))
    return findings


def score(findings: List[Finding]) -> float:
    """Return a quality score 0-10 based on findings."""
    penalty = 0.0
    for f in findings:
        if f.severity == "critical":
            penalty += 1.5
        elif f.severity == "warning":
            penalty += 0.5
        elif f.severity == "info":
            penalty += 0.1
    return max(0.0, round(10.0 - penalty, 1))
