from __future__ import annotations

import re
from .runtime_models import AdventureDefinition

# ── Patterns per il quality gate ──────────────────────────────────────────────
_OCR_STAT_RE = re.compile(
    r'\b(AC\s*[:=]\s*\d|HD\s*[:=]\s*\d|AT\s*[:=]|HP\s*[:=]\s*\d|MV\s*[:=]\s*\d|THAC0|thac0|D\s*[:=]\s*\d-\d)',
    re.IGNORECASE,
)
_OCR_GARBAGE_RE = re.compile(r'[~□■●▪]|ln ~|[^\x09\x0a\x0d\x20-\x7e\x80-\xff]')
_GENERIC_LOC_ID_RE = re.compile(r'^p\d+_room_\d+$|^room_\d+$|^section_\d+$|^loc_\d+$|^area_\d+$')


def _score(parts: list[bool]) -> int:
    if not parts:
        return 0
    return round(100 * sum(1 for p in parts if p) / len(parts))


def runtime_quality_report(definition: AdventureDefinition) -> dict:
    clue_checks = []
    for clue in definition.clues:
        clue_checks.extend([
            bool(clue.source_location),
            bool(clue.possible_actions),
            bool(clue.immediate_information),
            bool(clue.hidden_implication),
        ])
    npc_checks = []
    for actor in definition.actors:
        npc_checks.extend([
            bool(actor.goal),
            bool(actor.current_plan),
            bool(actor.fallback_plan),
            bool(actor.pressure_response),
        ])
    location_checks = []
    for loc in definition.locations:
        location_checks.extend([
            len(loc.concrete_features) >= 3,
            bool(loc.visual_identity),
            bool(loc.gameplay_function),
            len(loc.exits) >= 1,
        ])
    clock_checks = []
    for clock in definition.event_clocks:
        clock_checks.extend([
            len(clock.steps) >= min(4, clock.max_value),
            all(s.get("world_state_change") for s in clock.steps[: min(4, len(clock.steps))]),
            all(s.get("possible_player_response") for s in clock.steps[: min(4, len(clock.steps))]),
        ])
    finale_checks = []
    for finale in definition.finale_conditions:
        finale_checks.extend([
            len(finale.required_clues) >= 2,
            bool(finale.method),
            bool(finale.concrete_choice),
        ])
    scores = {
        "clue_concreteness_score": _score(clue_checks),
        "npc_agenda_score": _score(npc_checks),
        "location_playability_score": _score(location_checks),
        "clock_operational_score": _score(clock_checks),
        "finale_playability_score": _score(finale_checks),
    }
    scores["fiction_density_score"] = round(sum(scores.values()) / max(1, len(scores)))
    return scores


def pdf_fidelity_report(definition: AdventureDefinition) -> dict:
    cards = definition.source_cards or (definition.source_structure or {}).get("source_cards") or []
    card_counts: dict[str, int] = {}
    for card in cards:
        kind = str((card or {}).get("type") or "unknown")
        card_counts[kind] = card_counts.get(kind, 0) + 1

    def ratio(runtime_count: int, source_count: int, cap: int | None = None) -> int:
        if source_count <= 0:
            return 100
        target = min(source_count, cap) if cap else source_count
        return max(0, min(100, round(100 * runtime_count / max(1, target))))

    source_locations = max(
        card_counts.get("location", 0),
        min(14, card_counts.get("section", 0) + card_counts.get("map", 0) + card_counts.get("encounter", 0)),
    )
    source_actors = card_counts.get("actor", 0) + card_counts.get("faction", 0)
    if source_actors <= 0 and cards:
        source_actors = 4 if any(w in str(cards).lower() for w in ("npc", "png", "villain", "antagon", "duca", "barone", "professor", "captain", "lord")) else 0
    source_clues = card_counts.get("clue", 0) or min(6, card_counts.get("gm_note", 0) + card_counts.get("boxed_text", 0) + card_counts.get("encounter", 0))

    location_score = ratio(len(definition.locations), source_locations, cap=14)
    actor_score = ratio(len(definition.actors), source_actors, cap=10)
    clue_score = ratio(len(definition.clues), source_clues, cap=12)
    link_score = 100 if all(c.revelation_ids for c in definition.clues) else ratio(sum(1 for c in definition.clues if c.revelation_ids), len(definition.clues))
    finale_score = 100 if definition.finale_conditions else 0
    scores = [location_score, actor_score, clue_score, link_score, finale_score]
    overall = round(sum(scores) / max(1, len(scores)))
    return {
        "score": overall,
        "target": 85,
        "passes_target": overall >= 85,
        "source_card_counts": card_counts,
        "coverage": {
            "locations": location_score,
            "actors": actor_score,
            "clues": clue_score,
            "clue_links": link_score,
            "finale": finale_score,
        },
    }


