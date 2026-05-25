from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any


COMBAT_SKILLS = {"combattere", "mira", "lottare", "lanciare"}
STEALTH_SKILLS = {"furtivita", "infiltrarsi", "mimetizzare", "pedinare"}
SOCIAL_SKILLS = {"persuadere", "comunicare", "interrogare", "ingannare", "intuire", "calmare", "intimidire", "etichetta", "seduzione"}
INVESTIGATION_SKILLS = {"investigare", "osservare", "analizzare", "decifrare", "cultura", "scienze", "occultismo", "seguire_tracce", "medicina", "ingegneria"}
FORCE_SKILLS = {"forzare", "demolire", "sollevare", "trasportare", "arrampicarsi", "scassinare", "manualita"}

SAFE_FALLBACKS = ["investigare", "osservare", "persuadere", "acrobazia", "sopravvivere", "cultura"]

INTENT_SKILLS: dict[str, list[str]] = {
    "investigate": ["investigare", "analizzare", "osservare", "seguire_tracce"],
    "observe": ["osservare", "investigare", "intuire"],
    "research": ["cultura", "decifrare", "storia", "linguistica", "occultismo", "teologia"],
    "deduction": ["investigare", "analizzare", "intuire"],
    "technical": ["tecnologia", "meccanica", "elettronica", "informatica", "ingegneria", "scassinare"],
    "medical": ["medicina", "curare", "biologia", "chimica"],
    "persuasion": ["persuadere", "comunicare", "etichetta"],
    "intimidation": ["intimidire", "interrogare"],
    "deception": ["ingannare", "recitazione", "seduzione"],
    "empathy": ["intuire", "calmare", "persuadere"],
    "interrogation": ["interrogare", "intuire", "persuadere", "intimidire"],
    "diplomacy": ["persuadere", "etichetta", "politica", "comunicare"],
    "stealth": ["furtivita", "mimetizzare", "infiltrarsi"],
    "stealth_tracking": ["pedinare", "furtivita", "seguire_tracce"],
    "survival": ["sopravvivere", "sopravvivenza_urbana", "navigare", "seguire_tracce"],
    "force": ["forzare", "demolire", "sollevare", "scassinare", "manualita"],
    "movement": ["acrobazia", "rapidita", "arrampicarsi", "saltare", "nuotare"],
    "combat_melee": ["combattere", "lottare"],
    "combat_ranged": ["mira", "lanciare"],
    "defense": ["schivare", "proteggere", "resistere", "strategia"],
    "leadership": ["comandare", "ispirare", "strategia"],
    "lore": ["cultura", "storia", "occultismo", "teologia", "filosofia"],
}

INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    "investigate": {"examine": 2.0, "inspect": 2.0, "search": 1.8, "investigate": 2.2, "crime scene": 2.4, "body": 1.5, "corpse": 1.7, "clue": 1.6, "evidence": 1.8, "blood": 1.2, "traccia": 1.5, "indizio": 1.8, "cerc": 1.6, "esamin": 2.0, "ispezion": 1.8},
    "observe": {"observe": 2.0, "watch": 1.7, "look": 1.5, "listen": 1.4, "notice": 1.6, "reaction": 1.2, "osserv": 2.0, "guard": 1.2, "ascolt": 1.5, "scrut": 1.6},
    "research": {"study": 2.0, "read": 1.8, "manuscript": 2.0, "tome": 2.0, "book": 1.5, "library": 1.6, "archive": 1.6, "diary": 1.6, "journal": 1.5, "ancient": 1.0, "studia": 2.0, "leggi": 1.8, "libro": 1.5, "biblioteca": 1.6, "manoscritto": 2.0},
    "technical": {"repair": 2.0, "hack": 2.0, "engine": 1.8, "machine": 1.8, "generator": 1.8, "terminal": 1.5, "computer": 1.6, "device": 1.4, "drone": 1.2, "ripar": 2.0, "motore": 1.8, "macchina": 1.7, "terminale": 1.5, "consol": 1.5},
    "medical": {"treat": 2.0, "heal": 1.8, "stabilize": 2.0, "wound": 1.8, "injured": 1.6, "poison": 1.5, "diagnose": 1.8, "body": 0.8, "corpse": 0.8, "cur": 1.8, "stabilizz": 2.0, "ferita": 1.8, "veleno": 1.5, "diagnos": 1.7},
    "persuasion": {"convince": 2.0, "persuade": 2.0, "talk": 1.2, "ask": 1.0, "calmly": 1.0, "appeal": 1.4, "negotiate": 1.5, "convinc": 2.0, "persuad": 2.0, "parl": 1.2, "chied": 1.0, "negozi": 1.5},
    "intimidation": {"threaten": 2.4, "menace": 2.0, "scare": 1.7, "pressure": 1.3, "threat": 1.5, "minacc": 2.4, "intimid": 2.2, "spavent": 1.7},
    "deception": {"lie": 2.2, "deceive": 2.0, "bluff": 2.0, "fake": 1.5, "false identity": 2.2, "disguise": 1.4, "ment": 2.0, "ingann": 2.0, "fing": 1.5},
    "empathy": {"understand emotional": 2.3, "read emotion": 2.2, "emotional state": 2.0, "feelings": 1.7, "mood": 1.4, "calm": 1.8, "terrified": 1.4, "child": 0.8, "capire emoz": 2.0, "reazione emotiva": 2.0},
    "interrogation": {"question": 2.0, "interrogate": 2.0, "witness": 0.2, "suspect": 0.4, "ask witness": 2.0, "interrog": 2.0, "testimone": 0.2, "sospett": 0.4},
    "stealth": {"hide": 2.2, "sneak": 2.2, "avoid detection": 2.4, "patrol": 1.0, "silently": 1.4, "shadow": 1.0, "nascond": 2.2, "furtiv": 2.2, "silenz": 1.6, "pattuglia": 1.0},
    "stealth_tracking": {"follow secretly": 2.4, "follow": 1.4, "secretly": 0.8, "tail": 2.0, "shadow suspect": 2.0, "track without": 2.0, "pedin": 2.0, "seguire di nascosto": 2.2},
    "survival": {"survive": 1.8, "forage": 1.7, "navigate": 1.5, "camp": 1.2, "weather": 1.2, "orient": 1.5, "sopravviv": 1.8},
    "force": {"break": 2.0, "force": 1.8, "smash": 1.8, "locked door": 2.0, "door": 0.8, "lift": 1.5, "sfond": 2.0, "romp": 1.8, "forz": 1.8, "porta chiusa": 2.0},
    "movement": {"climb": 1.8, "jump": 1.7, "run": 1.2, "cross": 1.1, "swim": 1.8, "arramp": 1.8, "salt": 1.7, "corr": 1.2, "nuot": 1.8},
    "combat_melee": {"attack": 2.2, "strike": 2.0, "stab": 2.2, "slash": 2.0, "charge": 1.8, "tackle": 1.8, "cultist": 0.5, "attacc": 2.2, "colp": 2.0, "pugnal": 2.2, "caric": 1.8},
    "combat_ranged": {"shoot": 2.4, "fire": 2.0, "rifle": 1.8, "pistol": 1.8, "bow": 1.8, "arrow": 1.5, "spar": 2.4, "fucile": 1.8, "pistola": 1.8, "arco": 1.8},
    "defense": {"protect": 1.8, "defend": 1.8, "shield": 1.5, "resist": 1.4, "blast": 1.0, "cover ally": 1.5, "protegg": 1.8, "difend": 1.8, "resist": 1.4},
    "leadership": {"command": 1.8, "coordinate": 1.7, "lead": 1.5, "plan": 1.3, "order": 1.2, "comand": 1.8, "coordin": 1.7, "guid": 1.4},
    "lore": {"ritual": 1.5, "occult": 1.6, "myth": 1.3, "legend": 1.2, "rune": 1.4, "ritual": 1.5, "occult": 1.6, "runa": 1.4},
}

TARGET_WEIGHTS: dict[str, dict[str, float]] = {
    "corpse": {"investigate": 1.0, "medical": 0.8, "intimidation": -2.0, "combat_melee": -1.5, "combat_ranged": -1.5},
    "document": {"research": 1.2, "investigate": 0.8, "combat_melee": -2.0, "stealth": -1.2},
    "witness": {"interrogation": 0.3, "persuasion": 0.7, "empathy": 0.7, "stealth": -1.0},
    "suspect": {"interrogation": 0.5, "persuasion": 0.4, "intimidation": 0.3, "stealth_tracking": 0.4, "observe": 0.5},
    "machine": {"technical": 1.4, "investigate": 0.3, "seduction": -2.0},
    "lock": {"force": 0.8, "technical": 0.6, "stealth": -0.4},
    "enemy": {"combat_melee": 0.5, "combat_ranged": 0.5, "stealth": 0.2, "persuasion": -0.2},
    "area": {"investigate": 0.6, "observe": 0.5, "stealth": -0.6},
}

