from __future__ import annotations

import re
from typing import Any


def _slug(text: str, fallback: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text or "")).strip("_")[:40]
    return value or fallback


def _short_topic(text: str, fallback: str = "la minaccia") -> str:
    cleaned = " ".join(str(text or "").replace("\n", " ").split())
    if not cleaned:
        return fallback
    for sep in (".", ":", ";", "—", "-"):
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0].strip()
            break
    words = [w.strip(" ,.!?;:()[]{}\"'") for w in cleaned.split() if len(w.strip(" ,.!?;:()[]{}\"'")) > 2]
    stop = {"crea", "genera", "avventura", "missione", "storia", "modulo", "runtime", "per", "con", "del", "della", "delle", "degli", "una", "uno", "the", "and"}
    kept = [w for w in words if w.lower() not in stop][:6]
    return " ".join(kept) or fallback


def _text_blob(*values: Any) -> str:
    return " ".join(" ".join(str(v or "").replace("\n", " ").split()) for v in values).strip()


def _is_entry_location(loc: dict[str, Any]) -> bool:
    text = _text_blob(loc.get("name"), loc.get("description"), loc.get("original_section")).lower()
    entry_words = (
        "introduzione", "inizio", "ingresso", "entrata", "accesso", "porta",
        "villaggio", "strada", "taverna", "locanda", "piazza",
    )
    return any(word in text for word in entry_words)


def _is_late_revelation_location(loc: dict[str, Any]) -> bool:
    text = _text_blob(loc.get("name"), loc.get("description"), loc.get("original_section")).lower()
    late_words = (
        "sumar", "tesoro", "pelli di lupo", "rivelazione", "finale", "nasconde",
        "antagonista", "verità", "segreto", "boss", "stanza del tesoro",
    )
    return any(word in text for word in late_words)


def _is_hot_location(loc: dict[str, Any]) -> bool:
    text = _text_blob(loc.get("name"), loc.get("description"), loc.get("original_section")).lower()
    hot_words = (
        "terror", "terrore", "racket", "blood", "sangue", "soul bird", "spider ritual",
        "ritual", "rituale", "creature", "creatura", "monster", "mostro", "beast",
        "fight", "combat", "combattimento", "ambush", "agguato", "attack", "attacco",
        "orchetti", "lupi", "ragno", "arpie", "guardie", "soldati",
    )
    return any(word in text for word in hot_words)


def _is_meta_location_label(label: str) -> bool:
    low = str(label or "").lower()
    meta = (
        "about the adventure", "about 1shot", "notable npcs", "extending the adventure",
        "disclaimer", "pre-made characters", "premade characters", "character sheet",
    )
    if any(word in low for word in meta):
        return True
    if low.endswith("-") or low.endswith(" tac-"):
        return True
    stat_bits = ("st ", "dx ", "iq ", "ht ", "will:", "per:", "basic speed", "move:", "dodge:")
    return any(bit in low for bit in stat_bits)


def _playable_location_cards(cards: list[dict[str, Any]], actor_names: set[str]) -> list[dict[str, Any]]:
    playable: list[dict[str, Any]] = []
    for card in cards:
        label = str(card.get("label") or "")
        if _is_meta_location_label(label):
            continue
        low_label = label.lower()
        if card.get("type") == "section" and any(name and name in low_label for name in actor_names):
            continue
        if card.get("type") == "section" and label.isupper() and len(label.split()) <= 4 and any(low_label == name for name in actor_names):
            continue
        playable.append(card)
    return playable


def _select_location_cards(cards: list[dict[str, Any]], actor_names: set[str], limit: int) -> list[dict[str, Any]]:
    cutoff = len(cards)
    for idx, card in enumerate(cards):
        label = str(card.get("label") or "").lower()
        if any(marker in label for marker in ("extending the adventure", "about 1shot", "notable npcs", "appendix", "appendice")):
            cutoff = idx
            break
    cards = cards[:cutoff]
    playable = _playable_location_cards(cards, actor_names)
    selected = playable[:limit]
    late_cards = [
        card for card in playable
        if _is_late_revelation_location({"name": card.get("label"), "description": card.get("text")})
        or "finale" in str(card.get("label") or "").lower()
    ]
    for card in late_cards[:2]:
        if any(existing.get("id") == card.get("id") for existing in selected):
            continue
        if len(selected) >= limit:
            selected = selected[:-1]
        selected.append(card)
    return selected


