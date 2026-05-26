"""LLM-driven extractors for narrative content the regex pass misses.

The regex extractors in ``pdf_structure_extractor`` only match clues / NPCs /
encounters that are *labelled* with prefixes like ``Clue:`` or ``Indizio:``.
Most real modules write clues inline in prose, so the regex pass recovers a
small fraction. This module asks the LLM to mine that prose and return
structured items in the same shape the runtime shape builder consumes.

Public API:
    extract_clues_with_llm(text, structure, *, title="") -> list[dict] | None
    enrich_actors_with_llm(text, structure, *, title="") -> list[dict] | None

Default-off. Enable with ``GURPS_ENABLE_LLM_EXTRACTORS=1`` *and* a configured
text provider. Returns ``None`` when disabled or on any failure — callers
keep the regex-extracted content unchanged.
"""
from __future__ import annotations

import os
from typing import Any


def _llm_extractors_enabled() -> bool:
    return os.getenv("GURPS_ENABLE_LLM_EXTRACTORS", "").strip().lower() in {"1", "true", "yes", "on"}


_CLUE_PROMPT = """Sei un analista di moduli GDR. Devi estrarre gli INDIZI giocabili da un'avventura.

Un indizio e un dettaglio concreto che i PG possono scoprire e che li avvicina alla soluzione: una fotografia, un documento, una testimonianza, una traccia fisica, una contraddizione tra versioni, un oggetto fuori posto. NON sono indizi: descrizioni d'ambiente generiche, regole di sistema, blocchi statistici, ringraziamenti.

Per ogni indizio estrai:
- label: nome breve (max 90 char)
- text: la frase originale o un riassunto fedele (max 240 char)
- type: uno tra "physical_evidence", "testimony", "document", "scene_observation", "forensic", "contradiction"
- source_location: SCENA GIOCABILE dove i PG lo scopriranno durante la sessione.
  REGOLE STRINGENTI:
  - DEVE essere una stanza/luogo/PNG dalla lista "Sezioni/room note" qui sotto.
  - MAI usare "Adventure Background", "About the Adventure", "Adventure Summary",
    "Adventure Hook", "Introduction", "Setting", "Credits" o nomi di sezioni meta.
  - Se l'indizio descrive backstory, scegli la scena ATTUALE dove i PG lo
    incontreranno (un PNG che lo racconta, una stanza dove si trova l'oggetto,
    un documento in archivio).
  - In ultima istanza, prefersci la prima stanza/luogo che ha senso narrativamente.
- reveals: cosa fa capire ai giocatori (max 180 char)
- hidden_implication: l'implicazione nascosta, opzionale (max 180 char)
- payoff: come l'indizio cambia le scelte successive (max 140 char)
- possible_actions: 1-3 azioni concrete che i PG possono fare con questo indizio
  (frasi complete con verbo + oggetto, NON solo "Cercare X"; SEMPRE in italiano, anche se il modulo è in inglese)

Titolo modulo: {title}

Sezioni/room note (per source_location):
{sections}

Indizi gia trovati via regex (NON ripeterli, integrali se vuoi):
{existing}

Estratto del modulo (max ~7000 char):
\"\"\"
{excerpt}
\"\"\"

Rispondi SOLO con JSON di questa forma:
{{
  "clues": [
    {{
      "label": "...",
      "text": "...",
      "type": "physical_evidence",
      "source_location": "...",
      "reveals": "...",
      "hidden_implication": "...",
      "payoff": "...",
      "possible_actions": ["...", "..."]
    }}
  ]
}}

Estrai tra 4 e 14 indizi. Se il modulo non ne ha abbastanza, restituisci tutti quelli reali e basta.
"""


_META_LOCATIONS = {
    "adventure background", "about the adventure", "adventure summary",
    "adventure hook", "introduction", "setting", "credits", "the adventure",
    "premise", "synopsis", "summary", "preface", "foreword",
    "about 1shot", "about 1shot adventures", "running the adventure",
    "gm notes", "gm's notes", "notes for the gm",
}


def _rewrite_meta_location(loc: str, fallback_choices: list[str]) -> str:
    """If the LLM tagged a clue with a meta-section name, rewrite to the
    first plausible playable location. Returns the original if it's fine.
    """
    low = " ".join(str(loc or "").lower().split())
    if not low or low not in _META_LOCATIONS:
        return loc
    return fallback_choices[0] if fallback_choices else loc


_VALID_TYPES = {
    "physical_evidence",
    "testimony",
    "document",
    "scene_observation",
    "forensic",
    "contradiction",
}


def _format_sections(structure: dict) -> str:
    rooms = (structure or {}).get("rooms") or []
    sections = (structure or {}).get("sections") or []
    lines: list[str] = []
    for room in rooms[:30]:
        name = (room.get("name") or room.get("description") or "").strip()
        if name:
            lines.append(f"- {name[:120]}")
    for section in sections[:25]:
        name = (section.get("title") or "").strip()
        if name:
            lines.append(f"- {name[:120]}")
    return "\n".join(lines) or "(nessuna sezione identificata)"


def _format_existing_clues(structure: dict) -> str:
    clues = (structure or {}).get("clues") or []
    if not clues:
        return "(nessuno)"
    return "\n".join(f"- {(c.get('label') or '')[:120]}" for c in clues[:20] if isinstance(c, dict))


def _truncate_excerpt(text: str, limit: int = 7000) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head - 16
    return text[:head] + "\n[...]\n" + text[-tail:]


