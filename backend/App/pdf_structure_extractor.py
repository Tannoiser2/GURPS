from __future__ import annotations

import re
from typing import Any

from .pdf_cleanup import clean_pdf_pages, clean_pdf_text
from .source_mapper import create_source_ref


_ROOM_RE = re.compile(
    r"(?m)^\s*(?:area|room|stanza|camera|sala|luogo|location)?\s*([A-Z]?\d{1,3}[A-Z]?)[\).\:-]\s+(.+)$"
)
_SECTION_RE = re.compile(r"(?m)^\s{0,3}(?:#{1,4}\s*)?([A-ZÀ-Ü][^\n]{3,80})\s*$")
_NPC_RE = re.compile(r"(?im)^\s*(?:npc|png|personaggio|creatura|mostro|fazione|suspect|sospetto)[:\s-]+(.+)$")
_GURPS_ACTOR_RE = re.compile(
    r"(?ms)^\s*([A-ZÀ-Ü][A-ZÀ-Ü0-9'’() .,-]{3,70})\s*$"
    r"(?=.{0,520}\b(?:ST|DX|IQ|HT|HP|Will|Per|Basic Speed|Move|Dodge)\b)"
)
_FACTION_RE = re.compile(r"(?im)^\s*(?:fazione|faction|casata|gilda|clan)[:\s-]+(.+)$")
_CLUE_RE = re.compile(r"(?im)^\s*(?:clue|indizio|prova|evidence|testimonianza|documento)[:\s-]+(.+)$")
# Pattern to detect if a clue label is predominantly a stat block (e.g. "HP 14 ST 12 DX 11")
_STAT_BLOCK_DENSE_RE = re.compile(
    r'\b(AC|HD|HP|MV|THAC0|ST|DX|IQ|HT|FP|Move|Speed|Dodge|Parry|Block)\s*[:=]?\s*\d',
    re.IGNORECASE,
)
_ENCOUNTER_RE = re.compile(r"(?im)^\s*(?:encounter|incontro|combattimento|trappola|hazard|pericolo)[:\s-]+(.+)$")
_TIMELINE_RE = re.compile(r"(?im)^\s*(?:giorno|turno|ora|timeline|evento)\s*([0-9IVX:-]*)[:\s-]+(.+)$")
_TIMELINE_LADDER_RE = re.compile(
    r"(?im)^\s*(?:\*\*\s*)?(?:#{1,4}\s*)?"
    r"(day|hour|turn|round|phase|step|fase|ora|giorno|turno|round|fase)\s+"
    r"([0-9]{1,3}|[IVX]{1,4})"
    r"\s*[:.\-—]?\s*(.{0,200})$"
)
_TABLE_RE = re.compile(r"(?im)^\s*(?:d6|d66|d100|tabella|random table|incontri casuali)[:\s-]+(.+)$")
_MAP_RE = re.compile(r"(?im)\b(?:mappa|map|cartina|battlemap|planimetria)\b[:\s-]*([^\n]{0,120})")
_BOXED_RE = re.compile(r"(?ims)(?:boxed text|read aloud|leggi ai giocatori|testo da leggere)[:\s-]+(.{40,800}?)(?=\n\s*\n|$)")
_SECRET_RE = re.compile(r"(?ims)(?:gm only|keeper only|segreto|verità|dietro le quinte|solo master)[:\s-]+(.{40,800}?)(?=\n\s*\n|$)")