def validate_ai_generated_definition(definition: AdventureDefinition) -> dict:
    return _validate_adventure_definition(definition, mode="ai_generated")


def validate_pdf_import_definition(definition: AdventureDefinition) -> dict:
    return _validate_adventure_definition(definition, mode="pdf_import")


def validate_adventure_definition(definition: AdventureDefinition) -> dict:
    if definition.source_mode in {"pdf_import", "pdf_import_fallback"}:
        return validate_pdf_import_definition(definition)
    return validate_ai_generated_definition(definition)


def _validate_adventure_definition(definition: AdventureDefinition, *, mode: str) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = list(definition.suggestions or [])
    is_pdf = mode == "pdf_import"
    clue_ids = {c.id for c in definition.clues}
    revelation_ids = {r.id for r in definition.revelations}
    objective_ids = {o.id for o in definition.objectives}
    location_ids = {l.id for l in definition.locations}

    for clue in definition.clues:
        linked = clue.revelation_ids or ([f"rev_{clue.thread_id}"] if clue.thread_id else [])
        if not linked or not any(rid in revelation_ids for rid in linked):
            warnings.append(f"Clue {clue.id} non collegato a una revelation valida.")
        if not clue.source_location:
            warnings.append(f"Clue {clue.id} senza source_location concreta.")
        if not clue.possible_actions:
            warnings.append(f"Clue {clue.id} senza possible_actions.")
        if not clue.immediate_information or not clue.hidden_implication:
            warnings.append(f"Clue {clue.id} troppo astratta: manca immediate_information o hidden_implication.")
        if is_pdf and clue.is_preserved_from_pdf and clue.inferred_payoff:
            warnings.append(f"Indizio preservato {clue.id} senza payoff chiaro nel PDF: payoff inferito.")

    for revelation in definition.revelations:
        has_clue = any(revelation.id in (c.revelation_ids or []) for c in definition.clues)
        if not has_clue and not revelation.required_clues and not revelation.conditions:
            warnings.append(f"Revelation {revelation.id} non ha clue o condizioni.")

    for objective in definition.objectives:
        if not objective.success_conditions:
            warnings.append(f"Objective {objective.id} non ha success_conditions.")

    for finale in definition.finale_conditions:
        deps = finale.depends_on + finale.required_threads + finale.required_clues
        if not deps:
            warnings.append(f"FinaleCondition {finale.id} non ha dipendenze esplicite.")

    for actor in definition.actors:
        if not actor.role:
            warnings.append(f"Actor {actor.id} senza role.")
        if not actor.goal:
            warnings.append(f"Actor {actor.id} senza goal.")
        if is_pdf and actor.is_preserved_from_pdf and actor.inferred_agenda:
            warnings.append(f"NPC preservato {actor.id} presente ma senza agenda esplicita nel PDF.")
        if not actor.current_plan or not actor.fallback_plan:
            warnings.append(f"Actor {actor.id} senza piano operativo/fallback.")
        if not actor.pressure_response:
            warnings.append(f"Actor {actor.id} senza pressure_response.")
        if "antagon" in actor.role.lower() and not actor.fallback_plan:
            warnings.append(f"Antagonist {actor.id} senza fallback_plan.")
        if ("witness" in actor.role.lower() or "testim" in actor.role.lower()) and not actor.knows:
            warnings.append(f"Witness {actor.id} senza informazione utile.")
        if "ally" in actor.role.lower() and not actor.resources:
            warnings.append(f"Ally {actor.id} senza utility concreta.")
        if actor.location_id and actor.location_id not in location_ids and actor.location_id not in {l.name for l in definition.locations}:
            warnings.append(f"Actor {actor.id} ha location non riconosciuta: {actor.location_id}.")

    for location in definition.locations:
        if not location.id or not location.name:
            errors.append("Location senza id o name.")
        if not location.type:
            warnings.append(f"Location {location.id} senza type.")
        if not location.access_state:
            warnings.append(f"Location {location.id} senza access_state.")
        if len(location.concrete_features) < 3:
            warnings.append(f"Location {location.id} senza almeno 3 feature concrete.")
        if not location.visual_identity:
            warnings.append(f"Location {location.id} senza visual_identity.")
        if is_pdf and location.is_preserved_from_pdf and not location.gameplay_function:
            warnings.append(f"Location preservata {location.id} senza funzione ludica evidente.")

    for clock in definition.event_clocks:
        if clock.max_value <= 0:
            errors.append(f"EventClock {clock.id} ha max non valido.")
        if not clock.on_complete and not clock.consequence:
            warnings.append(f"EventClock {clock.id} senza on_complete/consequence.")
        if len(clock.steps) < min(4, clock.max_value):
            warnings.append(f"EventClock {clock.id} senza almeno 4 step concreti.")

    profiles = set(definition.runtime_profiles or [])
    if "investigation_graph" in profiles:
        if not definition.revelations:
            errors.append("investigation_graph richiede almeno una revelation.")
        if len(definition.clues) < 3 and not is_pdf:
            warnings.append("investigation_graph dovrebbe avere almeno 3 clue.")
    if "heist" in profiles:
        has_heat = any("heat" in p.id.lower() or "sicurezza" in p.label.lower() for p in definition.pressure_systems)
        if not has_heat and not definition.genre_runtime.get("security_layers"):
            warnings.append("heist richiede security_layers o pressure_system heat.")
    if "survival_escape" in profiles:
        routes = definition.genre_runtime.get("routes") or definition.genre_runtime.get("route_nodes") or []
        safe_nodes = definition.genre_runtime.get("safe_nodes") or []
        if not definition.resources and not routes and not safe_nodes:
            warnings.append("survival_escape richiede resources o route/safe nodes.")
        if len(routes) + len(safe_nodes) < 2:
            warnings.append("survival_escape richiede almeno 2 routes o safe_nodes.")
    if "faction_crisis" in profiles and len(definition.factions) < 2:
        warnings.append("faction_crisis richiede almeno 2 factions.")
    if "ritual_dungeon" in profiles:
        if not definition.genre_runtime.get("ritual_conditions") and not definition.genre_runtime.get("special_items"):
            warnings.append("ritual_dungeon richiede ritual_conditions o special_items.")
    if "branching_node_graph" in profiles and not definition.genre_runtime.get("scene_nodes"):
        warnings.append("branching_node_graph richiede scene_nodes con choices e target_node.")

    for finale in definition.finale_conditions:
        if len(finale.required_clues) < 2 and not is_pdf:
            warnings.append(f"FinaleCondition {finale.id} dovrebbe richiedere almeno 2 clue.")
        if not finale.method or not finale.concrete_choice:
            warnings.append(f"FinaleCondition {finale.id} senza metodo/scelta concreta.")

    fidelity = pdf_fidelity_report(definition) if is_pdf else {}
    if is_pdf:
        structure = definition.source_structure or {}
        counts = structure.get("counts") or {}
        policy = definition.preservation_policy or {}
        if policy.get("preserve_rooms") and counts.get("rooms", 0) and len(definition.locations) < counts["rooms"]:
            errors.append(f"Compressione strutturale vietata: PDF con {counts['rooms']} stanze, runtime con {len(definition.locations)} location.")
        if policy.get("preserve_all_clues") and counts.get("clues", 0) and len(definition.clues) < counts["clues"]:
            errors.append(f"Compressione indizi vietata: PDF con {counts['clues']} indizi, runtime con {len(definition.clues)} clue.")
        if not definition.event_clocks:
            suggestions.append("PDF senza clock chiaro: non è stato creato un clock obbligatorio.")
        if not definition.finale_conditions:
            warnings.append("PDF senza chiara condizione finale.")
        if not definition.locations:
            errors.append("runtime impossibile da avviare: location iniziale mancante.")
        if not definition.locations and not definition.clues and not definition.actors:
            errors.append("nessuna struttura giocabile riconoscibile nel PDF.")
        if fidelity and fidelity["score"] < 70:
            warnings.append(f"Fidelity score basso: {fidelity['score']}% rispetto agli elementi PDF estratti.")

    quality = runtime_quality_report(definition)
    playable = not errors and bool(definition.objectives) and bool(definition.locations)
    playable_score = max(0, min(100, quality.get("fiction_density_score", 0) - len(errors) * 25 - min(30, len(warnings) * 2)))
    return {
        "valid": not errors,
        "playable": playable,
        "playable_score": playable_score,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "quality": quality,
        "fidelity": fidelity,
        "counts": {
            "objectives": len(objective_ids),
            "locations": len(location_ids),
            "actors": len(definition.actors),
            "clues": len(clue_ids),
            "revelations": len(revelation_ids),
        },
    }