def _normalize_clue(item: Any, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    label = str(item.get("label") or "").strip()
    text = str(item.get("text") or label).strip()
    if not label and not text:
        return None
    kind = str(item.get("type") or "physical_evidence").strip().lower()
    if kind not in _VALID_TYPES:
        kind = "physical_evidence"

    actions = item.get("possible_actions") or []
    if isinstance(actions, str):
        actions = [actions]
    actions = [str(a).strip()[:160] for a in actions if str(a or "").strip()][:5]

    return {
        "id": f"llm_clue_{index}",
        "label": (label or text)[:160],
        "text": text[:480],
        "type": kind,
        "source_location": str(item.get("source_location") or "").strip()[:160],
        "reveals": str(item.get("reveals") or "").strip()[:240],
        "hidden_implication": str(item.get("hidden_implication") or "").strip()[:240],
        "payoff": str(item.get("payoff") or "").strip()[:180],
        "possible_actions": actions,
        "source_ref": {"section": str(item.get("source_location") or "").strip()[:120]},
        "source_status": "inferred",
        "is_preserved_from_pdf": False,
        "confidence": 0.75,
        "llm_extracted": True,
    }


_REGEX_LABEL_LOW_VALUE_MARKERS = (
    "dettaglio verificabile",
    "documento concreto",
    "indizio strutturale",
    "elemento canonico",
    "prova generica",
)


def _looks_low_value_regex_label(label: str) -> bool:
    low = str(label or "").lower().strip()
    if not low:
        return True
    if any(marker in low for marker in _REGEX_LABEL_LOW_VALUE_MARKERS):
        return True
    # Strip whitespace + ignore short connector words; a clue needs at least
    # 3 content-carrying tokens to be worth keeping over an LLM-mined one.
    stop = {"di", "in", "il", "la", "lo", "i", "le", "un", "una", "uno", "del", "della", "dei", "degli", "delle", "the", "a", "an", "of", "on", "at", "to"}
    content_words = [w for w in low.split() if w not in stop and len(w) > 1]
    if len(content_words) <= 2:
        return True
    return False


def _merge_with_existing(existing: list[dict], llm_clues: list[dict]) -> list[dict]:
    """Append LLM clues alongside the regex ones, deduplicating on a first-40
    char label prefix. When the LLM produced at least 3 concrete clues, drop
    regex clues whose label is a low-value placeholder (these get rewritten
    downstream by ``semantic_concretizer`` into ``"Dettaglio verificabile in
    X"`` noise that crowds the real evidence list).
    """
    def key(label: str) -> str:
        return " ".join(str(label or "").lower().split())[:40]

    if len(llm_clues) >= 3:
        kept_existing = [
            c for c in existing
            if isinstance(c, dict) and not _looks_low_value_regex_label(c.get("label") or "")
        ]
    else:
        kept_existing = [c for c in existing if isinstance(c, dict)]

    seen = {key(c.get("label") or "") for c in kept_existing}
    merged = list(kept_existing)
    for clue in llm_clues:
        k = key(clue.get("label") or "")
        if k and k not in seen:
            merged.append(clue)
            seen.add(k)
    return merged


def extract_clues_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
) -> list[dict] | None:
    """Run the LLM clue extractor and merge with regex output.

    Returns the merged list to drop into ``structure['clues']``, or ``None``
    when disabled / unavailable / on failure.
    """
    if not _llm_extractors_enabled():
        return None

    try:
        from . import claude_service
    except Exception:
        return None

    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    prompt = _CLUE_PROMPT.format(
        title=title or "(senza titolo)",
        sections=_format_sections(structure),
        existing=_format_existing_clues(structure),
        excerpt=_truncate_excerpt(text or ""),
    )

    try:
        raw = claude_service._call_text_model(prompt, max_tokens=6000)
    except Exception as exc:
        print(f"[llm_extractors] clue call fallita: {type(exc).__name__}: {exc}")
        return None

    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_extractors] parse JSON fallito: {exc}")
        return None

    items = parsed.get("clues") or []
    if not isinstance(items, list) or not items:
        return None

    # Build a fallback playable-location list from rooms first, then sections
    # that DON'T match meta-section names.
    rooms = (structure or {}).get("rooms") or []
    sections = (structure or {}).get("sections") or []
    fallback_locations: list[str] = []
    for room in rooms[:30]:
        name = (room.get("name") or "").strip()
        if name and name.lower() not in _META_LOCATIONS:
            fallback_locations.append(name)
    for section in sections[:30]:
        name = (section.get("title") or "").strip()
        if name and name.lower() not in _META_LOCATIONS and name not in fallback_locations:
            fallback_locations.append(name)

    llm_clues: list[dict] = []
    for idx, item in enumerate(items, start=1):
        normalized = _normalize_clue(item, idx)
        if normalized:
            rewritten = _rewrite_meta_location(normalized.get("source_location") or "", fallback_locations)
            normalized["source_location"] = rewritten
            normalized["source_ref"] = {"section": rewritten}
            llm_clues.append(normalized)
    if not llm_clues:
        return None

    return _merge_with_existing(structure.get("clues") or [], llm_clues)


_ACTOR_PROMPT = """Sei un analista di moduli GDR. Devi arricchire i PNG (personaggi non giocanti) di un modulo con agende operative concrete e giocabili a runtime.

NON inventare PNG nuovi. Lavora SOLO sulla lista fornita; per ognuno estrai dal testo del modulo quanto serve a un Master IA per farlo agire.

Per ogni PNG estrai:
- name: nome canonico (copia da input)
- role: uno tra "antagonist", "ally", "witness", "victim", "patron", "rival", "neutral"
- goal: obiettivo concreto e attuale, una frase (max 160 char). Cosa vuole ottenere ORA.
- fear: cosa teme di piu, una frase (max 120 char)
- secret: cio che nasconde ai PG (max 200 char). Stringa vuota se non ha segreti reali.
- current_plan: cosa sta facendo gia all'inizio dell'avventura (max 160 char)
- fallback_plan: cosa fa se il piano principale fallisce (max 160 char)
- knows: lista di 0-3 fatti operativi che conosce
- wants: lista di 0-3 esiti che vuole
- avoids: lista di 0-3 esiti che vuole evitare
- relationships: 0-3 oggetti {{"name": "...", "type": "ally|rival|family|patron|enemy|lover|subordinate", "note": "..."}}
- pressure_response: oggetto {{"low": "...", "medium": "...", "high": "...", "critical": "..."}} con risposta CONCRETA del PNG a livelli crescenti di pressione dai PG (verbi attivi, non parole generiche tipo "osserva")

Titolo modulo: {title}

PNG da arricchire (nome + paragrafo descrittivo dal modulo):
{actors}

Estratto del modulo (max ~6000 char):
\"\"\"
{excerpt}
\"\"\"

Rispondi SOLO con JSON di questa forma:
{{
  "actors": [
    {{
      "name": "...",
      "role": "antagonist",
      "goal": "...",
      "fear": "...",
      "secret": "...",
      "current_plan": "...",
      "fallback_plan": "...",
      "knows": ["..."],
      "wants": ["..."],
      "avoids": ["..."],
      "relationships": [{{"name": "...", "type": "ally", "note": "..."}}],
      "pressure_response": {{"low": "...", "medium": "...", "high": "...", "critical": "..."}}
    }}
  ]
}}
"""


_VALID_ROLES = {"antagonist", "ally", "witness", "victim", "patron", "rival", "neutral"}
_VALID_REL_TYPES = {"ally", "rival", "family", "patron", "enemy", "lover", "subordinate"}