def _looks_like_stat_block(text: str) -> bool:
    low = str(text or "").lower()
    stat_markers = (
        "ac:", "ac ", "hd:", "hd", "hp:", "hp", "at:", " d:", "d:",
        "danno", "damage", "veleno", "thac0", "st:", "st ", "dx:", "dx ",
        "iq:", "iq ", "ht:", "ht ", "will:", "per:", "basic speed", "move:", "dodge:",
    )
    marker_hits = sum(1 for marker in stat_markers if marker in low)
    numeric_density = sum(ch.isdigit() for ch in low) >= max(4, len(low) // 18)
    return marker_hits >= 2 or (marker_hits >= 1 and numeric_density)


def _looks_like_section_noise(title: str) -> bool:
    raw = str(title or "").strip()
    low = raw.lower()
    if not raw:
        return True
    if raw[0].islower():
        return True
    if _looks_like_stat_block(raw):
        return True
    if "www." in low or "@" in raw or ".com" in low:
        return True
    if low.startswith(("able on ", "the adventure includes", "com or tweet", "disclaimer")):
        return True
    # Byline / credits / copyright lines (author, designer, artist).
    if low.startswith(("by ", "written by", "design by", "designed by", "art by", "illustrated by", "copyright", "©")):
        return True
    if low.endswith(" by") or " by " in low and len(raw.split()) <= 6 and any(ch.isupper() for ch in raw.split()[-1] if ch.isalpha()):
        # Catches "ADVENTURE BY J.C. CONNORS" style headings
        return True
    if raw.endswith((").", ").", ".", ",")):
        return True
    if len(raw.split()) > 8:
        return True
    return False


def _blocks_from_regex(pattern: re.Pattern, text: str, kind: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for idx, match in enumerate(pattern.finditer(text), start=1):
        label = " ".join(g for g in match.groups() if g).strip()
        line_start = text.rfind("\n", 0, match.start()) + 1
        quote = text[line_start:text.find("\n", match.end()) if "\n" in text[match.end():] else match.end()].strip()
        blocks.append({
            "id": f"{kind}_{idx}",
            "label": label[:160] or kind,
            "text": quote or label,
            "source_ref": create_source_ref(section=_nearest_heading(text, match.start()), paragraph=idx, quote=quote or label),
        })
    return blocks


def _nearest_heading(text: str, pos: int) -> str:
    before = text[:pos].splitlines()[-30:]
    for line in reversed(before):
        stripped = line.strip(" #\t")
        if 3 <= len(stripped) <= 80 and not stripped.endswith("."):
            if re.match(r"^[A-ZÀ-Ü0-9][A-Za-zÀ-ÿ0-9 '\-:]+$", stripped):
                return stripped
    return ""


def extract_pdf_sections(text: str) -> list[dict[str, Any]]:
    sections = []
    for idx, match in enumerate(_SECTION_RE.finditer(text or ""), start=1):
        title = match.group(1).strip()
        words = title.split()
        low = title.lower()
        if _looks_like_section_noise(title):
            continue
        if len(words) > 7:
            continue
        if "," in title or ";" in title:
            continue
        if low.startswith(("and ", "or ", "but ")):
            continue
        if low.endswith((" in", " with", " to", " from", " of", " for", " and", " or")):
            continue
        if sum(ch.isdigit() for ch in title) > max(2, len(title) // 3):
            continue
        sections.append({
            "id": f"section_{idx}",
            "title": title,
            "source_ref": create_source_ref(section=title, paragraph=idx, quote=title),
        })
    return sections[:200]


def _card(kind: str, item: dict[str, Any], idx: int, *, label_key: str = "label") -> dict[str, Any]:
    label = item.get(label_key) or item.get("name") or item.get("title") or item.get("label") or kind
    text = item.get("text") or item.get("description") or label
    return {
        "id": f"card_{kind}_{idx}",
        "type": kind,
        "label": str(label or kind)[:180],
        "text": str(text or label or "")[:1200],
        "source_ref": item.get("source_ref") or {},
        "source_status": "explicit",
        "confidence": 0.9,
        "raw_id": item.get("id") or "",
    }


def build_source_cards(structure: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten extracted PDF structure into audit-friendly cards before runtime shaping."""
    cards: list[dict[str, Any]] = []
    collections = [
        ("location", structure.get("rooms") or [], "name"),
        ("section", structure.get("sections") or [], "title"),
        ("actor", structure.get("npcs") or [], "label"),
        ("faction", structure.get("factions") or [], "label"),
        ("clue", structure.get("clues") or [], "label"),
        ("encounter", structure.get("encounters") or [], "label"),
        ("event", structure.get("events") or [], "label"),
        ("map", structure.get("maps") or [], "label"),
        ("boxed_text", structure.get("boxed_text") or [], "label"),
        ("gm_note", structure.get("gm_notes") or [], "label"),
        ("table", structure.get("tables") or [], "label"),
    ]
    for kind, items, label_key in collections:
        for item in items:
            if isinstance(item, dict):
                cards.append(_card(kind, item, len(cards) + 1, label_key=label_key))
    return cards


def extract_room_keys(text: str) -> list[dict[str, Any]]:
    rooms = []
    for idx, match in enumerate(_ROOM_RE.finditer(text or ""), start=1):
        number, title = match.group(1).strip(), match.group(2).strip()
        section = _nearest_heading(text, match.start())
        rooms.append({
            "id": f"room_{number.lower()}",
            "number": number,
            "name": title[:120],
            "description": title[:280],
            "section": section,
            "is_stat_block": _looks_like_stat_block(title),
            "source_ref": create_source_ref(section=section, paragraph=idx, quote=match.group(0)),
        })
    return rooms


def _preceding_paragraph(text: str, pos: int, max_chars: int = 600) -> str:
    """Return the descriptive paragraph that ends just before ``pos``.

    Used for ALL-CAPS GURPS actor headers: the narrative description of the
    character sits *above* the stat block, not after it. Reading the 400 chars
    after the header (the previous behaviour) scoops up stat lines and inline
    parentheticals as the NPC description.
    """
    window_start = max(0, pos - max_chars * 2)
    window = text[window_start:pos]
    # Drop trailing blank lines, then walk back to the previous blank line.
    window = window.rstrip()
    blank = window.rfind("\n\n")
    paragraph = window[blank + 2:] if blank != -1 else window
    paragraph = " ".join(paragraph.split())
    return paragraph[-max_chars:].strip()


def extract_npc_blocks(text: str) -> list[dict[str, Any]]:
    blocks = _blocks_from_regex(_NPC_RE, text or "", "npc")
    seen = {str(block.get("label") or "").lower() for block in blocks}
    for idx, match in enumerate(_GURPS_ACTOR_RE.finditer(text or ""), start=len(blocks) + 1):
        label = " ".join(match.group(1).split())
        if _looks_like_section_noise(label):
            continue
        low = label.lower()
        if low in seen:
            continue
        description = _preceding_paragraph(text, match.start())
        if not description or len(description) < 30:
            # Fall back to a short post-header window only if no narrative
            # paragraph precedes the stat block.
            line_start = text.rfind("\n", 0, match.start()) + 1
            description = " ".join(text[line_start:min(len(text), match.end() + 200)].split())
        blocks.append({
            "id": f"npc_{idx}",
            "label": label[:160],
            "text": description[:600],
            "source_ref": create_source_ref(section=_nearest_heading(text, match.start()), paragraph=idx, quote=label),
        })
        seen.add(low)
    return blocks


def extract_faction_blocks(text: str) -> list[dict[str, Any]]:
    return _blocks_from_regex(_FACTION_RE, text or "", "faction")


def _is_stat_block_label(label: str) -> bool:
    """Returns True if the label looks like a stat block row rather than a narrative clue.

    Triggers when ≥ 2 distinct stat field names are present in the label — a
    density that almost always means the regex matched a D&D/GURPS stat line
    that happened to follow an 'indizio:' keyword on the same page.
    """
    if not label:
        return False
    return len(_STAT_BLOCK_DENSE_RE.findall(label)) >= 2


def extract_clue_blocks(text: str) -> list[dict[str, Any]]:
    blocks = _blocks_from_regex(_CLUE_RE, text or "", "clue")
    # Drop blocks whose label is predominantly a stat block (OCR artefact)
    return [b for b in blocks if not _is_stat_block_label(b.get("label") or "")]


def extract_encounter_blocks(text: str) -> list[dict[str, Any]]:
    return _blocks_from_regex(_ENCOUNTER_RE, text or "", "encounter")


def extract_timeline_events(text: str) -> list[dict[str, Any]]:
    blocks = _blocks_from_regex(_TIMELINE_RE, text or "", "event")
    seen = {str(b.get("label") or "").lower() for b in blocks}
    # Ladder pattern matches headers like "Day 1", "Hour 0", "Phase II" with
    # or without trailing text — covers escalation timelines that most modules
    # write as section headings rather than prefixed lines.
    for idx, match in enumerate(_TIMELINE_LADDER_RE.finditer(text or ""), start=len(blocks) + 1):
        unit = match.group(1).strip().lower()
        number = match.group(2).strip()
        tail = (match.group(3) or "").strip()
        label = f"{unit.title()} {number}"
        if tail:
            label = f"{label}: {tail[:140]}"
        low = label.lower()
        if low in seen:
            continue
        line_start = (text or "").rfind("\n", 0, match.start()) + 1
        quote_end = match.end() + 280
        quote = (text or "")[line_start:min(len(text or ""), quote_end)].strip()
        blocks.append({
            "id": f"event_ladder_{idx}",
            "label": label,
            "text": quote or label,
            "ladder_unit": unit,
            "ladder_index": number,
            "source_ref": create_source_ref(section=_nearest_heading(text or "", match.start()), paragraph=idx, quote=label),
        })
        seen.add(low)
    return blocks


def extract_random_tables(text: str) -> list[dict[str, Any]]:
    return _blocks_from_regex(_TABLE_RE, text or "", "table")


def extract_maps_references(text: str) -> list[dict[str, Any]]:
    return _blocks_from_regex(_MAP_RE, text or "", "map")


def extract_boxed_text(text: str) -> list[dict[str, Any]]:
    return _blocks_from_regex(_BOXED_RE, text or "", "boxed")


def extract_gm_secrets(text: str) -> list[dict[str, Any]]:
    return _blocks_from_regex(_SECRET_RE, text or "", "secret")


def detect_module_structure(text: str) -> dict[str, bool]:
    text = text or ""
    rooms = extract_room_keys(text)
    clues = extract_clue_blocks(text)
    npcs = extract_npc_blocks(text)
    factions = extract_faction_blocks(text)
    encounters = extract_encounter_blocks(text)
    events = extract_timeline_events(text)
    tables = extract_random_tables(text)
    low = text.lower()
    return {
        "has_room_keys": len(rooms) >= 3,
        "has_timeline": bool(events),
        "has_random_tables": bool(tables),
        "has_factions": bool(factions) or any(w in low for w in ("fazione", "faction", "casata", "gilda", "clan")),
        "has_investigation": len(clues) >= 2 or any(w in low for w in ("indizio", "clue", "mistero", "sospetto")),
        "has_wilderness": any(w in low for w in ("wilderness", "selva", "foresta", "viaggio", "esagono", "hex")),
        "has_dungeon": len(rooms) >= 3 or any(w in low for w in ("dungeon", "cripta", "catacombe", "stanze numerate")),
        "has_heist": any(w in low for w in ("furto", "colpo", "heist", "sicurezza", "bersaglio")),
        "has_military": any(w in low for w in ("missione", "obiettivo tattico", "squadra", "forze", "terreno")),
        "has_sandbox": any(w in low for w in ("sandbox", "fazioni", "fronti", "luoghi liberi")),
    }


def extract_pdf_structure(text: str) -> dict[str, Any]:
    text = clean_pdf_text(text or "")
    rooms = extract_room_keys(text)
    clues = extract_clue_blocks(text)
    npcs = extract_npc_blocks(text)
    factions = extract_faction_blocks(text)
    encounters = extract_encounter_blocks(text)
    events = extract_timeline_events(text)
    tables = extract_random_tables(text)
    maps = extract_maps_references(text)
    gm_notes = extract_gm_secrets(text)
    boxed = extract_boxed_text(text)
    structure = {
        "detected_structure": detect_module_structure(text),
        "sections": extract_pdf_sections(text),
        "rooms": rooms,
        "npcs": npcs,
        "factions": factions,
        "clues": clues,
        "encounters": encounters,
        "events": events,
        "tables": tables,
        "maps": maps,
        "boxed_text": boxed,
        "gm_notes": gm_notes,
        "counts": {
            "rooms": len(rooms),
            "npcs": len(npcs),
            "factions": len(factions),
            "clues": len(clues),
            "encounters": len(encounters),
            "events": len(events),
            "tables": len(tables),
            "maps": len(maps),
        },
    }
    structure["source_cards"] = build_source_cards(structure)
    structure["counts"]["source_cards"] = len(structure["source_cards"])
    return structure


def _with_page_ref(item: dict[str, Any], page: int, prefix: str) -> dict[str, Any]:
    next_item = dict(item or {})
    if next_item.get("id"):
        next_item["id"] = f"{prefix}_{next_item['id']}"
    source_ref = dict(next_item.get("source_ref") or {})
    source_ref["page"] = page
    next_item["source_ref"] = source_ref
    return next_item


def extract_pdf_structure_from_pages(pages: list[str]) -> dict[str, Any]:
    """Extract and merge structure page-by-page, preserving page source refs."""
    merged: dict[str, Any] = {
        "detected_structure": {},
        "sections": [],
        "rooms": [],
        "npcs": [],
        "factions": [],
        "clues": [],
        "encounters": [],
        "events": [],
        "tables": [],
        "maps": [],
        "boxed_text": [],
        "gm_notes": [],
        "page_chunks": [],
    }
    cleaned_pages = clean_pdf_pages(list(pages or []))
    for page_number, page_text in enumerate(cleaned_pages, start=1):
        page_text = page_text or ""
        if not page_text.strip():
            continue
        structure = extract_pdf_structure(page_text)
        prefix = f"p{page_number}"
        merged["page_chunks"].append({
            "page": page_number,
            "chars": len(page_text),
            "counts": structure.get("counts") or {},
            "detected_structure": structure.get("detected_structure") or {},
        })
        for key, value in (structure.get("detected_structure") or {}).items():
            merged["detected_structure"][key] = bool(merged["detected_structure"].get(key) or value)
        for key in ("sections", "rooms", "npcs", "factions", "clues", "encounters", "events", "tables", "maps", "boxed_text", "gm_notes"):
            for item in structure.get(key) or []:
                if isinstance(item, dict):
                    merged[key].append(_with_page_ref(item, page_number, prefix))
    merged["counts"] = {
        "rooms": len(merged["rooms"]),
        "npcs": len(merged["npcs"]),
        "factions": len(merged["factions"]),
        "clues": len(merged["clues"]),
        "encounters": len(merged["encounters"]),
        "events": len(merged["events"]),
        "tables": len(merged["tables"]),
        "maps": len(merged["maps"]),
        "pages": len([p for p in pages or [] if (p or "").strip()]),
    }
    merged["source_cards"] = build_source_cards(merged)
    merged["counts"]["source_cards"] = len(merged["source_cards"])
    return merged
