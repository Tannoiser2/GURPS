"""LLM-based metadata classifier for compiled adventures.

Replaces (but does not remove) the keyword-based genre detection in
``adventure_compiler.normalize_runtime_genre`` and the heuristic archetype
ranking in ``archetype_detector``. The keyword heuristics keep working as a
safe fallback when no LLM provider is configured (e.g. offline test runs).

Public API:
    classify_adventure_metadata(text, source_cards=None, *, title="")
        -> dict | None

The returned dict has the shape::

    {
        "genre": str,                       # one of GENRE_PACKS keys
        "primary_archetype": str,           # one of ARCHETYPE_LIBRARY keys
        "secondary_archetypes": [str, ...], # 0-3 ids
        "tone": str,                        # free-form short label
        "confidence": float,                # 0..1, how sure the LLM is
        "reason": str,                      # one-sentence justification
        "source": "llm",
    }

Returns ``None`` when no provider is configured or the call fails — callers
must be ready to fall back to the existing heuristic path.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .data_genres import GENRE_PACKS
from .narrative_archetypes import ARCHETYPE_LIBRARY


def _llm_classifier_enabled() -> bool:
    """LLM classification is opt-in. Set ``GURPS_ENABLE_LLM_CLASSIFIER=1`` to
    enable it in production; tests and offline runs leave it disabled so the
    compiler stays hermetic.
    """
    return os.getenv("GURPS_ENABLE_LLM_CLASSIFIER", "").strip().lower() in {"1", "true", "yes", "on"}


_PROMPT_TEMPLATE = """Sei un classificatore di moduli di avventura GDR.
Devi etichettare l'avventura seguente con genere e archetipo strutturale.

Vincoli rigidi (rispondi SOLO con valori da queste liste):
- genre ∈ {genres}
- primary_archetype ∈ {archetypes}
- secondary_archetypes: 0-3 valori distinti da {archetypes}, diversi da primary

Titolo: {title}

Indizi strutturali estratti (titoli sezione/room/clue/npc/encounter):
{cards}

Estratto testuale (max 4000 char):
\"\"\"
{excerpt}
\"\"\"

Rispondi SOLO con JSON valido in questa forma:
{{
  "genre": "...",
  "primary_archetype": "...",
  "secondary_archetypes": ["...", "..."],
  "tone": "breve etichetta tono (es: 'noir urbano', 'horror gotico', 'sword & sorcery')",
  "confidence": 0.0,
  "reason": "una frase con la giustificazione"
}}
"""


def _format_cards(source_cards: list[dict] | None, limit: int = 40) -> str:
    if not source_cards:
        return "(nessuna card strutturale estratta)"
    lines: list[str] = []
    for card in source_cards[:limit]:
        if not isinstance(card, dict):
            continue
        kind = card.get("type") or "card"
        label = str(card.get("label") or "").strip()
        if not label:
            continue
        lines.append(f"- [{kind}] {label[:120]}")
    return "\n".join(lines) or "(nessuna card strutturale estratta)"


def _coerce_archetype(value: Any) -> str | None:
    if not value:
        return None
    candidate = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return candidate if candidate in ARCHETYPE_LIBRARY else None


def _coerce_genre(value: Any) -> str | None:
    if not value:
        return None
    candidate = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return candidate if candidate in GENRE_PACKS else None


def classify_adventure_metadata(
    text: str,
    source_cards: list[dict] | None = None,
    *,
    title: str = "",
) -> dict | None:
    """Run the LLM classifier. Returns ``None`` when no provider is available
    or the call fails for any reason — callers fall back to heuristics.
    """
    if not _llm_classifier_enabled():
        return None

    try:
        from . import claude_service
    except Exception:
        return None

    if not getattr(claude_service, "_text_provider_available", None) or not claude_service._text_provider_available():
        return None

    excerpt = (text or "").strip()
    if len(excerpt) > 4000:
        # Keep head + a tail slice — moduli spesso esplicitano genere nel finale.
        excerpt = excerpt[:3200] + "\n[...]\n" + excerpt[-700:]

    prompt = _PROMPT_TEMPLATE.format(
        genres=sorted(GENRE_PACKS.keys()),
        archetypes=sorted(ARCHETYPE_LIBRARY.keys()),
        title=title or "(senza titolo)",
        cards=_format_cards(source_cards),
        excerpt=excerpt or "(testo vuoto)",
    )

    try:
        raw = claude_service._call_text_model(prompt, max_tokens=600)
    except Exception as exc:
        print(f"[llm_classifier] chiamata fallita: {type(exc).__name__}: {exc}")
        return None

    try:
        parsed = claude_service._extract_json_object(raw)
    except Exception as exc:
        print(f"[llm_classifier] parse JSON fallito: {exc}")
        return None

    genre = _coerce_genre(parsed.get("genre"))
    primary = _coerce_archetype(parsed.get("primary_archetype"))
    if not genre or not primary:
        print(f"[llm_classifier] valori fuori whitelist: genre={parsed.get('genre')} archetype={parsed.get('primary_archetype')}")
        return None

    secondaries_raw = parsed.get("secondary_archetypes") or []
    if isinstance(secondaries_raw, str):
        secondaries_raw = [secondaries_raw]
    secondaries: list[str] = []
    for value in secondaries_raw:
        coerced = _coerce_archetype(value)
        if coerced and coerced != primary and coerced not in secondaries:
            secondaries.append(coerced)
        if len(secondaries) >= 3:
            break

    try:
        confidence = float(parsed.get("confidence", 0.7))
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))

    return {
        "genre": genre,
        "primary_archetype": primary,
        "secondary_archetypes": secondaries,
        "tone": str(parsed.get("tone") or "").strip()[:80],
        "confidence": confidence,
        "reason": str(parsed.get("reason") or "").strip()[:240],
        "source": "llm",
    }