def _format_actors_for_prompt(structure: dict) -> str:
    npcs = (structure or {}).get("npcs") or []
    if not npcs:
        return "(nessun PNG estratto)"
    lines: list[str] = []
    for idx, npc in enumerate(npcs[:20], start=1):
        if not isinstance(npc, dict):
            continue
        label = (npc.get("label") or npc.get("name") or "").strip()
        desc = (npc.get("text") or npc.get("description") or "").strip()
        if not label:
            continue
        lines.append(f"{idx}. {label[:120]}\n   {desc[:400]}")
    return "\n".join(lines) or "(nessun PNG estratto)"


def _normalize_str_list(value: Any, limit_item: int = 160, max_items: int = 5) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        s = str(item or "").strip()
        if s:
            out.append(s[:limit_item])
        if len(out) >= max_items:
            break
    return out


def _normalize_relationships(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:120]
        if not name:
            continue
        rel_type = str(item.get("type") or "").strip().lower()
        if rel_type not in _VALID_REL_TYPES:
            rel_type = "ally"
        out.append({
            "name": name,
            "type": rel_type,
            "note": str(item.get("note") or "").strip()[:160],
        })
        if len(out) >= 4:
            break
    return out


def _normalize_pressure(value: Any) -> dict[str, str]:
    default = {
        "low": "osserva e prepara",
        "medium": "tratta o negozia",
        "high": "agisce concretamente",
        "critical": "forza una svolta",
    }
    if not isinstance(value, dict):
        return default
    out: dict[str, str] = {}
    for key in ("low", "medium", "high", "critical"):
        out[key] = str(value.get(key) or default[key]).strip()[:160]
    return out


def _normalize_actor(item: Any) -> dict | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name") or "").strip()
    if not name:
        return None
    role = str(item.get("role") or "neutral").strip().lower()
    if role not in _VALID_ROLES:
        role = "neutral"
    return {
        "name": name,
        "role": role,
        "goal": str(item.get("goal") or "").strip()[:220],
        "fear": str(item.get("fear") or "").strip()[:160],
        "secret": str(item.get("secret") or "").strip()[:240],
        "current_plan": str(item.get("current_plan") or "").strip()[:220],
        "fallback_plan": str(item.get("fallback_plan") or "").strip()[:220],
        "knows": _normalize_str_list(item.get("knows"), max_items=4),
        "wants": _normalize_str_list(item.get("wants"), max_items=4),
        "avoids": _normalize_str_list(item.get("avoids"), max_items=4),
        "relationships": _normalize_relationships(item.get("relationships")),
        "pressure_response": _normalize_pressure(item.get("pressure_response")),
        "llm_enriched": True,
    }


def _match_existing_actor(name: str, existing: list[dict]) -> int | None:
    if not name:
        return None
    target = " ".join(name.lower().split())
    for idx, npc in enumerate(existing):
        if not isinstance(npc, dict):
            continue
        for key in ("label", "name"):
            candidate = " ".join(str(npc.get(key) or "").lower().split())
            if candidate and (candidate == target or target in candidate or candidate in target):
                return idx
    return None


def _call_actor_batch(claude_service, prompt: str, *, max_tokens: int) -> list[dict] | None:
    """Single LLM call returning the list of actor dicts, or None on any
    failure. Defensive against empty Anthropic content (which surfaces as
    IndexError in _call_claude when ``response.content`` is empty).
    """
    try:
        raw = claude_service._call_text_model(prompt, max_tokens=max_tokens)
    except IndexError as exc:
        # Anthropic returned empty content (rare, transient).
        print(f"[llm_extractors] actor call ricevuta vuota: {exc}")
        return None
    except Exception as exc:
        print(f"[llm_extractors] actor call fallita: {type(exc).__name__}: {exc}")
        return None
    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_extractors] parse actor JSON fallito: {exc}")
        return None
    items = parsed.get("actors") or []
    return items if isinstance(items, list) else None


def enrich_actors_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
) -> list[dict] | None:
    """Enrich regex-extracted NPCs with LLM-derived agendas.

    Batches NPCs in groups of 5 — large groups (Uzrah has 16) sometimes get
    truncated by Anthropic returning empty content. Smaller batches are more
    reliable and total cost is the same since each NPC contributes the same
    output tokens.
    """
    if not _llm_extractors_enabled():
        return None

    existing = list((structure or {}).get("npcs") or [])
    if not existing:
        return None

    try:
        from . import claude_service
    except Exception:
        return None
    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    enriched = [dict(npc) for npc in existing if isinstance(npc, dict)]
    any_match = False
    excerpt = _truncate_excerpt(text or "", limit=6000)
    BATCH_SIZE = 5

    for batch_start in range(0, len(enriched), BATCH_SIZE):
        batch = enriched[batch_start:batch_start + BATCH_SIZE]
        sub_structure = {"npcs": batch}
        prompt = _ACTOR_PROMPT.format(
            title=title or "(senza titolo)",
            actors=_format_actors_for_prompt(sub_structure),
            excerpt=excerpt,
        )
        items = _call_actor_batch(claude_service, prompt, max_tokens=4000)
        if not items:
            continue
        for item in items:
            normalized = _normalize_actor(item)
            if not normalized:
                continue
            idx = _match_existing_actor(normalized["name"], enriched)
            if idx is None:
                continue
            target = enriched[idx]
            target.update({k: v for k, v in normalized.items() if v not in (None, "", [], {})})
            target["llm_enriched"] = True
            any_match = True

    return enriched if any_match else None


_EXTRACT_ACTORS_PROMPT = """Sei un analista di moduli GDR. Estrai TUTTI i personaggi non giocanti (NPC/PNG) importanti da questo modulo.

Un NPC importante è: un antagonista, un alleato, un testimone, un contatto, una vittima nominata, un PNG con cui i PG interagiscono. NON includere: mostri generici senza nome, PNG di folla, oggetti personificati.

Titolo modulo: {title}

Testo del modulo (estratto):
\"\"\"
{excerpt}
\"\"\"

Ritorna un JSON con questa struttura esatta:
{{
  "actors": [
    {{
      "id": "actor_slug_minuscolo",
      "name": "Nome Completo",
      "role": "antagonist|ally|witness|contact|victim|neutral",
      "description": "Descrizione fisica e comportamentale in 1-2 frasi",
      "motivation": "Cosa vuole questo personaggio",
      "secret": "Cosa nasconde (null se non ha segreti evidenti)",
      "location": "Dove si trova normalmente",
      "attitude": "friendly|neutral|hostile|deceptive|suspicious"
    }}
  ]
}}

Estrai almeno 2 NPC, massimo 12. Solo JSON, nessun testo aggiuntivo.
"""