DOMAIN_BONUSES: dict[str, dict[str, float]] = {
    "noir": {"investigate": 0.5, "interrogation": 0.4, "empathy": 0.2, "persuasion": 0.2},
    "detective": {"investigate": 0.6, "observe": 0.3, "interrogation": 0.4},
    "investigation": {"investigate": 0.6, "research": 0.4, "observe": 0.3},
    "horror": {"observe": 0.8, "survival": 0.6, "investigate": 0.4},
    "fantasy": {"lore": 0.3, "research": 0.2, "combat_melee": 0.1},
    "sci": {"technical": 0.4, "observe": 0.2, "investigate": 0.2},
    "cyber": {"technical": 0.6, "stealth": 0.2, "deception": 0.2},
    "military": {"combat_ranged": 0.3, "leadership": 0.3, "survival": 0.2},
    "stealth": {"stealth": 1.0, "stealth_tracking": 0.8, "observe": 0.2},
    "infiltration": {"stealth": 1.0, "technical": 0.2, "deception": 0.2},
    "battlefield": {"defense": 0.7, "leadership": 0.4, "observe": 0.2},
    "survival": {"survival": 0.6, "observe": 0.2, "movement": 0.2},
    "supernatural": {"lore": 0.5, "occult": 0.5, "research": 0.3},
}

COMBAT_VERBS = {"attack", "strike", "shoot", "stab", "slash", "fire", "assault", "charge", "tackle", "attacc", "colp", "spar", "pugnal", "caric"}
PASSIVE_VERBS = {"investigate", "search", "inspect", "ask", "negotiate", "study", "examine", "observe", "read", "cerc", "esamin", "studia", "osserv", "leggi", "parl"}


@dataclass
class SkillCandidate:
    skill: str
    score: float
    intent: str
    reasoning: str


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _contains(blob: str, pattern: str) -> bool:
    tokens = re.sub(r"[^a-zàèéìòù ]", " ", blob).split()
    if pattern == "stab":
        return any(tok in {"stab", "stabs", "stabbed", "stabbing"} for tok in tokens)
    if " " in pattern:
        return pattern in blob
    return any(tok.startswith(pattern) for tok in tokens)


def infer_target_type(action_text: str, context: dict[str, Any] | None = None) -> str:
    blob = _text(action_text)
    context = context or {}
    explicit = _text(context.get("target_type", ""))
    if explicit:
        return explicit
    checks = [
        ("corpse", ["body", "corpse", "cadaver", "dead", "murder victim", "cadavere", "corpo", "morto"]),
        ("document", ["diary", "journal", "book", "tome", "manuscript", "letter", "file", "archive", "diario", "libro", "manoscritto", "lettera", "archivio"]),
        ("witness", ["witness", "bartender", "informant", "child", "testimone", "barista", "informatore", "bambino"]),
        ("suspect", ["suspect", "guard", "cultist", "prisoner", "sospetto", "guardia", "cultista", "prigioniero"]),
        ("machine", ["machine", "engine", "generator", "terminal", "console", "device", "macchina", "motore", "generatore", "terminale", "consolle"]),
        ("lock", ["lock", "locked door", "door", "gate", "serratura", "porta chiusa", "porta", "cancello"]),
        ("enemy", ["enemy", "orc", "soldier", "patrol", "monster", "nemico", "orco", "soldato", "pattuglia", "mostro"]),
    ]
    for target, terms in checks:
        if any(_contains(blob, term) for term in terms):
            return target
    return "area"