def _phase_locations(locations: list[dict[str, Any]], required_clues: list[str]) -> list[dict[str, Any]]:
    if not locations:
        return locations

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        idx, loc = item
        source_page = int((loc.get("source_ref") or {}).get("page") or 999)
        is_late = _is_late_revelation_location(loc)
        is_entry = _is_entry_location(loc)
        is_stat = bool(loc.get("is_stat_block"))
        phase = 0 if is_entry else (2 if is_late else 1)
        return (phase, 1 if is_stat else 0, source_page * 1000 + idx)

    ordered = [loc for _, loc in sorted(enumerate(locations), key=sort_key)]
    if ordered and not _is_entry_location(ordered[0]):
        ordered[0]["type"] = ordered[0].get("type") or "entry"
        ordered[0]["gameplay_function"] = ordered[0].get("gameplay_function") or "apertura giocabile"

    total = max(1, len(ordered))
    for idx, loc in enumerate(ordered):
        loc = dict(loc)
        page = int((loc.get("source_ref") or {}).get("page") or idx + 1)
        explicit_late = _is_late_revelation_location(loc)
        late = explicit_late or idx >= max(2, int(total * 0.80))
        stat_block = bool(loc.get("is_stat_block"))
        if idx == 0:
            loc["status"] = "known"
            loc["access_state"] = "open"
            loc.setdefault("type", "entry")
            loc["gameplay_function"] = loc.get("gameplay_function") or "premessa e orientamento iniziale"
        elif stat_block and not explicit_late:
            loc["status"] = "unknown"
            loc["access_state"] = "open"
            loc["type"] = "encounter"
            loc["gameplay_function"] = loc.get("gameplay_function") or "incontro opzionale o pericolo di percorso"
            loc["tactical_map"] = {
                "enabled": True,
                "role": "combat",
                "trigger": "si attiva se i PG affrontano direttamente il pericolo",
            }
        elif _is_hot_location(loc):
            loc["status"] = "unknown"
            loc["access_state"] = "open"
            loc["type"] = "encounter" if loc.get("type") == "section" else loc.get("type", "encounter")
            loc["gameplay_function"] = loc.get("gameplay_function") or "zona calda con rischio di scontro o fuga"
            loc["tactical_map"] = {
                "enabled": True,
                "role": "hot_zone",
                "trigger": "si attiva se i PG entrano, forzano la scena o affrontano la minaccia",
            }
        elif late:
            loc["status"] = "hidden"
            loc["access_state"] = "locked"
            loc["type"] = "finale" if _is_late_revelation_location(loc) else loc.get("type", "late_scene")
            loc["access_requirements"] = list(required_clues[:2])
            loc["gameplay_function"] = loc.get("gameplay_function") or "rivelazione tardiva o confronto finale"
            if _is_late_revelation_location(loc):
                loc["tactical_map"] = {
                    "enabled": False,
                    "role": "locked_finale",
                    "trigger": "si attiva solo dopo gli indizi richiesti",
                }
        else:
            loc["status"] = "known" if page <= 3 or idx <= 2 else "unknown"
            loc["access_state"] = "open"
            loc["gameplay_function"] = loc.get("gameplay_function") or "sviluppo della progressione"
        ordered[idx] = loc
    return ordered


def _infer_initial_premise(text: str, sections: list[dict[str, Any]], title: str) -> str:
    preferred = [
        s for s in sections
        if any(word in str(s.get("title") or "").lower() for word in ("introduzione", "background", "premessa", "situazione"))
    ]
    if preferred:
        return preferred[0].get("title") or title or "Premessa del modulo."
    cleaned = _text_blob((text or "")[:900])
    if cleaned:
        return cleaned[:500]
    return title or "Premessa del modulo."


def _names_from_story_text(*values: str) -> list[str]:
    text = _text_blob(*values)
    ignored = {
        "Il", "La", "Lo", "Gli", "Le", "Un", "Una", "In", "Nel", "Nella", "Questa", "Questo",
        "Stanza", "Ingresso", "Scala", "Anticamera", "Tesoro", "Accanto", "Arpie", "Ragno",
        "Moduli", "Modulo", "Dove", "Come", "Note", "Introduzione",
    }
    names: list[str] = []
    for match in re.finditer(r"\b[A-ZÀ-Ü][a-zà-ÿ]{2,}(?:\s+[A-ZÀ-Ü][a-zà-ÿ]{2,}){0,2}\b", text):
        name = match.group(0).strip()
        if name.split()[0] in ignored:
            continue
        if name.lower() not in {n.lower() for n in names}:
            names.append(name)
    return names[:6]