def extract_actors_with_llm(
    text: str,
    *,
    title: str = "",
) -> list[dict] | None:
    """Estrae NPC da zero dal testo grezzo quando l'heuristic non ne trova."""
    if not _llm_extractors_enabled():
        return None
    try:
        from . import claude_service
    except Exception:
        return None
    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    excerpt = _truncate_excerpt(text or "", limit=8000)
    prompt = _EXTRACT_ACTORS_PROMPT.format(title=title or "(senza titolo)", excerpt=excerpt)
    try:
        raw = claude_service._call_claude(prompt, max_tokens=3000)
    except Exception as exc:
        print(f"[llm_extractors] extract_actors fallito: {exc}")
        return None
    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_extractors] extract_actors parse fallito: {exc}")
        return None
    items = parsed.get("actors") or []
    if not isinstance(items, list) or len(items) == 0:
        return None
    # Normalizza verso il formato atteso dal pipeline
    result = []
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = str(item["name"])
        slug = name.lower().replace(" ", "_").replace("'", "").replace("-", "_")[:30]
        result.append({
            "id": item.get("id") or f"actor_{slug}",
            "name": name,
            "role": str(item.get("role") or "neutral"),
            "description": str(item.get("description") or ""),
            "goal": str(item.get("motivation") or ""),
            "current_plan": "",
            "fallback_plan": "",
            "pressure_response": "",
            "knows": [],
            "resources": [],
            "secret": str(item.get("secret") or "") if item.get("secret") else "",
            "location": str(item.get("location") or ""),
            "attitude": str(item.get("attitude") or "neutral"),
            "llm_extracted": True,
        })
    return result if result else None


_REVELATION_PROMPT = """Sei un analista di moduli GDR. Devi costruire il GRAFO DI DEDUZIONE di un'avventura.

Una rivelazione (revelation) e una verita centrale che i PG devono dedurre combinando piu indizi di tipi diversi. NON deve essere derivabile da un solo indizio: serve corroborazione (testimony + physical_evidence, o document + forensic, ecc.).

Indizi tipizzati gia disponibili (con id e tipo):
{clues}

Rivelazioni gia presenti nel modulo (se vuoi riusarle/integrarle):
{existing_revelations}

Titolo: {title}

Estratto del modulo (max ~5500 char):
\"\"\"
{excerpt}
\"\"\"

Costruisci 3-6 rivelazioni che insieme coprono la trama centrale. Per ognuna:
- statement: la verita affermativa (max 200 char), NON una domanda
- required_clue_ids: lista degli id di indizi necessari (almeno 2, max 5)
- required_evidence_kinds: lista dei TIPI necessari (almeno 2 tipi diversi)
- minimum_independent_kinds: numero minimo di tipi indipendenti per dedurre (default 2)
- red_herring_clue_ids: 0-2 id di indizi che SEMBRANO supportarla ma non lo fanno
- payoff: cosa cambia nel gioco quando viene dedotta (max 160 char)
- thread_id: identificatore breve della pista narrativa (es. "T_identita", "T_rituale")

Rispondi SOLO con JSON di questa forma:
{{
  "revelations": [
    {{
      "statement": "...",
      "required_clue_ids": ["..."],
      "required_evidence_kinds": ["physical_evidence", "testimony"],
      "minimum_independent_kinds": 2,
      "red_herring_clue_ids": [],
      "payoff": "...",
      "thread_id": "T_..."
    }}
  ]
}}
"""


def _format_clues_for_revelation_prompt(structure: dict) -> str:
    clues = (structure or {}).get("clues") or []
    if not clues:
        return "(nessun indizio disponibile)"
    lines: list[str] = []
    for clue in clues[:30]:
        if not isinstance(clue, dict):
            continue
        cid = clue.get("id") or ""
        kind = clue.get("type") or "?"
        label = (clue.get("label") or "").strip()[:80]
        loc = (clue.get("source_location") or "").strip()[:50]
        lines.append(f"- {cid} [{kind}] {label}  @ {loc}")
    return "\n".join(lines)


def _format_existing_revelations(structure: dict) -> str:
    revelations = (structure or {}).get("revelations") or []
    if not revelations:
        return "(nessuna)"
    lines: list[str] = []
    for rev in revelations[:10]:
        if not isinstance(rev, dict):
            continue
        statement = (rev.get("statement") or rev.get("true_answer") or rev.get("question") or "").strip()[:120]
        if statement:
            lines.append(f"- {statement}")
    return "\n".join(lines) or "(nessuna)"


def _normalize_revelation(item: Any, index: int, known_clue_ids: set[str]) -> dict | None:
    if not isinstance(item, dict):
        return None
    statement = str(item.get("statement") or "").strip()
    if not statement:
        return None
    required_ids_raw = item.get("required_clue_ids") or []
    if isinstance(required_ids_raw, str):
        required_ids_raw = [required_ids_raw]
    required = [str(x).strip() for x in required_ids_raw if str(x).strip() in known_clue_ids][:5]
    if len(required) < 2:
        # Skip revelations that can't actually require corroboration
        return None
    kinds_raw = item.get("required_evidence_kinds") or []
    if isinstance(kinds_raw, str):
        kinds_raw = [kinds_raw]
    kinds = [str(k).strip().lower() for k in kinds_raw if str(k or "").strip()]
    kinds = [k for k in kinds if k in _VALID_TYPES][:4]
    red_herrings_raw = item.get("red_herring_clue_ids") or []
    if isinstance(red_herrings_raw, str):
        red_herrings_raw = [red_herrings_raw]
    red_herrings = [str(x).strip() for x in red_herrings_raw if str(x).strip() in known_clue_ids][:3]
    try:
        min_kinds = int(item.get("minimum_independent_kinds") or max(2, len(set(kinds))))
    except (TypeError, ValueError):
        min_kinds = 2
    min_kinds = max(1, min(min_kinds, len(set(kinds)) or 2))
    return {
        "id": f"llm_rev_{index}",
        "thread_id": str(item.get("thread_id") or f"T_llm_{index}").strip()[:40],
        "statement": statement[:240],
        "required_clues": required,
        "required_evidence_kinds": list(set(kinds)),
        "minimum_independent_kinds": min_kinds,
        "red_herring_clues": red_herrings,
        "payoff": str(item.get("payoff") or "").strip()[:200],
        "status": "hidden",
        "llm_generated": True,
    }