def infer_interaction_mode(action_text: str, context: dict[str, Any] | None = None) -> str:
    blob = _text(action_text)
    if any(_contains(blob, w) for w in COMBAT_VERBS):
        return "aggressive"
    if any(_contains(blob, w) for w in ["threaten", "minacc", "intimid"]):
        return "coercive"
    if any(_contains(blob, w) for w in ["lie", "bluff", "fake", "ment", "ingann", "fing"]):
        return "deceptive"
    if any(_contains(blob, w) for w in ["calm", "convince", "persuade", "negotiate", "convinc", "persuad", "negozi"]):
        return "cooperative"
    if any(_contains(blob, w) for w in ["hide", "sneak", "secretly", "avoid detection", "nascond", "furtiv", "silenz"]):
        return "covert"
    if any(_contains(blob, w) for w in ["repair", "hack", "ripar", "terminal", "machine", "macchina"]):
        return "technical"
    if any(_contains(blob, w) for w in ["read", "study", "analyze", "leggi", "studia", "analizz"]):
        return "analytical"
    return "exploratory"


def extract_action_intent(action_text: str, context: dict[str, Any] | None = None) -> dict:
    blob = _text(action_text)
    context = context or {}
    scores = {intent: 0.0 for intent in INTENT_SKILLS}
    evidence: dict[str, list[str]] = {intent: [] for intent in INTENT_SKILLS}
    for intent, weights in INTENT_WEIGHTS.items():
        for pattern, weight in weights.items():
            if _contains(blob, pattern):
                scores[intent] += weight
                evidence[intent].append(pattern)

    target_type = infer_target_type(action_text, context)
    for intent, bonus in TARGET_WEIGHTS.get(target_type, {}).items():
        if intent in scores:
            scores[intent] += bonus
            evidence[intent].append(f"target:{target_type}")

    domain_blob = " ".join(str(x) for x in [
        context.get("scene_type", ""),
        context.get("genre", ""),
        " ".join(context.get("location_tags", []) or []),
        context.get("active_objective", ""),
    ]).lower()
    for domain, bonuses in DOMAIN_BONUSES.items():
        if domain in domain_blob:
            for intent, bonus in bonuses.items():
                if intent in scores:
                    scores[intent] += bonus
                    evidence[intent].append(f"domain:{domain}")

    if context.get("combat_active"):
        scores["defense"] += 0.3
        if any(_contains(blob, w) for w in COMBAT_VERBS):
            scores["combat_melee"] += 0.5
            scores["combat_ranged"] += 0.5
    elif not any(_contains(blob, w) for w in COMBAT_VERBS):
        scores["combat_melee"] -= 3.0
        scores["combat_ranged"] -= 3.0

    best_intent, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        best_intent, best_score = "investigate", 0.35
        evidence[best_intent].append("safe_default")

    mode = infer_interaction_mode(action_text, context)
    return {
        "intent": best_intent,
        "intent_scores": scores,
        "evidence": evidence.get(best_intent, []),
        "interaction_mode": mode,
        "target_type": target_type,
        "context": context,
        "is_combat_intent": best_intent in {"combat_melee", "combat_ranged"} and any(_contains(blob, w) for w in COMBAT_VERBS),
        "is_stealth_intent": best_intent in {"stealth", "stealth_tracking"} and mode == "covert",
    }


def generate_skill_candidates(intent_data: dict, available_skills: dict[str, int] | None = None) -> list[dict]:
    intent = intent_data.get("intent", "investigate")
    candidates = []
    for rank, skill in enumerate(INTENT_SKILLS.get(intent, SAFE_FALLBACKS)):
        base = max(0.25, 0.95 - rank * 0.09)
        if available_skills and skill in available_skills:
            base += min(0.12, max(0, available_skills[skill] - 10) * 0.01)
        candidates.append({
            "skill": skill,
            "score": round(base, 3),
            "intent": intent,
            "reasoning": f"skill coerente con intent {intent}",
        })
    return candidates