def build_shape_for_pdf_import(
    text: str,
    extracted_structure: dict[str, Any],
    archetype_profile: dict[str, Any],
    preservation_policy: dict[str, Any],
    *,
    title: str = "",
    genre_hint: str | None = None,
) -> dict[str, Any]:
    counts = extracted_structure.get("counts") or {}
    rooms = extracted_structure.get("rooms") or []
    clues = extracted_structure.get("clues") or []
    npcs = extracted_structure.get("npcs") or []
    factions_raw = extracted_structure.get("factions") or []
    encounters = extracted_structure.get("encounters") or []
    events = extracted_structure.get("events") or []
    maps = extracted_structure.get("maps") or []
    gm_notes = extracted_structure.get("gm_notes") or []
    sections = extracted_structure.get("sections") or []
    source_cards = extracted_structure.get("source_cards") or []
    # Clock già estratti da LLM (con clock_type, resolution_clues, ecc.)
    llm_clocks = extracted_structure.get("event_clocks") or []
    actor_name_set = {
        str((npc.get("label") or npc.get("name") or "")).strip().lower()
        for npc in (npcs or [])
        if isinstance(npc, dict) and (npc.get("label") or npc.get("name"))
    }
    locations = []
    preserved_elements = []

    if rooms:
        for idx, room in enumerate(rooms, start=1):
            source_ref = room.get("source_ref") or {}
            locations.append({
                "id": room.get("id") or f"room_{idx}",
                "name": room.get("name") or f"Stanza {room.get('number') or idx}",
                "description": room.get("description") or "",
                "type": "encounter" if room.get("is_stat_block") else "room",
                "access_state": "open",
                "is_stat_block": bool(room.get("is_stat_block")),
                "source_ref": source_ref,
                "source_status": "explicit",
                "is_preserved_from_pdf": True,
                "original_room_number": str(room.get("number") or idx),
                "original_section": room.get("section") or "",
                "inferred_runtime_fields": ["visual_identity", "gameplay_function", "concrete_features"],
            })
            preserved_elements.append({"type": "location", "id": locations[-1]["id"], "source_ref": source_ref})
        if len(locations) < 6:
            extra_cards = [
                card for card in source_cards
                if card.get("type") in {"section", "map", "encounter", "boxed_text"}
                and card.get("label")
            ][: max(0, 12 - len(locations))]
            extra_cards = _select_location_cards(extra_cards, actor_name_set, max(0, 12 - len(locations)))
            for offset, section in enumerate(extra_cards, start=1):
                section_name = section.get("label") or f"Sezione {offset}"
                loc_id = f"section_extra_{offset}"
                if any(loc["name"].lower() == section_name.lower() for loc in locations):
                    continue
                locations.append({
                    "id": loc_id,
                    "name": section_name,
                    "description": section.get("text") or section_name,
                    "type": "encounter" if section.get("type") == "encounter" else ("map" if section.get("type") == "map" else "section"),
                    "access_state": "open",
                    "source_ref": section.get("source_ref") or {},
                    "source_status": "explicit",
                    "is_preserved_from_pdf": True,
                    "original_section": section_name,
                    "inferred_runtime_fields": ["gameplay_function"],
                })
                preserved_elements.append({"type": "location", "id": loc_id, "source_ref": section.get("source_ref") or {}})
    else:
        location_cards = [
            card for card in source_cards
            if card.get("type") in {"section", "map", "encounter", "boxed_text"}
            and card.get("label")
        ]
        location_cards = _select_location_cards(location_cards, actor_name_set, 14)
        source_sections = location_cards or sections[:12] or [{"label": "Scena iniziale", "title": "Scena iniziale", "source_ref": {}}]
        for idx, section in enumerate(source_sections, start=1):
            section_name = section.get("label") or section.get("title") or f"Sezione {idx}"
            locations.append({
                "id": f"section_{idx}",
                "name": section_name,
                "description": section.get("text") or section_name,
                "type": "encounter" if section.get("type") == "encounter" else ("map" if section.get("type") == "map" else "section"),
                "access_state": "open",
                "source_ref": section.get("source_ref") or {},
                "source_status": "explicit",
                "is_preserved_from_pdf": True,
                "original_section": section_name,
                "inferred_runtime_fields": ["gameplay_function"],
            })

    clue_sources = list(clues)
    if not clue_sources:
        inferred_sources = [
            card for card in source_cards
            if card.get("type") in {"gm_note", "boxed_text", "encounter", "map"}
        ][:6] or rooms[:3] or encounters[:3] or maps[:2]
        for idx, source in enumerate(inferred_sources, start=1):
            name = source.get("name") or source.get("label") or source.get("text") or f"Elemento {idx}"
            clue_sources.append({
                "id": f"inferred_clue_{idx}",
                "label": f"Dettaglio chiave: {name[:80]}",
                "text": f"In {name[:100]} c'e un dettaglio operativo che orienta accessi, rischi o soluzione della scena.",
                "source_ref": source.get("source_ref") or {},
                "inferred": True,
            })

    runtime_clues = []
    for idx, clue in enumerate(clue_sources, start=1):
        source_ref = clue.get("source_ref") or {}
        loc = locations[min(idx - 1, len(locations) - 1)]["name"] if locations else "Modulo"
        is_llm = bool(clue.get("llm_extracted"))
        # LLM-extracted clues already carry concrete label/type/source_location;
        # preserve them and let the shape builder only fill missing fields.
        clue_loc = clue.get("source_location") or clue.get("location") or loc
        runtime_clues.append({
            "id": clue.get("id") or f"clue_{idx}",
            "label": clue.get("label") or f"Indizio {idx}",
            "text": clue.get("text") or clue.get("label") or f"Indizio {idx}",
            "type": clue.get("type") or "physical_evidence",
            "thread_id": clue.get("thread_id") or f"T{min(idx, max(1, len(clues)))}",
            "source_location": clue_loc,
            "location": clue_loc,
            "reveals": clue.get("reveals") or clue.get("label") or clue.get("text") or "",
            "hidden_implication": clue.get("hidden_implication") or "",
            "payoff": clue.get("payoff") or "chiarisce una rotta, un rischio o una condizione utile della scena",
            "possible_actions": list(clue.get("possible_actions") or []),
            "revelation_ids": [f"rev_{idx}"],
            "is_required": True,
            "source_ref": source_ref,
            "source_status": clue.get("source_status") or ("inferred" if clue.get("inferred") or is_llm else "explicit"),
            "is_preserved_from_pdf": False if is_llm else (not clue.get("inferred")),
            "inferred_payoff": not is_llm,
            "confidence": float(clue.get("confidence") or (0.58 if clue.get("inferred") else 0.9)),
            "llm_extracted": is_llm,
        })
        preserved_elements.append({"type": "clue", "id": runtime_clues[-1]["id"], "source_ref": source_ref})

    locations = _phase_locations(locations, [c["id"] for c in runtime_clues])

    actors = []
    for idx, npc in enumerate(npcs, start=1):
        source_ref = npc.get("source_ref") or {}
        is_enriched = bool(npc.get("llm_enriched"))
        # LLM-enriched NPCs already carry concrete agenda fields — propagate
        # them; otherwise fall back to the regex pass that only knows label.
        actors.append({
            "id": npc.get("id") or f"actor_{idx}",
            "name": npc.get("name") or npc.get("label") or f"PNG {idx}",
            "role": npc.get("role") or "neutral",
            "location_id": locations[min(idx - 1, len(locations) - 1)]["id"] if locations else "",
            "goal": npc.get("goal") or "",
            "secret": npc.get("secret") or "",
            "fear": npc.get("fear") or "",
            "current_plan": npc.get("current_plan") or "",
            "fallback_plan": npc.get("fallback_plan") or "",
            "knows": list(npc.get("knows") or []),
            "wants": list(npc.get("wants") or []),
            "avoids": list(npc.get("avoids") or []),
            "relationships": list(npc.get("relationships") or []),
            "pressure_response": dict(npc.get("pressure_response") or {}),
            "source_ref": source_ref,
            "source_status": "explicit" if not is_enriched else "inferred",
            "is_preserved_from_pdf": True,
            "inferred_agenda": not is_enriched,
            "confidence": 0.92 if is_enriched else 0.85,
            "llm_enriched": is_enriched,
        })
        preserved_elements.append({"type": "actor", "id": actors[-1]["id"], "source_ref": source_ref})

    if not actors:
        actor_cards = [
            card for card in source_cards
            if card.get("type") in {"actor", "faction"}
        ][:10]
        for idx, card in enumerate(actor_cards, start=1):
            source_ref = card.get("source_ref") or {}
            actors.append({
                "id": card.get("raw_id") or f"actor_card_{idx}",
                "name": card.get("label") or f"PNG {idx}",
                "role": "neutral" if card.get("type") == "actor" else "faction",
                "location_id": locations[min(idx - 1, len(locations) - 1)]["id"] if locations else "",
                "goal": f"portare avanti il proprio ruolo in {title or 'questo modulo'}",
                "secret": card.get("text") or "",
                "current_plan": "reagire alle mosse dei PG secondo il testo del modulo",
                "fallback_plan": "spostare pressione o informazioni verso una scena collegata",
                "pressure_response": {"low": "osserva", "medium": "agisce", "high": "escalation", "critical": "forza una svolta"},
                "source_ref": source_ref,
                "source_status": "explicit",
                "is_preserved_from_pdf": True,
                "inferred_agenda": True,
                "confidence": 0.72,
            })
            preserved_elements.append({"type": "actor", "id": actors[-1]["id"], "source_ref": source_ref})

    if not actors:
        late_locations = [loc for loc in locations if loc.get("type") == "finale" or _is_late_revelation_location(loc)]
        for idx, loc in enumerate(late_locations[:4], start=1):
            names = _names_from_story_text(loc.get("name", ""), loc.get("description", ""))
            for name in names[:1]:
                source_ref = loc.get("source_ref") or {}
                antagonist = _is_late_revelation_location(loc)
                actors.append({
                    "id": f"actor_{_slug(name, f'png_{idx}')}",
                    "name": name,
                    "role": "antagonist" if antagonist else "neutral",
                    "location_id": loc.get("id") or "",
                    "status": "unintroduced",
                    "goal": f"proteggere il proprio ruolo nella rivelazione legata a {loc.get('name') or 'questa scena'}",
                    "secret": loc.get("description") or loc.get("name") or "",
                    "current_plan": f"restare fuori scena finche i PG non sbloccano {loc.get('name') or 'la scena finale'}",
                    "fallback_plan": "spostarsi verso una posizione difendibile o rivelare una verita parziale sotto pressione",
                    "resources": ["accessi", "alleati locali", "tempo"],
                    "knows": [c["id"] for c in runtime_clues[:2]],
                    "wants": ["mantenere nascosta la verita centrale"],
                    "avoids": ["essere esposto prima del confronto finale"],
                    "pressure_response": {
                        "low": "depista e resta nascosto",
                        "medium": "chiude un accesso o manda un ostacolo intermedio",
                        "high": "sposta una prova o accelera il confronto",
                        "critical": "si ritira verso la zona finale e forza la rivelazione",
                    },
                    "source_ref": source_ref,
                    "source_status": "inferred",
                    "is_preserved_from_pdf": True,
                    "inferred_agenda": True,
                    "confidence": 0.62,
                })
                preserved_elements.append({"type": "actor", "id": actors[-1]["id"], "source_ref": source_ref})

    factions = []
    for idx, faction in enumerate(factions_raw, start=1):
        source_ref = faction.get("source_ref") or {}
        factions.append({
            "id": faction.get("id") or f"faction_{idx}",
            "name": faction.get("label") or f"Fazione {idx}",
            "agenda": "agenda da preservare/inferire dal modulo",
            "source_ref": source_ref,
            "source_status": "explicit",
            "confidence": 0.86,
        })
        preserved_elements.append({"type": "faction", "id": factions[-1]["id"], "source_ref": source_ref})

    revelations = []
    llm_revelations = [
        r for r in (extracted_structure.get("revelations") or [])
        if isinstance(r, dict) and r.get("llm_generated")
    ]
    if llm_revelations:
        # Map LLM revelations onto the rebuilt clue ids so the deduction graph
        # actually points at clue ids that exist in this shape's runtime_clues.
        clue_id_lookup = {c["id"] for c in runtime_clues}
        for idx, rev in enumerate(llm_revelations, start=1):
            valid_required = [cid for cid in (rev.get("required_clues") or []) if cid in clue_id_lookup]
            valid_red_herrings = [cid for cid in (rev.get("red_herring_clues") or []) if cid in clue_id_lookup]
            revelations.append({
                "id": rev.get("id") or f"rev_llm_{idx}",
                "thread_id": rev.get("thread_id") or f"T_llm_{idx}",
                "statement": rev.get("statement") or f"Rivelazione {idx}",
                "required_clues": valid_required,
                "required_evidence_kinds": list(rev.get("required_evidence_kinds") or []),
                "minimum_independent_kinds": int(rev.get("minimum_independent_kinds") or 2),
                "red_herring_clues": valid_red_herrings,
                "payoff": rev.get("payoff") or "",
                "source_status": "inferred",
                "confidence": 0.78,
                "llm_generated": True,
            })
    elif runtime_clues:
        for idx, clue in enumerate(runtime_clues, start=1):
            revelations.append({
                "id": f"rev_{idx}",
                "thread_id": clue["thread_id"],
                "statement": f"Capire cosa implica: {clue['label']}",
                "required_clues": [clue["id"]],
                "payoff": clue["payoff"],
                "source_status": "inferred",
                "confidence": 0.62,
            })
    else:
        revelations.append({
            "id": "rev_pdf_structure",
            "thread_id": "T1",
            "statement": "Comprendere la struttura del modulo importato",
            "required_clues": [],
            "conditions": ["esplorare le sezioni preservate"],
            "payoff": "orienta il gioco senza inventare nuovi misteri",
            "source_status": "inferred",
            "confidence": 0.45,
        })

    event_clocks = []
    # Se LLM ha estratto clock semantici, usali direttamente — non fare il fallback euristico
    if llm_clocks:
        event_clocks = llm_clocks
    elif events:
        event_clocks.append({
            "id": "clock_timeline_pdf",
            "label": "Timeline del modulo",
            "progress": 0,
            "max": max(4, len(events)),
            "on_complete": events[-1].get("label") or events[-1].get("text") or "La timeline raggiunge il suo esito.",
            "steps": [
                {
                    "step": idx,
                    "world_state_change": event.get("label") or event.get("text") or f"Evento {idx}",
                    "scene_prompt": event.get("text") or event.get("label") or "",
                    "possible_player_response": "intervenire, deviare o prepararsi all'evento",
                }
                for idx, event in enumerate(events, start=1)
            ],
            "source_ref": events[0].get("source_ref") or {},
            "source_status": "explicit",
            "is_explicit_from_source": True,
            "is_inferred": False,
            "confidence": 0.9,
        })
    elif locations and (
        len(locations) >= 6
        or bool(actors)
        or bool(encounters)
        or any(_is_hot_location(loc) or _is_late_revelation_location(loc) or loc.get("type") == "finale" for loc in locations)
    ):
        beat_locations = [loc for loc in locations if loc.get("type") not in {"appendix", "meta"}]
        sampled: list[dict[str, Any]] = []
        if beat_locations:
            indexes = sorted(set([
                0,
                max(0, len(beat_locations) // 3),
                max(0, (len(beat_locations) * 2) // 3),
                len(beat_locations) - 1,
            ]))
            sampled = [beat_locations[i] for i in indexes if 0 <= i < len(beat_locations)]
        event_clocks.append({
            "id": "clock_progressione_pdf",
            "label": "Progressione del modulo",
            "progress": 0,
            "max": max(4, len(sampled) or 4),
            "on_complete": "La progressione raggiunge il finale previsto dal modulo.",
            "steps": [
                {
                    "step": idx,
                    "world_state_change": f"Il focus si sposta verso {loc.get('name') or 'la scena successiva'}.",
                    "scene_prompt": loc.get("description") or loc.get("name") or "",
                    "possible_player_response": "seguire la pista, prepararsi, evitare il rischio o cercare un accesso alternativo",
                    "location_id": loc.get("id") or "",
                }
                for idx, loc in enumerate(sampled, start=1)
            ],
            "source_ref": (sampled[0].get("source_ref") if sampled else {}) or {},
            "source_status": "inferred",
            "is_explicit_from_source": False,
            "is_inferred": True,
            "confidence": 0.62,
        })

    module_topic = _short_topic(title or (sections[0].get("title") if sections else "") or (locations[0]["name"] if locations else ""), "il modulo")
    hidden_truth = (gm_notes[0].get("text") if gm_notes else "") or f"La verita va ricostruita collegando gli elementi preservati di {module_topic}, senza aggiungere sottotrame esterne."
    objective = f"Raggiungere la risoluzione di {module_topic} usando stanze, incontri e indizi preservati dal modulo."
    premise = _infer_initial_premise(text, sections, title)
    initial_hook = (
        (locations[0].get("description") or locations[0].get("name")) if locations else ""
    ) or premise
    suggestions = []
    if not event_clocks:
        suggestions.append("PDF senza clock esplicito: aggiungere solo un optional_clock se serve pressione al tavolo.")
    if not runtime_clues and preservation_policy.get("preserve_all_clues"):
        suggestions.append("PDF investigativo rilevato, ma nessun indizio esplicito estratto: controllare formattazione o aggiungere mapping manuale.")

    return {
        "title": title or "Modulo PDF compilato",
        "genre": genre_hint or "",
        "runtime_profiles": _profiles_from_archetype(archetype_profile),
        "source_mode": "pdf_import",
        "source_structure": extracted_structure,
        "source_cards": source_cards,
        "archetype_profile": archetype_profile,
        "preservation_policy": preservation_policy,
        "original_structure_map": {
            "room_ids": [loc["id"] for loc in locations if loc.get("original_room_number")],
            "clue_ids": [c["id"] for c in runtime_clues],
            "actor_ids": [a["id"] for a in actors],
            "encounter_count": len(encounters),
            "table_count": counts.get("tables", 0),
            "source_card_count": len(source_cards),
        },
        "preserved_elements": preserved_elements,
        "inferred_elements": [
            {"type": "revelation", "id": r["id"], "source_status": "inferred", "confidence": r.get("confidence", 0.6)}
            for r in revelations
        ],
        "premise": premise,
        "initial_hook": initial_hook,
        "hidden_truth": hidden_truth,
        "core_truths": [{"id": "truth_pdf", "statement": hidden_truth, "reveal_clues": [c["id"] for c in runtime_clues[:2]], "reveal_rule": "quando gli elementi canonici collegati sono emersi"}],
        "objectives": [{"id": "obj_pdf", "label": objective, "success_conditions": ["seguire le condizioni del modulo o del GM"]}],
        "revelations": revelations,
        "clues": runtime_clues,
        "actors": actors,
        "factions": factions,
        "locations": locations,
        "event_clocks": event_clocks,
        "finale_conditions": [{
            "id": "finale_pdf",
            "label": "Finale del modulo preservato",
            "depends_on": ["obj_pdf"],
            "required_clues": [c["id"] for c in runtime_clues[:2]],
            "method": "seguire il finale previsto dal modulo o la condizione esplicita del GM",
            "concrete_choice": "scegliere una risoluzione basata sugli elementi preservati",
            "source_status": "inferred",
            "confidence": 0.55,
        }],
        "genre_runtime": {
            "pdf_structure_counts": counts,
            "encounters": encounters,
            "random_tables": extracted_structure.get("tables") or [],
            "maps": extracted_structure.get("maps") or [],
            "boxed_text": extracted_structure.get("boxed_text") or [],
        },
        "suggestions": suggestions,
    }


def build_shape_for_ai_generated(text: str, archetype_profile: dict[str, Any], *, title: str = "", genre_hint: str | None = None) -> dict[str, Any]:
    primary = archetype_profile.get("primary_archetype") or "investigation_graph"
    shape = _ai_shape_counts(primary)
    topic = _short_topic(text or title, "la crisi centrale")
    loc_names = _ai_location_names(primary, shape["locations"], topic)
    locations = [
        {
            "id": f"loc_ai_{idx}",
            "name": name,
            "description": f"{name}: nodo giocabile della struttura {primary}.",
            "type": "finale" if idx == shape["locations"] else ("entry" if idx == 1 else "site"),
            "access_state": "open",
            "source_status": "generated",
            "confidence": 0.72,
            "has_combat_potential": idx == shape["locations"] or primary in {"room_keyed_dungeon", "heist", "survival_escape", "military_operation"},
        }
        for idx, name in enumerate(loc_names, start=1)
    ]
    clues = [
        {
            "id": f"clue_ai_{idx}",
            "label": _ai_clue_label(primary, idx, topic),
            "text": _ai_clue_text(primary, idx, topic, locations[(idx - 1) % len(locations)]["name"]),
            "type": _ai_clue_type(primary, idx),
            "thread_id": f"T{((idx - 1) % max(1, shape['threads'])) + 1}",
            "source_location": locations[(idx - 1) % len(locations)]["name"],
            "reveals": _ai_clue_reveal(primary, idx, topic),
            "payoff": _ai_clue_payoff(primary, idx, topic),
            "revelation_ids": [f"rev_ai_{((idx - 1) % max(1, shape['threads'])) + 1}"],
            "is_required": idx <= max(1, shape["clues"] - 1),
            "source_status": "generated",
            "confidence": 0.72,
        }
        for idx in range(1, shape["clues"] + 1)
    ]
    revelations = [
        {
            "id": f"rev_ai_{idx}",
            "thread_id": f"T{idx}",
            "statement": _ai_revelation_statement(primary, idx, topic),
            "required_clues": [c["id"] for c in clues if c["thread_id"] == f"T{idx}"][:2],
            "payoff": _ai_revelation_payoff(primary, idx, topic),
            "source_status": "generated",
            "confidence": 0.7,
        }
        for idx in range(1, shape["threads"] + 1)
    ]
    actors = [
        {
            "id": f"actor_ai_{idx}",
            "name": _ai_actor_name(primary, idx, topic),
            "role": _ai_actor_role(primary, idx),
            "location_id": locations[min(idx, len(locations)) - 1]["id"],
            "goal": _ai_actor_goal(primary, idx, topic),
            "secret": _ai_actor_secret(primary, idx, topic),
            "source_status": "generated",
            "confidence": 0.7,
        }
        for idx in range(1, shape["actors"] + 1)
    ]
    clocks = []
    if shape["clock"]:
        clocks.append({
            "id": "clock_ai_main",
            "label": _ai_clock_label(primary, topic),
            "progress": 0,
            "max": shape["clock"],
            "on_complete": _ai_clock_complete(primary, topic),
            "is_inferred": True,
            "source_status": "generated",
            "confidence": 0.7,
        })
    return {
        "title": title or "Avventura generata",
        "genre": genre_hint or "",
        "runtime_profiles": _profiles_from_archetype(archetype_profile),
        "source_mode": "ai_generated",
        "archetype_profile": archetype_profile,
        "preservation_policy": {"preserve_original_structure": False, "forbid_structural_compression": False},
        "premise": text[:500],
        "initial_hook": text[:300],
        "objective": _ai_objective(primary, topic),
        "hidden_truth": _ai_hidden_truth(primary, topic),
        "locations": locations,
        "clues": clues,
        "revelations": revelations,
        "actors": actors,
        "event_clocks": clocks,
        "finale_conditions": [{
            "id": "finale_ai_main",
            "label": f"Finale: {topic}",
            "required_clues": [c["id"] for c in clues[: min(3, len(clues))]],
            "depends_on": ["obj_main"],
            "method": _ai_finale_method(primary, topic),
            "concrete_choice": _ai_finale_choice(primary, topic),
        }],
        "suggestions": [],
    }


def _ai_shape_counts(primary: str) -> dict[str, int | bool]:
    table = {
        "room_keyed_dungeon": {"locations": 7, "clues": 4, "threads": 2, "actors": 3, "clock": 0},
        "dungeon_exploration": {"locations": 6, "clues": 3, "threads": 2, "actors": 3, "clock": 0},
        "heist": {"locations": 5, "clues": 5, "threads": 3, "actors": 3, "clock": 6},
        "survival_escape": {"locations": 5, "clues": 3, "threads": 2, "actors": 2, "clock": 6},
        "faction_sandbox": {"locations": 5, "clues": 6, "threads": 4, "actors": 5, "clock": 0},
        "wilderness_sandbox": {"locations": 6, "clues": 4, "threads": 2, "actors": 3, "clock": 0},
        "military_operation": {"locations": 5, "clues": 3, "threads": 2, "actors": 4, "clock": 5},
        "romance_drama": {"locations": 4, "clues": 4, "threads": 3, "actors": 4, "clock": 0},
        "ritual_countdown": {"locations": 5, "clues": 5, "threads": 3, "actors": 3, "clock": 6},
    }
    return table.get(primary, {"locations": 4, "clues": 4, "threads": 3, "actors": 3, "clock": 0})


def _ai_location_names(primary: str, count: int, topic: str = "") -> list[str]:
    seeds = {
        "heist": ["Punto di osservazione", "Ingresso di servizio", "Sicurezza interna", f"Bersaglio: {topic}", "Via di estrazione"],
        "room_keyed_dungeon": ["Ingresso", "Corridoio delle scelte", "Sala trappola", "Archivio", "Santuario laterale", "Anticamera", f"Sala finale di {topic}"],
        "faction_sandbox": ["Piazza neutrale", "Sede fazione A", "Sede fazione B", "Mercato delle informazioni", "Luogo del confronto"],
        "survival_escape": ["Punto di partenza", "Percorso rapido", "Nodo sicuro", "Zona pericolosa", "Uscita contestata"],
        "ritual_countdown": ["Soglia del rito", "Archivio dei segni", "Camera degli officianti", "Altare incompleto", f"Cuore del rito: {topic}"],
    }
    base = seeds.get(primary) or ["Apertura", "Nodo indizi", "Luogo sociale", "Zona calda", "Finale", "Epilogo"]
    return [base[i] if i < len(base) else f"Nodo {i + 1}" for i in range(count)]


def _ai_clue_label(primary: str, idx: int, topic: str = "") -> str:
    if primary == "heist":
        labels = ["Turno delle guardie", "Badge duplicabile", "Cieco nelle telecamere", "Codice del vault", "Rotta di estrazione"]
    elif primary in {"room_keyed_dungeon", "dungeon_exploration"}:
        labels = ["Segno sulla porta", "Mappa incompleta", "Traccia della chiave", "Avvertimento inciso"]
    elif primary == "faction_sandbox":
        labels = ["Promessa tradita", "Debito segreto", "Accordo nascosto", "Testimone conteso", "Risorsa ricattabile", "Falso patto"]
    elif primary == "ritual_countdown":
        labels = ["Calendario del rito", "Nome dell'officiante", "Componente mancante", "Cerchio di interruzione", "Segno del sacrificio"]
    else:
        labels = ["Prova concreta", "Testimonianza utile", "Contraddizione verificabile", "Accesso alternativo", "Costo nascosto", "Leva finale"]
    label = labels[(idx - 1) % len(labels)]
    return f"{label} di {topic}" if topic and idx == len(labels) else label


def _ai_clue_text(primary: str, idx: int, topic: str, location: str) -> str:
    if primary == "ritual_countdown":
        templates = [
            f"Nel punto segnato a {location}, una sequenza di candele indica quanto manca al compimento di {topic}.",
            f"Un nome ripetuto nelle note rituali collega l'officiante principale a {topic}.",
            f"Una coppa, un sigillo o un ingrediente assente mostra quale parte del rito puo essere sabotata.",
            f"Il cerchio sul pavimento ha una frattura precisa: interromperla al momento giusto puo fermare il rito.",
            f"Una traccia di sangue o cenere rivela chi paghera il costo se il rito arriva alla fine.",
        ]
        return templates[(idx - 1) % len(templates)]
    return f"A {location} emerge una prova concreta collegata a {topic}: va esaminata, confermata o usata per sbloccare una scelta."


def _ai_clue_reveal(primary: str, idx: int, topic: str) -> str:
    if primary == "ritual_countdown":
        reveals = [
            f"quanto tempo resta prima che {topic} si compia",
            "chi sta guidando davvero il rito",
            "quale componente rende vulnerabile il rituale",
            "dove intervenire senza scatenare il costo peggiore",
            "qual e il prezzo nascosto del fallimento",
        ]
        return reveals[(idx - 1) % len(reveals)]
    return f"un dettaglio verificabile su {topic}"


def _ai_clue_payoff(primary: str, idx: int, topic: str) -> str:
    if primary == "ritual_countdown":
        payoffs = [
            "rende visibile il clock rituale",
            "permette di confrontare o indebolire l'officiante",
            "sblocca l'azione di sabotaggio",
            "riduce il rischio del confronto finale",
            "chiarisce la conseguenza del fallimento",
        ]
        return payoffs[(idx - 1) % len(payoffs)]
    return "sblocca una decisione, una rotta o una leva narrativa concreta"


def _ai_clue_type(primary: str, idx: int) -> str:
    cycle = ["physical_evidence", "testimony", "document", "location_detail", "contradiction"]
    return cycle[(idx - 1) % len(cycle)]


def _ai_revelation_statement(primary: str, idx: int, topic: str = "") -> str:
    if primary == "ritual_countdown":
        statements = [
            f"Quando e come si compie {topic}?",
            "Chi controlla il rito e cosa teme?",
            "Quale intervento puo fermare il rito senza peggiorarne il costo?",
        ]
        return statements[(idx - 1) % len(statements)]
    if primary == "heist":
        statements = ["Qual e la via d'ingresso piu sicura?", "Come si supera la sicurezza?", "Come si esce con il bersaglio?"]
        return statements[(idx - 1) % len(statements)]
    return f"Quale fatto concreto su {topic} cambia la scelta dei giocatori?"


def _ai_revelation_payoff(primary: str, idx: int, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return ["gestisce il tempo del rito", "identifica il bersaglio sociale", "sblocca il finale giocabile"][(idx - 1) % 3]
    return "trasforma gli indizi in una scelta giocabile"


def _ai_actor_name(primary: str, idx: int, topic: str = "") -> str:
    if primary == "ritual_countdown":
        roles = ["Officiante del rito", "Testimone del primo segno", "Custode del componente", "Vittima designata"]
        return roles[(idx - 1) % len(roles)]
    roles = ["Custode della leva", "Testimone utile", "Oppositore", "Alleato interessato", "Fazione mobile"]
    return f"{roles[(idx - 1) % len(roles)]} {idx}"


def _ai_actor_role(primary: str, idx: int) -> str:
    roles = ["witness", "ally", "antagonist", "neutral", "red_herring"]
    return roles[(idx - 1) % len(roles)]


def _ai_actor_goal(primary: str, idx: int, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return ["completare il rito", "sopravvivere raccontando cio che ha visto", "proteggere il componente mancante"][(idx - 1) % 3]
    return "portare avanti una leva dell'avventura senza aggiungere sottotrame gratuite"


def _ai_actor_secret(primary: str, idx: int, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return ["conosce il momento esatto del compimento", "ha visto chi ha preparato il cerchio", "sa quale oggetto puo interrompere il rito"][(idx - 1) % 3]
    return "conosce o controlla un pezzo della soluzione"


def _ai_clock_label(primary: str, topic: str = "") -> str:
    return {
        "heist": "Heat della sicurezza",
        "survival_escape": "Chiusura delle vie di fuga",
        "military_operation": "Reazione delle forze ostili",
        "ritual_countdown": f"Compimento di {topic}",
    }.get(primary, "Pressione archetipica")


def _ai_clock_complete(primary: str, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return f"{topic} si compie e il finale diventa molto piu costoso."
    return "La pressione dell'archetipo raggiunge il confronto finale."


def _ai_objective(primary: str, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return f"Scoprire le condizioni di {topic} e interromperlo prima del compimento."
    return f"Risolvere {topic} usando indizi, PNG e luoghi gia stabiliti."


def _ai_hidden_truth(primary: str, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return f"{topic} non e solo una minaccia: dipende da una condizione precisa che i giocatori possono scoprire e spezzare."
    return f"La verita centrale di {topic} e gia definita dal canovaccio e va rivelata progressivamente."


def _ai_finale_method(primary: str, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return "usare il componente corretto, il momento giusto e la prova sull'officiante"
    return "usare le leve scoperte durante la struttura archetipica"


def _ai_finale_choice(primary: str, topic: str = "") -> str:
    if primary == "ritual_countdown":
        return "interrompere il rito, deviarne il costo o affrontare l'officiante nella zona finale"
    return "scegliere una risoluzione coerente con indizi, PNG e rischi emersi"


def _profiles_from_archetype(archetype_profile: dict[str, Any]) -> list[str]:
    primary = archetype_profile.get("primary_archetype") or "investigation_graph"
    mapping = {
        "room_keyed_dungeon": "room_keyed_dungeon",
        "dungeon_exploration": "room_keyed_dungeon",
        "faction_sandbox": "faction_crisis",
        "wilderness_sandbox": "guided_sandbox",
        "heist": "heist",
        "survival_escape": "survival_escape",
        "ritual_countdown": "ritual_dungeon",
        "military_operation": "guided_sandbox",
        "romance_drama": "guided_sandbox",
    }
    profiles = [mapping.get(primary, "investigation_graph")]
    for secondary in archetype_profile.get("secondary_archetypes") or []:
        mapped = mapping.get(secondary)
        if mapped and mapped not in profiles:
            profiles.append(mapped)
    return profiles[:3]