def build_deduction_graph_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
) -> list[dict] | None:
    """Build a corroboration-required revelation graph from typed clues.

    Returns a list of revelation dicts ready to feed into the runtime, or
    ``None`` when disabled / unavailable / on failure. Each revelation
    requires multiple clues of distinct kinds — eliminates the "find one
    document, win the case" template.
    """
    if not _llm_extractors_enabled():
        return None

    clues = (structure or {}).get("clues") or []
    typed_clues = [c for c in clues if isinstance(c, dict) and c.get("id")]
    if len(typed_clues) < 3:
        return None

    try:
        from . import claude_service
    except Exception:
        return None
    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    known_ids = {str(c.get("id")) for c in typed_clues}
    prompt = _REVELATION_PROMPT.format(
        title=title or "(senza titolo)",
        clues=_format_clues_for_revelation_prompt(structure),
        existing_revelations=_format_existing_revelations(structure),
        excerpt=_truncate_excerpt(text or "", limit=5500),
    )

    try:
        raw = claude_service._call_text_model(prompt, max_tokens=3000)
    except Exception as exc:
        print(f"[llm_extractors] revelation call fallita: {type(exc).__name__}: {exc}")
        return None
    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_extractors] parse revelation JSON fallito: {exc}")
        return None

    items = parsed.get("revelations") or []
    if not isinstance(items, list) or not items:
        return None
    revelations: list[dict] = []
    for idx, item in enumerate(items, start=1):
        normalized = _normalize_revelation(item, idx, known_ids)
        if normalized:
            revelations.append(normalized)
    return revelations or None


_SYNTHESIS_PROMPT = """Sei un editor di moduli GDR. Devi scrivere la sinossi giocabile di un'avventura per il Master IA.

Titolo: {title}
Genere/archetipo identificati: {genre} / {archetype}
Tono: {tone}

Indizi tipizzati (id+tipo+label):
{clues}

Estratto del modulo (max ~5000 char):
\"\"\"
{excerpt}
\"\"\"

Genera la sinossi nei seguenti campi. NON usare placeholder o frasi vuote tipo "elementi preservati", "senza aggiungere sottotrame": ogni campo deve essere CONCRETO e citare elementi del modulo.

- premise (max 280 char): 2-3 frasi che presentano la situazione iniziale, dove si trovano i PG, cosa stanno per scoprire. Evita frasi promozionali o credits.
- hidden_truth (max 240 char): la verita centrale che il gruppo deve dedurre. Una frase affermativa, non una domanda.
- win_condition (max 220 char): cosa devono ottenere/concludere i PG per "vincere", in termini concreti del modulo.
- threat_description (max 140 char): cosa peggiora se nulla viene fatto. Una frase breve.
- initial_hook (max 220 char): l'aggancio narrativo iniziale, una scena/situazione che porta i PG nell'azione.

Rispondi SOLO con JSON:
{{
  "premise": "...",
  "hidden_truth": "...",
  "win_condition": "...",
  "threat_description": "...",
  "initial_hook": "..."
}}
"""


def synthesize_narrative_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
    genre: str = "",
    archetype: str = "",
    tone: str = "",
) -> dict | None:
    """Generate premise / hidden_truth / win_condition / threat_description /
    initial_hook from the cleaned module text. These four are the user-facing
    fields of the adventure brief — without an LLM call here the runtime
    falls back to generic templates that say nothing about the actual story.
    """
    if not _llm_extractors_enabled():
        return None
    try:
        from . import claude_service
    except Exception:
        return None
    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    clues = (structure or {}).get("clues") or []
    clue_lines: list[str] = []
    for clue in clues[:25]:
        if not isinstance(clue, dict):
            continue
        cid = clue.get("id") or ""
        kind = clue.get("type") or "?"
        label = (clue.get("label") or "").strip()[:90]
        if label:
            clue_lines.append(f"- {cid} [{kind}] {label}")
    clues_block = "\n".join(clue_lines) or "(nessun indizio disponibile)"

    prompt = _SYNTHESIS_PROMPT.format(
        title=title or "(senza titolo)",
        genre=genre or "n/d",
        archetype=archetype or "n/d",
        tone=tone or "n/d",
        clues=clues_block,
        excerpt=_truncate_excerpt(text or "", limit=5000),
    )

    try:
        raw = claude_service._call_text_model(prompt, max_tokens=1200)
    except Exception as exc:
        print(f"[llm_extractors] synthesis call fallita: {type(exc).__name__}: {exc}")
        return None
    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_extractors] parse synthesis JSON fallito: {exc}")
        return None

    if not isinstance(parsed, dict):
        return None

    out: dict[str, str] = {}
    for field, limit in (
        ("premise", 320),
        ("hidden_truth", 280),
        ("win_condition", 260),
        ("threat_description", 180),
        ("initial_hook", 260),
    ):
        value = str(parsed.get(field) or "").strip()
        if value:
            out[field] = value[:limit]
    return out or None


_FACTION_PROMPT = """Sei un analista di moduli GDR. Estrai le FAZIONI o gruppi di potere presenti in questa avventura.

Una fazione è un gruppo organizzato con un'agenda propria: gilda, culto, nobile casata, banda criminale, fazione politica, organizzazione militare, setta, corporazione. NON includere singoli NPC come fazione (a meno che non guidino un gruppo), né fazioni implicite senza nome.

Per ogni fazione restituisci un JSON object con:
- id: stringa snake_case (es. "gilda_ladri", "culto_drago_nero")
- name: nome della fazione (max 60 char)
- agenda: cosa vuole ottenere CONCRETAMENTE in questa avventura (max 200 char)
- status: uno tra "quiet" | "watching" | "active" | "escalating" | "dominant" | "weakened" | "broken"
- pressure: intero 0-5 (quanto attivamente interferisce con i PG: 0=passiva, 5=antagonista principale)
- allies: lista di id di fazioni alleate (può essere vuota)
- enemies: lista di id di fazioni nemiche (può essere vuota)
- key_npc: nome del NPC leader o rappresentante principale (stringa, opzionale)

Restituisci un JSON array. Se non ci sono fazioni identificabili, restituisci [].

Titolo modulo: {title}
Genere: {genre}

NPC estratti (per riconoscere appartenenze):
{npcs}

Estratto del modulo:
\"\"\"
{excerpt}
\"\"\"

Rispondi SOLO con il JSON array, senza testo aggiuntivo."""


