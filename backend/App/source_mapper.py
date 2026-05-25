from __future__ import annotations

import hashlib
from typing import Any


def _hash(text: str) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()[:12]


def create_source_ref(*, section: str = "", paragraph: int | None = None, page: int | None = None, quote: str = "") -> dict[str, Any]:
    quote = str(quote or "").strip()
    return {
        "page": page,
        "section": section or "",
        "paragraph": paragraph,
        "snippet_hash": _hash(f"{section}|{paragraph}|{quote}"),
        "quote": quote[:500],
    }


def attach_source_to_element(element: dict, source_ref: dict | None, *, status: str = "explicit", confidence: float = 1.0) -> dict:
    next_element = dict(element or {})
    next_element["source_ref"] = source_ref or {}
    next_element["source_status"] = status
    next_element["confidence"] = confidence
    return next_element


def get_source_context_for_runtime_element(definition: dict, element_id: str) -> dict:
    for collection in ("locations", "clues", "actors", "factions", "event_clocks"):
        for element in definition.get(collection) or []:
            if isinstance(element, dict) and element.get("id") == element_id:
                return element.get("source_ref") or {}
    return {}