def check_raw_compilation_quality(defn) -> dict:
    """Quality gate su adventure_definition (dict grezzo O oggetto AdventureDefinition).
    Rileva compilazioni fallite prima del salvataggio.
    Ritorna {"passed": bool, "blocking": bool, "critical": [...], "warnings": [...]}
    """
    critical: list[str] = []
    warnings_: list[str] = []

    # Normalizza: Pydantic model → estrai attributi; dict → usa .get()
    if isinstance(defn, dict):
        clues = defn.get("clues") or []
        actors = defn.get("actors") or []
        locations = defn.get("locations") or []
        threads = defn.get("story_threads") or []
        clocks = defn.get("event_clocks") or []
        finales = defn.get("finale_conditions") or []
        title = str(defn.get("title") or "")
        player_obj = str(defn.get("player_facing_objective") or "").strip()
        # Per i dict raw, la label clue è in c.get("label") o c.get("id")
        def _clue_label(c): return str(c.get("label") or c.get("id") or "")
        def _clue_id(c): return str(c.get("id") or "")
        def _loc_id(l): return str(l.get("id") or "")
        def _clock_label(cl): return str(cl.get("label") or cl.get("id") or "")
        def _clock_steps(cl): return cl.get("steps") or []
    else:
        # AdventureDefinition Pydantic model
        clues = list(defn.clues or [])
        actors = list(defn.actors or [])
        locations = list(defn.locations or [])
        # story_threads su Pydantic = revelations (una per thread)
        threads = list(defn.revelations or [])
        clocks = list(defn.event_clocks or [])
        finales = list(defn.finale_conditions or [])
        title = str(defn.title or "")
        player_obj = str((defn.objectives[0].label if defn.objectives else "") or "").strip()
        def _clue_label(c): return str(getattr(c, "label", "") or getattr(c, "id", "") or "")
        def _clue_id(c): return str(getattr(c, "id", "") or "")
        def _loc_id(l): return str(getattr(l, "id", "") or "")
        def _clock_label(cl): return str(getattr(cl, "label", "") or getattr(cl, "id", "") or "")
        def _clock_steps(cl): return list(getattr(cl, "steps", None) or [])

    # ── 1. Conteggio clue ───────────────────────────────────────────────────
    n_clues = len(clues)
    if n_clues == 0:
        critical.append(
            "Nessun indizio estratto: il compilatore non ha trovato contenuto narrativo utile."
        )
    elif n_clues < 4:
        critical.append(
            f"Solo {n_clues} indizi estratti (minimo 4). "
            "L'estrazione è fallita o il PDF non era leggibile."
        )

    # ── 2. OCR / stat-block nelle label dei clue ────────────────────────────
    garbage_clues = []
    for c in clues:
        label = _clue_label(c)
        if _OCR_STAT_RE.search(label) or _OCR_GARBAGE_RE.search(label):
            garbage_clues.append(_clue_id(c) or "?")
    if garbage_clues:
        valid_count = len(clues) - len(garbage_clues)
        _ocr_msg = (
            f"Indizi con contenuto OCR non valido (stat block o caratteri corrotti): "
            f"{', '.join(garbage_clues[:5])}. "
            "Il testo del PDF non è stato estratto correttamente."
        )
        if len(garbage_clues) <= 2 and valid_count >= 4:
            # Only a handful of bad clues and plenty of valid ones — downgrade to warning
            # so the game can still be played; the stat-block clues are simply skipped.
            warnings_.append(_ocr_msg)
        else:
            critical.append(_ocr_msg)

    # ── 3. Conteggio attori ─────────────────────────────────────────────────
    n_actors = len(actors)
    if n_actors == 0:
        critical.append("Nessun NPC estratto: il compilatore non ha riconosciuto i personaggi.")
    elif n_actors < 2:
        warnings_.append(
            f"Solo {n_actors} NPC estratto: idealmente un'avventura ne ha almeno 2-3. "
            "L'estrazione potrebbe essere incompleta."
        )

    # ── 4. Location con ID generici/numerici ────────────────────────────────
    if locations:
        generic = [_loc_id(l) for l in locations if _GENERIC_LOC_ID_RE.match(_loc_id(l))]
        generic_ratio = len(generic) / len(locations)
        if generic_ratio == 1.0:
            # Tutte generiche → blocco (non c'è nulla di reale)
            critical.append(
                f"Tutte le location hanno ID generici o numerici "
                f"({', '.join(generic[:3])}{'...' if len(generic) > 3 else ''}): "
                "il compilatore non ha estratto la mappa reale dell'avventura."
            )
        elif generic_ratio >= 0.6:
            warnings_.append(
                f"{len(generic)}/{len(locations)} location hanno ID generici "
                f"({', '.join(generic[:3])}...): la mappa è estratta parzialmente."
            )

    # ── 5. Story threads ────────────────────────────────────────────────────
    if len(threads) == 0:
        critical.append(
            "Nessun story thread: l'avventura non ha struttura narrativa riconoscibile. "
            "I giocatori non avranno fili conduttori da seguire."
        )

    # ── 6. Titolo == nome file ──────────────────────────────────────────────
    if title.lower().endswith(".pdf"):
        warnings_.append(
            f"Il titolo è il nome del file PDF ('{title}'): "
            "il compilatore non ha estratto un titolo reale."
        )

    # ── 7. Obiettivo giocatori vuoto ────────────────────────────────────────
    if not player_obj:
        warnings_.append(
            "Obiettivo visibile ai giocatori assente: "
            "i giocatori non sapranno cosa fare all'inizio."
        )

    # ── 8. Nessun finale ────────────────────────────────────────────────────
    if not finales:
        warnings_.append(
            "Nessuna condizione di finale: "
            "i giocatori non sapranno mai quando hanno vinto."
        )

    # ── 9. Clock senza step ──────────────────────────────────────────────────
    for cl in clocks:
        if not _clock_steps(cl):
            warnings_.append(
                f"Clock '{_clock_label(cl)}' senza step operativi: "
                "il GM non saprà cosa succede ad ogni tick."
            )

    blocking = len(critical) > 0
    score = max(0, 100 - len(critical) * 25 - len(warnings_) * 8)
    return {
        "passed": not blocking,
        "blocking": blocking,
        "score": score,
        "critical": critical,
        "warnings": warnings_,
    }