def extract_factions_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
    genre: str = "",
    existing_actors: list[dict] | None = None,
) -> list[dict] | None:
    """Estrae fazioni e gruppi di potere dal testo del modulo.

    Ritorna una lista di dict compatibili con FactionState, o None se
    LLM disabilitato / errore / nessuna fazione trovata.
    """
    if not _llm_extractors_enabled():
        return None

    from .claude_service import _call_active_provider  # type: ignore[attr-defined]

    excerpt = text[:6000]
    npcs_text = "\n".join(
        f"- {a.get('name','')} ({a.get('role','')}): {(a.get('agenda') or a.get('goal') or '')[:80]}"
        for a in (existing_actors or [])[:20]
        if a.get("name")
    ) or "Nessuno estratto."

    prompt = _FACTION_PROMPT.format(
        title=title or "Sconosciuto",
        genre=genre or "avventura",
        npcs=npcs_text,
        excerpt=excerpt,
    )

    try:
        from .claude_service import _call_text_model  # type: ignore[attr-defined]
        raw = _call_text_model(prompt, max_tokens=1200)
    except Exception:
        return None

    from .claude_service import _extract_json_object  # type: ignore[attr-defined]
    import json, re as _re
    # Estrai array JSON dalla risposta
    array_match = _re.search(r"\[.*\]", raw, _re.DOTALL)
    if not array_match:
        return None
    try:
        parsed = json.loads(array_match.group(0))
    except Exception:
        return None
    if not isinstance(parsed, list):
        return None

    valid_statuses = {"quiet", "watching", "active", "escalating", "dominant", "weakened", "broken"}
    factions: list[dict] = []
    seen_ids: set[str] = set()
    for i, f in enumerate(parsed):
        if not isinstance(f, dict):
            continue
        name = str(f.get("name") or "").strip()
        if not name:
            continue
        fid = str(f.get("id") or "").strip()
        if not fid:
            fid = "faction_" + "_".join(name.lower().split())[:30]
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        status = str(f.get("status") or "quiet")
        if status not in valid_statuses:
            status = "quiet"
        pressure = int(f.get("pressure") or 0)
        pressure = max(0, min(5, pressure))
        factions.append({
            "id": fid,
            "name": name,
            "agenda": str(f.get("agenda") or "")[:200],
            "status": status,
            "pressure": pressure,
            "allies": [str(x) for x in (f.get("allies") or []) if x],
            "enemies": [str(x) for x in (f.get("enemies") or []) if x],
            "key_npc": str(f.get("key_npc") or "")[:80],
            "source_status": "llm_extracted",
        })
    return factions or None


# ── P5: Source-aware finale ────────────────────────────────────────────────

import re as _re_module

_FINALE_SECTION_RE = _re_module.compile(
    r"(?:^|\n)\s*(?:#{1,3}|={3,}|-{3,})?\s*"
    r"(?:ending|conclusion|risoluzione|finale|resolution|denouement|aftermath|rewards?|epilog(?:ue)?)"
    r"\b[^\n]{0,60}\n"
    r"(?P<body>(?:.|\n){100,2500}?)(?=\n\s*(?:#{1,3}|={3,}|-{3,})\s*\w|\Z)",
    _re_module.IGNORECASE,
)

_BOXED_TEXT_RE = _re_module.compile(
    r"(?:boxed text|read(?:\s+aloud)?|letto ad alta voce|testo da leggere)[:\s]*\n"
    r"(?P<body>(?:.|\n){60,800}?)(?=\n\s*\n\s*\n|\Z)",
    _re_module.IGNORECASE,
)

_FINALE_SYNTHESIS_PROMPT = """Sei un analista di moduli GDR. Analizza queste sezioni finali di un'avventura e produci una lista di SCELTE CONCRETE che i personaggi giocanti possono fare nel momento culminante.

Una scelta concreta è un'azione decisiva, non una generica risoluzione: "sfidare il conte alla presenza dei testimoni usando il documento trovato nella cripta", "avvelenare la fonte prima dell'alba", "convincere il magistrato usando tre prove concrete". Dev'essere specifica per questa avventura.

Restituisci un JSON array di oggetti, ognuno con:
- label: descrizione breve del finale (max 80 char)
- concrete_choice: la scelta/azione concreta in italiano (max 220 char)
- method: come i PG la eseguono meccanicamente (max 120 char)
- required_clues_hint: lista di 0-3 tipi di prove necessarie (stringhe)

Titolo avventura: {title}
Obiettivo principale: {objective}

Sezioni finali trovate:
\"\"\"
{finale_text}
\"\"\"

Restituisci SOLO il JSON array."""


def extract_finale_conditions_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
    objective: str = "",
) -> list[dict] | None:
    """P5: Cerca sezioni ending/conclusion nel testo e genera FinaleCondition concrete.

    Ritorna lista di dict con label/concrete_choice/method pronti per il compiler,
    o None se LLM disabilitato / nessuna sezione finale trovata.
    """
    if not _llm_extractors_enabled():
        return None

    # Cerca sezioni finale nel testo
    finale_chunks: list[str] = []
    for m in _FINALE_SECTION_RE.finditer(text):
        chunk = m.group("body").strip()
        if len(chunk) >= 80:
            finale_chunks.append(chunk[:1200])
    for m in _BOXED_TEXT_RE.finditer(text):
        chunk = m.group("body").strip()
        if len(chunk) >= 60:
            finale_chunks.append(chunk[:600])
    # Ultimi 800 char del testo come fallback (spesso il finale è in coda)
    if not finale_chunks and len(text) > 800:
        finale_chunks.append(text[-1200:].strip())
    if not finale_chunks:
        return None

    finale_text = "\n\n---\n\n".join(finale_chunks[:3])

    prompt = _FINALE_SYNTHESIS_PROMPT.format(
        title=title or "Sconosciuto",
        objective=objective or "completare l'avventura",
        finale_text=finale_text,
    )

    try:
        from .claude_service import _call_text_model  # type: ignore[attr-defined]
        raw = _call_text_model(prompt, max_tokens=800)
    except Exception:
        return None

    import json
    array_match = _re_module.search(r"\[.*\]", raw, _re_module.DOTALL)
    if not array_match:
        return None
    try:
        parsed = json.loads(array_match.group(0))
    except Exception:
        return None

    if not isinstance(parsed, list):
        return None

    finales: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        choice = str(item.get("concrete_choice") or "").strip()
        if not label or not choice:
            continue
        finales.append({
            "label": label[:80],
            "concrete_choice": choice[:220],
            "method": str(item.get("method") or "")[:120],
            "required_clues_hint": [str(x) for x in (item.get("required_clues_hint") or [])[:3]],
            "source_status": "llm_extracted",
        })
    return finales or None


# ---------------------------------------------------------------------------
# Estrazione location da zero quando l'heuristic produce solo ID numerici
# ---------------------------------------------------------------------------