def score_skill_candidates(candidates: list[dict], intent_data: dict, context: dict[str, Any] | None = None) -> list[dict]:
    context = context or {}
    target = intent_data.get("target_type", "")
    mode = intent_data.get("interaction_mode", "")
    action = _text(context.get("action_text", ""))
    scored = []
    for cand in candidates:
        c = dict(cand)
        skill = c["skill"]
        score = float(c.get("score", 0.0))
        rejected_reason = validate_skill_against_context(skill, intent_data, context, return_reason=True)
        if rejected_reason:
            c["score"] = -1.0
            c["rejected"] = True
            c["rejected_reason"] = rejected_reason
            scored.append(c)
            continue
        if target == "corpse" and skill in {"medicina", "investigare", "analizzare"}:
            score += 0.08
        if target == "document" and skill in {"cultura", "decifrare", "storia", "occultismo"}:
            score += 0.08
        if mode == "cooperative" and skill in {"persuadere", "comunicare"}:
            score += 0.07
        if mode == "cooperative" and skill == "calmare":
            score += 0.16
        if mode == "deceptive" and skill == "ingannare":
            score += 0.1
        if mode == "coercive" and skill == "intimidire":
            score += 0.12
        if "poison" in action or "veleno" in action:
            if skill in {"medicina", "chimica", "biologia"}:
                score += 0.14
        c["score"] = round(min(1.0, score), 3)
        c["rejected"] = False
        scored.append(c)
    return sorted(scored, key=lambda x: x.get("score", -1), reverse=True)


def validate_skill_against_context(skill: str, intent_data: dict, context: dict[str, Any] | None = None, return_reason: bool = False):
    context = context or {}
    action = _text(context.get("action_text", ""))
    intent = intent_data.get("intent", "")
    target = intent_data.get("target_type", "")
    mode = intent_data.get("interaction_mode", "")
    combat_active = bool(context.get("combat_active"))
    has_combat_verb = any(_contains(action, w) for w in COMBAT_VERBS)

    reason = ""
    if skill in COMBAT_SKILLS and not (has_combat_verb or combat_active or intent in {"combat_melee", "combat_ranged"}):
        reason = "combat skill senza intento aggressivo"
    elif skill in {"intimidire"} and target in {"corpse", "document", "machine", "area"} and mode != "coercive":
        reason = f"intimidazione assurda su target {target}"
    elif skill in STEALTH_SKILLS and not (mode == "covert" or intent in {"stealth", "stealth_tracking"}):
        reason = "stealth senza evitare rilevamento/infiltrazione"
    elif skill == "seduzione" and target in {"corpse", "document", "machine", "lock", "area"}:
        reason = f"seduzione assurda su target {target}"
    elif skill in COMBAT_SKILLS and any(_contains(action, w) for w in PASSIVE_VERBS) and not has_combat_verb:
        reason = "combat non valido su azione passiva"
    elif skill in {"furtivita", "infiltrarsi"} and intent in {"investigate", "research", "observe", "medical", "technical", "persuasion"}:
        reason = f"stealth non coerente con intent {intent}"

    if return_reason:
        return reason
    return not reason


def select_best_skill(
    action_text: str,
    context: dict[str, Any] | None = None,
    available_skills: dict[str, int] | None = None,
) -> dict:
    context = dict(context or {})
    context["action_text"] = action_text
    intent_data = extract_action_intent(action_text, context)
    candidates = generate_skill_candidates(intent_data, available_skills)
    scored = score_skill_candidates(candidates, intent_data, context)
    valid = [c for c in scored if not c.get("rejected") and c.get("score", 0) >= 0]
    selected = valid[0] if valid else None
    rejected = [c for c in scored if c.get("rejected")]

    if not selected or selected["score"] < 0.45:
        for fallback in SAFE_FALLBACKS:
            fallback_reason = validate_skill_against_context(fallback, intent_data, context, return_reason=True)
            if not fallback_reason:
                selected = {
                    "skill": fallback,
                    "score": 0.45,
                    "intent": intent_data["intent"],
                    "reasoning": "fallback sicuro per bassa confidenza",
                }
                break

    result = {
        "selected_skill": selected["skill"] if selected else "investigare",
        "confidence": round(float(selected.get("score", 0.45) if selected else 0.45), 3),
        "reasoning": selected.get("reasoning", "") if selected else "fallback sicuro",
        "candidate_skills": scored,
        "rejected_candidates": rejected,
        "intent": intent_data["intent"],
        "interaction_mode": intent_data["interaction_mode"],
        "target_type": intent_data["target_type"],
        "intent_data": intent_data,
    }

    if os.getenv("ACTION_RESOLUTION_DEBUG", "").lower() in {"1", "true", "yes", "on"}:
        print(
            "[action_intent]",
            {
                "action": action_text,
                "intent": result["intent"],
                "target": result["target_type"],
                "selected": result["selected_skill"],
                "confidence": result["confidence"],
                "candidates": [(c["skill"], c["score"], c.get("rejected_reason")) for c in scored[:6]],
            },
        )
    return result