_EXTRACT_LOCATIONS_PROMPT = """Sei un analista di moduli GDR. Estrai tutte le LOCATION giocabili da questo modulo.

Una location è: una stanza, un edificio, una zona esterna, un'area con nome proprio dove i PG possono recarsi e fare cose. NON includere: aree anonime, blocchi statistici, descrizioni generiche senza nome.

Titolo modulo: {title}

Testo del modulo (estratto):
\"\"\"
{excerpt}
\"\"\"

Ritorna un JSON con questa struttura:
{{
  "locations": [
    {{
      "id": "loc_slug_minuscolo",
      "name": "Nome della Location",
      "description": "Descrizione in 1-2 frasi: cosa c'è, che atmosfera ha",
      "type": "indoor|outdoor|dungeon|urban|wilderness|vehicle",
      "gameplay_function": "Cosa fanno i PG qui (combattono, investigano, parlano, riposano...)",
      "notable_features": ["feature 1", "feature 2"],
      "is_starting_location": false
    }}
  ]
}}

Estrai 3-12 location. Metti is_starting_location=true solo per la location iniziale principale. Solo JSON, nessun testo aggiuntivo.
"""


def extract_locations_with_llm(text: str, *, title: str = "") -> list[dict] | None:
    """Estrae location con nome reale dal testo grezzo quando l'heuristic produce solo ID numerici."""
    if not _llm_extractors_enabled():
        return None
    try:
        from . import claude_service
    except Exception:
        return None
    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    excerpt = _truncate_excerpt(text or "", limit=8000)
    prompt = _EXTRACT_LOCATIONS_PROMPT.format(title=title or "(senza titolo)", excerpt=excerpt)
    try:
        raw = claude_service._call_claude(prompt, max_tokens=3000)
    except Exception as exc:
        print(f"[llm_extractors] extract_locations fallito: {exc}")
        return None
    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_extractors] extract_locations parse fallito: {exc}")
        return None
    items = parsed.get("locations") or []
    if not isinstance(items, list) or len(items) == 0:
        return None
    result = []
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = str(item["name"])
        slug = name.lower().replace(" ", "_").replace("'", "").replace("-", "_")[:40]
        result.append({
            "id": item.get("id") or f"loc_{slug}",
            "name": name,
            "description": str(item.get("description") or ""),
            "type": str(item.get("type") or "indoor"),
            "gameplay_function": str(item.get("gameplay_function") or ""),
            "concrete_features": list(item.get("notable_features") or [])[:6],
            "visual_identity": str(item.get("description") or "")[:120],
            "exits": [],
            "access_state": "open",
            "is_starting_location": bool(item.get("is_starting_location", False)),
            "llm_extracted": True,
        })
    return result if result else None


# Livello B: estrazione collegamenti tra locazioni dal testo PDF
# ---------------------------------------------------------------------------

_LOCATION_CONNECTIONS_PROMPT = """Sei un analista di moduli GDR. Dato il testo del modulo e la lista delle locazioni estratte, identifica i collegamenti fisici o narrativi tra di esse.

Per ogni connessione indica:
- from_location: nome ESATTO della locazione di partenza (dalla lista sotto)
- to_location: nome ESATTO della locazione di destinazione (dalla lista sotto)
- description: brevissima descrizione del collegamento (max 60 char, es. "corridoio segreto", "porta nord", "scala a chiocciola")
- bidirectional: true se si può percorrere in entrambi i sensi (default true)

Locazioni disponibili:
{location_names}

Titolo modulo: {title}

Testo del modulo (estratto):
\"\"\"
{text_excerpt}
\"\"\"

Regole:
- Usa SOLO i nomi dalla lista sopra, non inventarne altri.
- Non duplicare connessioni: se A↔B è bidirezionale, scrivila UNA volta sola con bidirectional=true.
- Se non trovi connessioni esplicite, deducile dal contesto narrativo (adiacenza, flusso dell'avventura).
- Restituisci SOLO il JSON array, nient'altro.

Esempio output:
[
  {{"from_location": "Ingresso", "to_location": "Sala delle Guardie", "description": "porta principale", "bidirectional": true}},
  {{"from_location": "Sala delle Guardie", "to_location": "Dungeon", "description": "scala discendente", "bidirectional": false}}
]"""


def extract_location_connections_with_llm(
    text: str,
    locations: list[dict],
    *,
    title: str = "",
) -> list[dict] | None:
    """Livello B: identifica i collegamenti reali tra locazioni dal testo PDF.

    Ritorna lista di dict con from_location/to_location/description/bidirectional,
    o None se LLM disabilitato / meno di 2 locazioni / fallimento.
    """
    if not _llm_extractors_enabled():
        return None
    if len(locations) < 2:
        return None

    loc_names = [str(l.get("name") or "") for l in locations if l.get("name")]
    if len(loc_names) < 2:
        return None

    # Usa al massimo 6000 char dal testo per non sprecare token
    text_excerpt = (text or "")[:6000].strip()
    if not text_excerpt:
        return None

    location_names_str = "\n".join(f"- {n}" for n in loc_names)
    prompt = _LOCATION_CONNECTIONS_PROMPT.format(
        title=title or "Sconosciuto",
        location_names=location_names_str,
        text_excerpt=text_excerpt,
    )

    try:
        from .claude_service import _call_text_model  # type: ignore[attr-defined]
        raw = _call_text_model(prompt, max_tokens=600)
    except Exception:
        return None

    import json as _json
    array_match = _re_module.search(r"\[.*\]", raw, _re_module.DOTALL)
    if not array_match:
        return None
    try:
        parsed = _json.loads(array_match.group(0))
    except Exception:
        return None

    if not isinstance(parsed, list):
        return None

    valid_names = set(loc_names)
    connections: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        frm = str(item.get("from_location") or "").strip()
        to = str(item.get("to_location") or "").strip()
        if frm not in valid_names or to not in valid_names or frm == to:
            continue
        connections.append({
            "from_location": frm,
            "to_location": to,
            "description": str(item.get("description") or "")[:60],
            "bidirectional": bool(item.get("bidirectional", True)),
        })
    return connections or None


# ---------------------------------------------------------------------------
# Livello B: estrazione clock semantici dal testo PDF
# ---------------------------------------------------------------------------

_CLOCK_EXTRACTION_PROMPT = """Sei un analista di moduli GDR. Devi identificare i CLOCK narrativi reali nel testo di questa avventura.

Un clock è una minaccia che avanza nel tempo, indipendente dalle azioni dei giocatori — o un obiettivo con scadenza.

Per ogni clock identifica:
- id: slug snake_case univoco (es. "clock_golem_completamento")
- label: nome breve (max 50 char, in italiano)
- clock_type: uno tra:
    "terminal_defeat"  → se il clock completa = sconfitta totale del gruppo (morte, apocalisse, obiettivo irrecuperabile)
    "terminal_victory" → se il clock completa = vittoria del gruppo (obietivo raggiunto automaticamente)
    "escalation"       → se il clock completa = la situazione peggiora drasticamente ma l'avventura continua
    "narrative"        → cambia lo stato del mondo ma non termina l'avventura
- max_value: numero di turni/segmenti prima che scatti (intero, 4-12; almeno resolution_clues+2)
- consequence: cosa succede quando il clock raggiunge max_value (in italiano, 1-2 frasi)
- resolution_clues: lista degli ID indizi che i giocatori devono trovare per FERMARE/RISOLVERE questo clock.
  Usa solo ID dalla lista indizi fornita. Lascia [] se il clock è inevitabile.
- resolution_condition: frase leggibile che descrive come i giocatori fermano il clock (in italiano)
- discovery_clue_id: ID dell'indizio che RIVELA ai giocatori che questo clock esiste.
  Quando i giocatori trovano questo indizio, il clock diventa visibile. Lascia "" se sempre visibile.
- discovery_hint: segnale atmosferico ambiguo prima della scoperta (es. "Le rocce vibrano leggermente")
- steps: lista di eventi intermedi (1 per ogni step intermedio, non obbligatorio):
    [{{"step": 1, "world_state_change": "...", "scene_prompt": "cosa diventa visibile"}}]

INDIZI DISPONIBILI (usa solo questi ID per resolution_clues e discovery_clue_id):
{clue_ids_block}

TITOLO AVVENTURA: {title}

TESTO DEL MODULO:
\"\"\"
{text_excerpt}
\"\"\"

REGOLE IMPORTANTI:
- Identifica SOLO clock espliciti o fortemente impliciti nel testo — non inventare pericoli non presenti.
- Se c'è una minaccia centrale (nemico che completa un rituale, pericolo ambientale che avanza) → terminal_defeat con i giusti resolution_clues.
- max_value per clock terminal_defeat deve essere >= len(resolution_clues) + 2.
- Un modulo tipico ha 1-3 clock. Non crearne di più a meno che non siano tutti espliciti.
- Restituisci SOLO il JSON array, nient'altro.

Esempio:
[
  {{
    "id": "clock_golem",
    "label": "Completamento del Golem di Platino",
    "clock_type": "terminal_defeat",
    "max_value": 8,
    "consequence": "I'Zor'zah completa il golem che distrugge la torre dei Maghi. Sconfitta totale.",
    "resolution_clues": ["clue_piano_golem", "clue_fonte_platino"],
    "resolution_condition": "I giocatori bloccano l'estrazione del platino o distruggono il laboratorio",
    "discovery_clue_id": "clue_iscrizioni_naniche",
    "discovery_hint": "Le pareti della montagna sembrano vibrare come se qualcosa si stesse muovendo nelle profondità",
    "steps": [
      {{"step": 2, "world_state_change": "Arriva un carico di platino grezzo alla miniera", "scene_prompt": "Carrelli di minerale scorrono lungo le rotaie"}},
      {{"step": 5, "world_state_change": "Il golem è per metà completato — si sentono colpi sordi nella roccia", "scene_prompt": "Vibrazioni sempre più forti dal sottosuolo"}}
    ]
  }}
]"""


def extract_clocks_with_llm(
    text: str,
    structure: dict,
    *,
    title: str = "",
) -> list[dict] | None:
    """Estrae clock semantici reali dal testo PDF con tipi, resolution_clues e discovery_clue_id.

    Ritorna lista di dict clock pronti per adventure_compiler, o None se LLM non disponibile.
    """
    if not _llm_extractors_enabled():
        return None
    try:
        from . import claude_service
    except Exception:
        return None
    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    clues = (structure or {}).get("clues") or []
    if not clues:
        return None

    clue_ids_lines = []
    for c in clues[:30]:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "")
        label = str(c.get("label") or "")[:70]
        if cid:
            clue_ids_lines.append(f"- {cid}: {label}")
    clue_ids_block = "\n".join(clue_ids_lines) or "(nessun indizio)"

    text_excerpt = _truncate_excerpt(text or "", limit=7000)
    prompt = _CLOCK_EXTRACTION_PROMPT.format(
        title=title or "Sconosciuto",
        clue_ids_block=clue_ids_block,
        text_excerpt=text_excerpt,
    )

    try:
        raw = claude_service._call_text_model(prompt, max_tokens=1400)
    except Exception as exc:
        print(f"[llm_extractors] clock extraction fallita: {type(exc).__name__}: {exc}")
        return None

    import json as _json
    array_match = _re_module.search(r"\[.*\]", raw, _re_module.DOTALL)
    if not array_match:
        return None
    try:
        parsed = _json.loads(array_match.group(0))
    except Exception:
        return None

    if not isinstance(parsed, list):
        return None

    valid_clue_ids = {str(c.get("id") or "") for c in clues if isinstance(c, dict) and c.get("id")}
    valid_clock_types = {"narrative", "terminal_defeat", "terminal_victory", "escalation"}

    clocks: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()[:50]
        if not cid or not label:
            continue
        clock_type = str(item.get("clock_type") or "narrative")
        if clock_type not in valid_clock_types:
            clock_type = "narrative"
        res_clues = [r for r in (item.get("resolution_clues") or []) if isinstance(r, str) and r in valid_clue_ids]
        disc_clue = str(item.get("discovery_clue_id") or "")
        if disc_clue and disc_clue not in valid_clue_ids:
            disc_clue = ""
        declared_max = max(1, int(item.get("max_value") or 6))
        # Auto-balance: terminale non può scattare prima che i giocatori abbiano avuto
        # turni sufficienti per trovare tutti i resolution_clues
        if res_clues and clock_type in {"terminal_defeat", "terminal_victory"}:
            declared_max = max(declared_max, len(res_clues) + 2)
        clocks.append({
            "id": cid,
            "label": label,
            "clock_type": clock_type,
            "max_value": declared_max,
            "consequence": str(item.get("consequence") or "")[:200],
            "on_complete": str(item.get("consequence") or "")[:200],
            "resolution_clues": res_clues,
            "resolution_condition": str(item.get("resolution_condition") or "")[:200],
            "discovery_clue_id": disc_clue,
            "discovery_hint": str(item.get("discovery_hint") or "")[:120],
            "steps": [
                {
                    "step": int(s.get("step") or 0),
                    "world_state_change": str(s.get("world_state_change") or "")[:120],
                    "scene_prompt": str(s.get("scene_prompt") or "")[:120],
                }
                for s in (item.get("steps") or [])
                if isinstance(s, dict)
            ],
            "auto_balance": True,
            "source_status": "llm_extracted",
            "is_explicit_from_source": False,
            "is_inferred": True,
            "confidence": 0.75,
        })
    return clocks or None
