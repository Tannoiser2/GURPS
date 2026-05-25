from __future__ import annotations

import hashlib

from .adventure_validator import validate_adventure_definition
from .archetype_detector import detect_archetypes_from_ai_prompt, detect_archetypes_from_pdf_structure
from .data_genres import GENRE_PACKS
from .genre_constraints import get_genre_profile
from .llm_classifier import classify_adventure_metadata
from .llm_extractors import (
    build_deduction_graph_with_llm,
    enrich_actors_with_llm,
    extract_clues_with_llm,
    synthesize_narrative_with_llm,
)
from .narrative_archetypes import get_archetype
from .pdf_structure_extractor import extract_pdf_structure, extract_pdf_structure_from_pages
from .preservation_policy import build_preservation_policy
from .runtime_shape_builder import build_shape_for_ai_generated, build_shape_for_pdf_import
from .semantic_concretizer import concretize_adventure_raw
from .runtime_models import (
    ActorState,
    AdventureDefinition,
    AdventureRuntimeState,
    EventClock,
    FinaleCondition,
    FactionState,
    HiddenTruth,
    LocationState,
    Objective,
    PressureSystem,
    Revelation,
    ResourceState,
    RuntimeClue,
)


def _id(prefix: str, text: str, idx: int) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text or ""))[:28].strip("_")
    return f"{prefix}_{slug or idx}"


def _profiles_for(text: str, hint: str | None = None) -> list[str]:
    if hint:
        return [hint]
    blob = text.lower()
    profiles = ["investigation_graph"]
    if any(w in blob for w in ["ritual", "cripta", "dungeon", "catacomb", "altare"]):
        profiles.append("ritual_dungeon")
    if any(w in blob for w in ["fuga", "escape", "sopravviv", "evacu"]):
        profiles.append("survival_escape")
    if any(w in blob for w in ["fazione", "casata", "concilio", "gilda"]):
        profiles.append("faction_crisis")
    if any(w in blob for w in ["furto", "colpo", "heist", "sabot"]):
        profiles.append("heist")
    return list(dict.fromkeys(profiles))[:3]


def normalize_runtime_genre(value: str | None, fallback: str = "detective_classico") -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in GENRE_PACKS:
        return raw
    blob = raw.replace("_", " ")
    if any(w in blob for w in ["fantasy", "medioevo", "medieval", "dungeon", "magia", "cripta", "drag"]):
        return "fantasy"
    if any(w in blob for w in ["horror", "gotic", "mystery", "occult", "lovecraft", "malediz"]):
        return "mystery_horror"
    if any(w in blob for w in ["sci", "space", "cyber", "alien", "futuro"]):
        return "sci_fi"
    if any(w in blob for w in ["war", "ww2", "guerra", "militar"]):
        return "ww2"
    if any(w in blob for w in ["detective", "noir", "investig", "giallo"]):
        return "detective_classico"
    if any(w in blob for w in ["romance", "sentiment"]):
        return "romance"
    if any(w in blob for w in ["action", "thriller", "azione"]):
        return "action"
    return fallback if fallback in GENRE_PACKS else "detective_classico"


def _looks_like_placeholder_thread(text: str) -> bool:
    blob = str(text or "").strip().lower()
    if not blob:
        return True
    markers = [
        "quale fatto concreto",
        "cambia la scelta dei giocatori",
        "quale leva della struttura",
        "struttura ritual_countdown",
        "pista 1:",
        "pista 2:",
        "pista 3:",
        "serve a: trasforma",
        "prova decisiva",
        "muovendo davvero la minaccia",
        "chiude l'avventura senza peggiorare",
    ]
    return any(marker in blob for marker in markers)


def _compact_text(value: str, limit: int = 180) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    return text[:limit].strip()


def _clue_label(clue: dict) -> str:
    return _compact_text(clue.get("label") or clue.get("text") or clue.get("id") or "indizio", 90)


def _derive_thread_question(tid: str, clues: list[dict], title: str = "") -> str:
    blob = " ".join(
        str(c.get(k, ""))
        for c in clues
        for k in ("label", "text", "reveals", "payoff", "source_location", "location")
    ).lower()
    labels = [_clue_label(c) for c in clues if _clue_label(c)]
    first = labels[0] if labels else _compact_text(title or "questa pista", 60)
    if any(w in blob for w in ["mappa", "posizione", "biblioteca", "accesso", "dove", "porta", "passaggio"]):
        return f"Dove conduce {first}?"
    if any(w in blob for w in ["barone", "sigillo", "complotto", "documenti riservati", "responsabile"]):
        return f"Che cosa prova {first} sul Barone o sui suoi complici?"
    if any(w in blob for w in ["gareth", "alleato", "sorella", "prigioniera", "testimone"]):
        return f"Come puo essere usato {first} per ottenere un alleato?"
    if any(w in blob for w in ["artefatto", "attivare", "chiave", "dente", "drago", "rituale", "sicuro"]):
        return f"Come si usa o si neutralizza {first} senza favorire la minaccia?"
    if len(labels) >= 2:
        return f"Che cosa dimostrano {labels[0]} e {labels[1]}?"
    return f"Che cosa dimostra {first}?"


def _derive_thread_answer(clues: list[dict], fallback: str = "") -> str:
    reveals = [
        _compact_text(c.get("reveals") or c.get("hidden_implication") or c.get("payoff") or c.get("text") or c.get("label"), 140)
        for c in clues
    ]
    reveals = [r for r in reveals if r and not _looks_like_placeholder_thread(r)]
    if reveals:
        if len(reveals) == 1:
            return reveals[0]
        return "; ".join(reveals[:2])
    return _compact_text(fallback or "La pista collega indizi concreti a una scelta giocabile.", 220)


def _derive_thread_payoff(clues: list[dict], fallback: str = "") -> str:
    payoffs = [_compact_text(c.get("payoff"), 120) for c in clues if c.get("payoff")]
    if payoffs:
        return " / ".join(payoffs[:2])
    return _compact_text(fallback or "sblocca una decisione concreta prevista dal canovaccio", 180)


def _looks_like_placeholder_actor(actor: dict) -> bool:
    text = " ".join(str(actor.get(k, "")) for k in ("name", "goal", "secret", "role")).lower()
    markers = [
        "custode della leva",
        "testimone utile",
        "oppositore",
        "alleato interessato",
        "fazione mobile",
        "portare avanti una leva",
        "senza aggiungere sottotrame",
        "conosce o controlla un pezzo della soluzione",
    ]
    return any(m in text for m in markers)


def _canon_names_from_text(*values: str) -> list[str]:
    text = " ".join(str(v or "") for v in values)
    candidates = []
    ignored = {
        "Il", "La", "Lo", "I", "Gli", "Le", "Un", "Una", "Nel", "Nella", "Nelle", "Dove", "Come",
        "Non",
        "Respiro Drago Dormiente", "Valdacre", "Nodo", "Apertura", "Zona", "Luogo",
    }
    for match in __import__("re").finditer(r"\b[A-ZÀ-Ü][a-zà-ÿ]{2,}(?:\s+[A-ZÀ-Ü][a-zà-ÿ]{2,}){0,2}\b", text):
        name = match.group(0).strip()
        if name in ignored or name.split()[0] in ignored:
            continue
        if name.lower() not in {n.lower() for n in candidates}:
            candidates.append(name)
    return candidates[:8]


def _actor_from_name(name: str, raw: dict, idx: int) -> dict:
    blob = " ".join(str(raw.get(k, "")) for k in ("hidden_truth", "premise", "win_condition")).lower()
    low = name.lower()
    role = "neutral"
    if any(w in low for w in ["selira", "tobin"]) or any(p in blob for p in [f"{low} ha corrotto", f"{low} quando", f"{low} per rompere"]):
        role = "antagonist"
    elif any(w in low for w in ["edrin", "durgan", "kragga", "yoren"]):
        role = "witness"
    locations = raw.get("locations") or []
    loc = ""
    if locations:
        loc_obj = locations[min(idx - 1, len(locations) - 1)]
        loc = loc_obj.get("id") or loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj)
    return {
        "id": f"actor_{''.join(ch.lower() if ch.isalnum() else '_' for ch in name).strip('_')[:28] or idx}",
        "name": name,
        "role": role,
        "location_id": loc,
        "goal": f"proteggere o rivelare il proprio ruolo nel caso di {raw.get('title') or 'questa avventura'}",
        "secret": f"conosce un dettaglio concreto collegato alla verita centrale su {name}",
        "source_status": "inferred",
        "confidence": 0.62,
    }


def _repair_actors_from_canon(raw: dict) -> dict:
    raw = dict(raw or {})
    npcs = [n for n in (raw.get("npcs") or []) if isinstance(n, dict) and n.get("name")]
    actors = [a for a in (raw.get("actors") or []) if isinstance(a, dict)]
    has_real_npcs = bool(npcs)
    actors_are_placeholder = bool(actors) and all(_looks_like_placeholder_actor(a) for a in actors)
    if raw.get("source_mode") == "pdf_import" and not has_real_npcs and not actors:
        return raw

    if has_real_npcs and (not actors or actors_are_placeholder):
        repaired = []
        for idx, npc in enumerate(npcs, start=1):
            actor = dict(npc)
            actor.setdefault("id", npc.get("id") or f"npc_{idx}")
            actor.setdefault("location_id", npc.get("location") or npc.get("location_id") or "")
            actor.setdefault("goal", npc.get("goal") or npc.get("motivation") or npc.get("description") or "")
            actor.setdefault("secret", npc.get("secret") or "")
            repaired.append(actor)
        raw["actors"] = repaired
        return raw

    if not actors or actors_are_placeholder:
        names = _canon_names_from_text(
            raw.get("hidden_truth", ""),
            raw.get("premise", ""),
            raw.get("win_condition", ""),
            " ".join(str(c.get("label", "")) + " " + str(c.get("reveals", "")) + " " + str(c.get("payoff", "")) for c in (raw.get("clues") or []) if isinstance(c, dict)),
        )
        if names:
            raw["actors"] = [_actor_from_name(name, raw, idx) for idx, name in enumerate(names[:5], start=1)]
    return raw


def _repair_story_threads_from_clues(raw: dict) -> dict:
    """Evita piste autoreferenziali: se il testo e placeholder, ricostruisce da clue canoniche."""
    # LLM-built deduction graphs already have non-placeholder statements and
    # corroboration metadata — leave them alone.
    existing = raw.get("revelations") or raw.get("story_threads") or []
    if existing and any(isinstance(r, dict) and r.get("llm_generated") for r in existing):
        return raw
    clues = [c for c in (raw.get("clues") or []) if isinstance(c, dict)]
    if not clues:
        return raw

    thread_ids: list[str] = []
    for idx, clue in enumerate(clues, start=1):
        tid = str(clue.get("thread_id") or f"T{min(idx, 3)}").strip() or f"T{min(idx, 3)}"
        clue["thread_id"] = tid
        if tid not in thread_ids:
            thread_ids.append(tid)

    by_thread = {tid: [c for c in clues if str(c.get("thread_id")) == tid] for tid in thread_ids}
    existing = [t for t in (raw.get("story_threads") or raw.get("revelations") or []) if isinstance(t, dict)]
    existing_by_id = {str(t.get("thread_id") or t.get("id") or f"T{i}"): t for i, t in enumerate(existing, start=1)}
    repaired = []
    for idx, tid in enumerate(thread_ids[:6], start=1):
        linked = by_thread.get(tid) or []
        current = existing_by_id.get(tid) or (existing[idx - 1] if idx - 1 < len(existing) else {})
        question = _compact_text(current.get("question") or current.get("title") or "", 180)
        answer = _compact_text(current.get("true_answer") or current.get("answer") or current.get("statement") or "", 240)
        if _looks_like_placeholder_thread(question) or (answer and question and answer.lower() == question.lower()):
            question = _derive_thread_question(tid, linked, raw.get("title") or "")
        if _looks_like_placeholder_thread(answer) or not answer or answer.lower() == question.lower():
            answer = _derive_thread_answer(linked, raw.get("hidden_truth") or raw.get("win_condition") or "")
        required = [str(c.get("id") or f"clue_{idx}_{n}") for n, c in enumerate(linked[:3], start=1)]
        for n, clue in enumerate(linked[:3], start=1):
            clue.setdefault("id", required[n - 1])
        repaired.append({
            **current,
            "id": current.get("id") or tid,
            "thread_id": tid,
            "title": _compact_text(current.get("title") or question.replace("?", ""), 120),
            "question": question,
            "true_answer": answer,
            "statement": answer,
            "required_clues": list(current.get("required_clues") or required),
            "minimum_clues_to_deduce": int(current.get("minimum_clues_to_deduce") or min(2, max(1, len(required)))),
            "payoff": _derive_thread_payoff(linked, current.get("payoff") or current.get("purpose") or ""),
        })
    raw["story_threads"] = repaired
    raw["revelations"] = repaired
    raw["clues"] = clues
    return raw


def _merge_ai_generated_shape(raw: dict, genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> dict:
    if raw.get("source_mode") != "ai_generated":
        return raw
    text = " ".join(str(raw.get(k, "")) for k in ("title", "premise", "objective", "win_condition", "hidden_truth"))
    archetype_profile = raw.get("archetype_profile") or detect_archetypes_from_ai_prompt(text, genre_hint or raw.get("genre") or "")
    if runtime_profile_hint:
        archetype_profile = dict(archetype_profile)
    shape = build_shape_for_ai_generated(text, archetype_profile, title=raw.get("title", ""), genre_hint=genre_hint or raw.get("genre"))
    merged = dict(shape)
    merged.update(raw)
    merged["archetype_profile"] = archetype_profile
    merged["runtime_profiles"] = raw.get("runtime_profiles") or shape.get("runtime_profiles")
    # Se il vecchio generatore locale ha prodotto il trio standard, sostituiscilo con la forma archetipica variabile.
    for key in ("locations", "clues", "revelations", "actors", "event_clocks", "finale_conditions"):
        current = raw.get(key)
        if not current or (key in {"locations", "clues"} and len(current) == 3 and raw.get("generation_warning")):
            merged[key] = shape.get(key, current)
    if raw.get("npcs") and not raw.get("actors") and len(raw.get("npcs") or []) != 3:
        merged["npcs"] = raw["npcs"]
    merged = _repair_actors_from_canon(merged)
    return _repair_story_threads_from_clues(merged)


def definition_from_compiler_json(raw: dict, *, source_type: str, title: str = "", genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> AdventureDefinition:
    raw = _merge_ai_generated_shape(dict(raw or {}), genre_hint, runtime_profile_hint)
    raw = concretize_adventure_raw(raw, genre_hint=genre_hint or raw.get("genre") or raw.get("detected_genre") or "")
    raw = _repair_actors_from_canon(raw)
    raw = _repair_story_threads_from_clues(raw)
    source_mode = raw.get("source_mode") or ("pdf_import" if source_type == "pdf_text" else "raw_text")
    preserve_source = source_mode in {"pdf_import", "pdf_import_fallback", "manual_json"} or bool((raw.get("preservation_policy") or {}).get("forbid_structural_compression"))
    content_key = f"{title}|{raw.get('title','')}"
    did = raw.get("id") or "adv_" + hashlib.sha1(content_key.encode("utf-8")).hexdigest()[:10]
    profiles = raw.get("runtime_profiles") or raw.get("runtime_profile") or _profiles_for(str(raw), runtime_profile_hint)
    if isinstance(profiles, str):
        profiles = [profiles]
    objective_statuses = {"hidden", "inactive", "available", "active", "complete", "failed"}
    location_statuses = {"hidden", "unknown", "known", "visited", "locked", "changed", "compromised", "secured", "destroyed"}
    access_states = {"open", "locked", "hidden", "blocked", "restricted", "unlocked", "sealed"}
    actor_statuses = {"unintroduced", "introduced", "active", "exposed", "allied", "hostile", "captured", "resolved", "dead", "missing"}
    faction_statuses = {"quiet", "watching", "active", "escalating", "dominant", "weakened", "broken"}
    revelation_statuses = {"hidden", "seeded", "available", "revealed", "resolved"}
    finale_statuses = {"locked", "seeded", "available", "satisfied", "failed"}
    objectives = []
    for idx, obj in enumerate(raw.get("objectives") or raw.get("objective_stack") or [], start=1):
        if isinstance(obj, str):
            obj = {"label": obj}
        objectives.append(Objective(
            id=obj.get("id") or _id("obj", obj.get("label") or obj.get("title") or "objective", idx),
            label=obj.get("label") or obj.get("title") or obj.get("description") or "Obiettivo",
            status=obj.get("status") if obj.get("status") in objective_statuses else "active",
            success_conditions=list(obj.get("success_conditions") or obj.get("conditions") or []),
            unlocks=list(obj.get("unlocks") or []),
        ))
    if not objectives:
        objective = raw.get("win_condition") or raw.get("objective") or "Completare l'avventura."
        objectives.append(Objective(id="obj_main", label=objective, success_conditions=[objective]))

    revelations = []
    for idx, rev in enumerate(raw.get("revelations") or raw.get("story_threads") or [], start=1):
        revelations.append(Revelation(
            id=rev.get("id") or _id("rev", rev.get("question") or rev.get("statement") or "revelation", idx),
            thread_id=rev.get("thread_id") or rev.get("id") or f"T{idx}",
            statement=rev.get("statement") or rev.get("true_answer") or rev.get("answer") or rev.get("question") or "Rivelazione",
            required_clues=list(rev.get("required_clues") or []),
            required_evidence_kinds=list(rev.get("required_evidence_kinds") or []),
            minimum_independent_kinds=int(rev.get("minimum_independent_kinds") or 1),
            red_herring_clues=list(rev.get("red_herring_clues") or []),
            status=rev.get("status") if rev.get("status") in revelation_statuses else "hidden",
            conditions=list(rev.get("conditions") or []),
            payoff=rev.get("payoff") or rev.get("purpose") or "",
            llm_generated=bool(rev.get("llm_generated", False)),
        ))

    revelation_ids_seen = {r.id for r in revelations}
    revelation_by_thread = {r.thread_id: r.id for r in revelations if r.thread_id}
    clues = []
    for idx, clue in enumerate(raw.get("clues") or [], start=1):
        rid = clue.get("revelation_id") or clue.get("revelation_ids") or clue.get("thread_id") or (revelations[0].id if revelations else "")
        raw_revelation_ids = rid if isinstance(rid, list) else ([rid] if rid else [])
        revelation_ids = []
        for candidate in raw_revelation_ids:
            candidate = str(candidate or "")
            if candidate in revelation_ids_seen:
                revelation_ids.append(candidate)
            elif candidate in revelation_by_thread:
                revelation_ids.append(revelation_by_thread[candidate])
        clues.append(RuntimeClue(
            id=clue.get("id") or _id("clue", clue.get("label") or clue.get("text") or "clue", idx),
            label=clue.get("label") or clue.get("text") or "Indizio",
            type=clue.get("type") or "physical_evidence",
            thread_id=clue.get("thread_id") or (revelations[0].thread_id if revelations else ""),
            source_location=clue.get("source_location") or clue.get("location") or "",
            reveals=clue.get("reveals") or "",
            payoff=clue.get("payoff") or "",
            revelation_ids=revelation_ids,
            is_required=bool(clue.get("is_required", True)),
            immediate_information=clue.get("immediate_information") or clue.get("text") or clue.get("label") or "",
            hidden_implication=clue.get("hidden_implication") or clue.get("reveals") or "",
            unlocks=list(clue.get("unlocks") or []),
            possible_actions=list(clue.get("possible_actions") or []),
            wrong_interpretations=list(clue.get("wrong_interpretations") or []),
            source_ref=dict(clue.get("source_ref") or {}),
            source_status=clue.get("source_status") if clue.get("source_status") in {"explicit", "inferred", "suggested", "generated"} else ("explicit" if clue.get("is_preserved_from_pdf") else "generated"),
            is_preserved_from_pdf=bool(clue.get("is_preserved_from_pdf", False)),
            inferred_payoff=bool(clue.get("inferred_payoff", False)),
            confidence=float(clue.get("confidence", 1.0) or 1.0),
            llm_extracted=bool(clue.get("llm_extracted", False)),
        ))
    if not revelations:
        revelations.append(Revelation(
            id="rev_core",
            thread_id="T1",
            statement=raw.get("hidden_truth") or raw.get("core_truth") or "Verità centrale da rivelare",
            required_clues=[c.id for c in clues[:2]],
            payoff="rende chiara la soluzione della missione",
        ))
    for clue in clues:
        if not clue.revelation_ids:
            clue.revelation_ids = [revelations[0].id]
    if len(clues) < 3 and not preserve_source:
        for idx in range(len(clues) + 1, 4):
            clues.append(RuntimeClue(
                id=f"clue_auto_{idx}",
                label=f"Documento concreto {idx} collegato alla pista",
                thread_id=revelations[0].thread_id,
                source_location="Scena iniziale",
                reveals=revelations[0].statement,
                payoff="supporta la rivelazione centrale",
                revelation_ids=[revelations[0].id],
                immediate_information=f"Documento concreto {idx} con dettaglio verificabile",
                hidden_implication=revelations[0].statement,
                unlocks=[revelations[0].thread_id],
                possible_actions=["esaminare il documento", "confrontarlo con un testimone", "cercare conferme nella location"],
                wrong_interpretations=["scambiarlo per dettaglio d'atmosfera"],
            ))

    locations = []
    for idx, loc in enumerate(raw.get("locations") or [], start=1):
        if isinstance(loc, str):
            loc = {"name": loc}
        locations.append(LocationState(
            id=loc.get("id") or _id("loc", loc.get("name") or "location", idx),
            name=loc.get("name") or "Location",
            description=loc.get("description") or "",
            status=loc.get("status") if loc.get("status") in location_statuses else "known",
            type=loc.get("type") or loc.get("kind") or "location",
            access_state=loc.get("access_state") if loc.get("access_state") in access_states else "open",
            access_requirements=list(loc.get("access_requirements") or []),
            tactical_map=loc.get("tactical_map") or {},
            contains_clues=[c.id for c in clues if c.source_location and loc.get("name", "").lower() in c.source_location.lower()],
            visual_identity=loc.get("visual_identity") or "",
            gameplay_function=loc.get("gameplay_function") or "",
            concrete_features=list(loc.get("concrete_features") or []),
            hazards=list(loc.get("hazards") or []),
            exits=list(loc.get("exits") or []),
            locked_paths=list(loc.get("locked_paths") or []),
            clue_slots=list(loc.get("clue_slots") or []),
            tactical_features=list(loc.get("tactical_features") or []),
            source_ref=dict(loc.get("source_ref") or {}),
            source_status=loc.get("source_status") if loc.get("source_status") in {"explicit", "inferred", "suggested", "generated"} else ("explicit" if loc.get("is_preserved_from_pdf") else "generated"),
            original_room_number=str(loc.get("original_room_number") or ""),
            original_section=str(loc.get("original_section") or ""),
            is_preserved_from_pdf=bool(loc.get("is_preserved_from_pdf", False)),
            inferred_runtime_fields=list(loc.get("inferred_runtime_fields") or []),
            confidence=float(loc.get("confidence", 1.0) or 1.0),
        ))
    if not locations:
        locations.append(LocationState(id="loc_start", name="Scena iniziale", description=raw.get("premise") or ""))

    actors = []
    for idx, actor in enumerate(raw.get("actors") or raw.get("npcs") or [], start=1):
        actors.append(ActorState(
            id=actor.get("id") or _id("actor", actor.get("name") or "actor", idx),
            name=actor.get("name") or "PNG",
            role=actor.get("role") or "neutral",
            location_id=actor.get("location_id") or actor.get("location") or "",
            status=actor.get("status") if actor.get("status") in actor_statuses else "unintroduced",
            goal=actor.get("goal") or actor.get("agenda") or actor.get("motivation") or f"proteggere il proprio ruolo in {raw.get('title') or 'questa avventura'}",
            secret=actor.get("secret") or "",
            fear=actor.get("fear") or "",
            current_plan=actor.get("current_plan") or "seguire la propria agenda finche i PG non fanno pressione",
            fallback_plan=actor.get("fallback_plan") or "spostarsi, negoziare o rivelare informazioni parziali sotto pressione",
            resources=list(actor.get("resources") or []),
            knows=list(actor.get("knows") or []),
            wants=list(actor.get("wants") or []),
            avoids=list(actor.get("avoids") or []),
            pressure_response=dict(actor.get("pressure_response") or {"low": "osserva", "medium": "tratta", "high": "agisce", "critical": "rivela o forza una svolta"}),
            reaction_table=dict(actor.get("reaction_table") or {}),
            relationships=list(actor.get("relationships") or []),
            source_ref=dict(actor.get("source_ref") or {}),
            source_status=actor.get("source_status") if actor.get("source_status") in {"explicit", "inferred", "suggested", "generated"} else ("explicit" if actor.get("is_preserved_from_pdf") else "generated"),
            is_preserved_from_pdf=bool(actor.get("is_preserved_from_pdf", False)),
            inferred_agenda=bool(actor.get("inferred_agenda", False)),
            confidence=float(actor.get("confidence", 1.0) or 1.0),
            llm_enriched=bool(actor.get("llm_enriched", False)),
        ))

    clocks = []
    for idx, clock in enumerate(raw.get("event_clocks") or [], start=1):
        clocks.append(EventClock(
            id=clock.get("id") or _id("clock", clock.get("label") or "clock", idx),
            label=clock.get("label") or clock.get("name") or "Clock",
            value=int(clock.get("value") or clock.get("progress") or 0),
            max_value=max(1, int(clock.get("max_value") or clock.get("max") or 6)),
            consequence=clock.get("consequence") or clock.get("on_complete") or "",
            on_complete=clock.get("on_complete") or clock.get("consequence") or "",
            steps=list(clock.get("steps") or []),
            source_ref=dict(clock.get("source_ref") or {}),
            source_status=clock.get("source_status") if clock.get("source_status") in {"explicit", "inferred", "suggested", "generated"} else ("explicit" if clock.get("is_explicit_from_source") else "generated"),
            is_explicit_from_source=bool(clock.get("is_explicit_from_source", False)),
            is_inferred=bool(clock.get("is_inferred", False)),
            confidence=float(clock.get("confidence", 1.0) or 1.0),
        ))
    if not clocks and not preserve_source:
        clocks.append(EventClock(id="clock_main", label=raw.get("threat_description") or "Pressione principale", max_value=int(raw.get("threat_max_turns") or 8), on_complete="La minaccia si compie."))

    pressures = [
        PressureSystem(
            id=p.get("id") or _id("pressure", p.get("label") or "pressure", i),
            label=p.get("label") or p.get("name") or "Pressione",
            value=int(p.get("value") or 0),
            max_value=max(1, int(p.get("max_value") or 10)),
            description=p.get("description") or "",
        )
        for i, p in enumerate(raw.get("pressure_systems") or [], start=1) if isinstance(p, dict)
    ]

    core_truths = []
    for idx, truth in enumerate(raw.get("core_truths") or raw.get("hidden_truths") or [], start=1):
        if isinstance(truth, str):
            truth = {"statement": truth}
        core_truths.append(HiddenTruth(
            id=truth.get("id") or _id("truth", truth.get("statement") or "truth", idx),
            statement=truth.get("statement") or "",
            reveal_clues=list(truth.get("reveal_clues") or [c.id for c in clues[:2]]),
            reveal_rule=truth.get("reveal_rule") or "quando gli indizi richiesti sono scoperti",
        ))
    if not core_truths:
        core_truths.append(HiddenTruth(id="truth_core", statement=raw.get("hidden_truth") or raw.get("core_truth") or "", reveal_clues=[c.id for c in clues[:2]]))

    finales = []
    for idx, fin in enumerate(raw.get("finale_conditions") or [], start=1):
        if isinstance(fin, str):
            fin = {"label": fin}
        finales.append(FinaleCondition(
            id=fin.get("id") or _id("finale", fin.get("label") or "finale", idx),
            label=fin.get("label") or fin.get("description") or "Finale",
            required_clues=list(fin.get("required_clues") or []),
            required_threads=list(fin.get("required_threads") or []),
            status=fin.get("status") if fin.get("status") in finale_statuses else "locked",
            depends_on=list(fin.get("depends_on") or []),
            method=fin.get("method") or "",
            concrete_choice=fin.get("concrete_choice") or "",
        ))
    if not finales:
        finales.append(FinaleCondition(
            id="finale_main",
            label=objectives[0].label,
            required_clues=[c.id for c in clues if c.is_required][:2],
            depends_on=[objectives[0].id],
            method="usare almeno due prove nella location finale",
            concrete_choice="scegliere una risoluzione concreta basata sugli indizi raccolti",
        ))

    normalized_genre = normalize_runtime_genre(genre_hint or raw.get("genre") or raw.get("detected_genre") or "", "detective_classico")
    genre_profile = get_genre_profile(profiles, normalized_genre)
    return AdventureDefinition(
        id=did,
        title=title or raw.get("title") or "Avventura compilata",
        source_type=source_type,
        source_mode=source_mode,
        source_structure=dict(raw.get("source_structure") or {}),
        archetype_profile=dict(raw.get("archetype_profile") or {}),
        preservation_policy=dict(raw.get("preservation_policy") or {}),
        original_structure_map=dict(raw.get("original_structure_map") or {}),
        source_cards=list(raw.get("source_cards") or (raw.get("source_structure") or {}).get("source_cards") or []),
        inferred_elements=list(raw.get("inferred_elements") or []),
        preserved_elements=list(raw.get("preserved_elements") or []),
        genre=normalized_genre,
        runtime_profiles=profiles,
        tone=raw.get("tone") or raw.get("atmosphere") or "",
        premise=raw.get("premise") or "",
        initial_hook=raw.get("initial_hook") or raw.get("hook") or raw.get("premise") or "",
        core_truths=core_truths,
        objectives=objectives,
        revelations=revelations,
        clues=clues,
        actors=actors,
        factions=[
            FactionState(
                id=f.get("id") or _id("faction", f.get("name") or "faction", i),
                name=f.get("name") or "Fazione",
                agenda=f.get("agenda") or f.get("goal") or "",
                pressure=int(f.get("pressure") or 0),
                status=f.get("status") if f.get("status") in faction_statuses else "quiet",
                source_ref=dict(f.get("source_ref") or {}),
                source_status=f.get("source_status") if f.get("source_status") in {"explicit", "inferred", "suggested", "generated"} else "generated",
                confidence=float(f.get("confidence", 1.0) or 1.0),
            )
            for i, f in enumerate(raw.get("factions") or [], start=1) if isinstance(f, dict)
        ],
        locations=locations,
        event_clocks=clocks,
        pressure_systems=pressures,
        resources=[
            ResourceState(
                id=r.get("id") or _id("resource", r.get("label") or r.get("name") or "resource", i),
                label=r.get("label") or r.get("name") or "Risorsa",
                value=int(r.get("value") or 0),
                max_value=int(r.get("max_value") or r.get("max") or 0),
            )
            for i, r in enumerate(raw.get("resources") or [], start=1) if isinstance(r, dict)
        ],
        finale_conditions=finales,
        genre_runtime=raw.get("genre_runtime") or {},
        genre_profile=genre_profile,
        suggestions=list(raw.get("suggestions") or []),
    )


def initialize_runtime_state(definition: AdventureDefinition) -> AdventureRuntimeState:
    clue_to_revelation_ids: dict[str, list[str]] = {}
    thread_to_revelation_ids: dict[str, list[str]] = {}
    revelation_to_thread_id: dict[str, str] = {}
    for revelation in definition.revelations:
        thread_id = revelation.thread_id or revelation.id
        revelation_to_thread_id[revelation.id] = thread_id
        thread_to_revelation_ids.setdefault(thread_id, [])
        if revelation.id not in thread_to_revelation_ids[thread_id]:
            thread_to_revelation_ids[thread_id].append(revelation.id)
    for clue in definition.clues:
        linked = list(clue.revelation_ids or [])
        if clue.thread_id:
            linked.extend(thread_to_revelation_ids.get(clue.thread_id, []))
        clue_to_revelation_ids[clue.id] = list(dict.fromkeys([rid for rid in linked if rid]))
    active_revelations = [
        r.id for r in definition.revelations
        if r.status in {"hidden", "seeded", "available", "revealed"}
    ][:6]
    return AdventureRuntimeState(
        definition_id=definition.id,
        current_scene_id=definition.locations[0].id if definition.locations else None,
        active_objective_ids=[o.id for o in definition.objectives if o.status in {"available", "active"}] or ([definition.objectives[0].id] if definition.objectives else []),
        completed_objective_ids=[o.id for o in definition.objectives if o.status == "complete"],
        failed_objective_ids=[o.id for o in definition.objectives if o.status == "failed"],
        revealed_truth_ids=[t.id for t in definition.core_truths if t.revealed],
        active_revelation_ids=active_revelations or [r.id for r in definition.revelations[:3]],
        ready_revelation_ids=[r.id for r in definition.revelations if r.status == "available"],
        resolved_revelation_ids=[r.id for r in definition.revelations if r.status == "resolved"],
        actor_runtime={
            a.id: {
                "status": a.status,
                "location_id": a.location_id,
                "agenda_pressure": a.agenda_pressure,
                "goal": a.goal,
                "current_plan": a.current_plan,
                "fallback_plan": a.fallback_plan,
                "pressure_response": a.pressure_response,
            }
            for a in definition.actors
        },
        faction_runtime={f.id: {"status": f.status, "pressure": f.pressure} for f in definition.factions},
        location_runtime={l.id: {"status": l.status, "access_state": l.access_state} for l in definition.locations},
        clock_runtime={c.id: {"value": c.value, "max": c.max_value, "active": c.active} for c in definition.event_clocks},
        pressure_runtime={p.id: {"value": p.value, "max": p.max_value} for p in definition.pressure_systems},
        resource_runtime={r.id: {"value": r.value, "max": r.max_value} for r in definition.resources},
        finale_runtime={f.id: {"status": f.status, "required_threads": f.required_threads, "required_clues": f.required_clues, "depends_on": f.depends_on} for f in definition.finale_conditions},
        truth_runtime={t.id: {"revealed": t.revealed, "reveal_clues": t.reveal_clues, "reveal_rule": t.reveal_rule} for t in definition.core_truths},
        clue_to_revelation_ids=clue_to_revelation_ids,
        thread_to_revelation_ids=thread_to_revelation_ids,
        revelation_to_thread_id=revelation_to_thread_id,
    )


def _legacy_thread_question(revelation: Revelation, clues: list[RuntimeClue], title: str = "") -> str:
    raw = str(revelation.statement or "")
    if raw.endswith("?") and not _looks_like_placeholder_thread(raw):
        return raw
    clue_dicts = [
        {
            "label": c.label,
            "text": c.immediate_information or c.label,
            "reveals": c.reveals,
            "payoff": c.payoff,
            "source_location": c.source_location,
        }
        for c in clues
    ]
    return _derive_thread_question(revelation.thread_id or revelation.id, clue_dicts, title)


def legacy_adventure_from_definition(definition: AdventureDefinition) -> dict:
    first_clock = definition.event_clocks[0] if definition.event_clocks else None
    clues_by_revelation = {
        r.id: [
            c for c in definition.clues
            if r.id in c.revelation_ids or c.thread_id == r.thread_id or c.id in r.required_clues
        ]
        for r in definition.revelations
    }
    return {
        "id": definition.id,
        "title": definition.title,
        "genre": definition.genre,
        "detected_genre": definition.genre,
        "premise": definition.premise or definition.initial_hook,
        "hidden_truth": definition.core_truths[0].statement if definition.core_truths else "",
        "win_condition": definition.objectives[0].label if definition.objectives else "",
        "threat_description": first_clock.label if first_clock else "Pressione dell'avventura",
        "threat_max_turns": first_clock.max_value if first_clock else 8,
        "has_time_pressure": bool(first_clock),
        "from_runtime_compiler": True,
        "source_mode": definition.source_mode,
        "archetype_profile": definition.archetype_profile,
        "preservation_policy": definition.preservation_policy,
        "source_cards": definition.source_cards,
        "preserved_elements": definition.preserved_elements,
        "inferred_elements": definition.inferred_elements,
        "adventure_definition_id": definition.id,
        "adventure_canon": {
            "core_truth": definition.core_truths[0].statement if definition.core_truths else "",
            "main_antagonist": next((a.name for a in definition.actors if "antagon" in a.role.lower()), ""),
            "key_locations": [l.name for l in definition.locations],
            "required_clues": [c.id for c in definition.clues if c.is_required],
            "finale_conditions": [f.label for f in definition.finale_conditions],
            "genre_profile": definition.genre_profile.model_dump() if hasattr(definition.genre_profile, "model_dump") else definition.genre_profile,
        },
        "story_threads": [
            {
                "id": r.thread_id or r.id,
                "title": _legacy_thread_question(r, clues_by_revelation.get(r.id, []), definition.title).replace("?", "")[:100],
                "question": _legacy_thread_question(r, clues_by_revelation.get(r.id, []), definition.title),
                "true_answer": r.statement,
                "required_clues": r.required_clues or [c.id for c in definition.clues if r.id in c.revelation_ids][:3],
                "minimum_clues_to_deduce": min(2, max(1, len(r.required_clues or []))),
                "payoff": r.payoff,
                "status": "hidden",
            }
            for r in definition.revelations
        ],
        "clues": [
            {
                "id": c.id,
                "label": c.label,
                "text": c.label,
                "type": c.type,
                "thread_id": c.thread_id or (definition.revelations[0].thread_id if definition.revelations else "T1"),
                "reveals": c.reveals,
                "payoff": c.payoff,
                "location": c.source_location,
                "immediate_information": c.immediate_information,
                "hidden_implication": c.hidden_implication,
                "unlocks": c.unlocks,
                "possible_actions": c.possible_actions,
                "wrong_interpretations": c.wrong_interpretations,
                "found": False,
                "source_ref": c.source_ref,
                "source_status": c.source_status,
                "is_preserved_from_pdf": c.is_preserved_from_pdf,
                "confidence": c.confidence,
            }
            for c in definition.clues
        ],
        "npcs": [
            {
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "description": a.goal,
                "location": a.location_id,
                "secret": a.secret,
                "status": "alive" if a.status in {"active", "unintroduced", "exposed"} else a.status,
                "npc_agenda": {
                    "role": a.role if a.role in {"ally", "antagonist", "witness", "red_herring", "victim", "patron", "neutral"} else "neutral",
                    "goal": a.goal,
                    "fear": a.fear,
                    "current_plan": a.current_plan,
                    "fallback_plan": a.fallback_plan,
                    "resources": a.resources,
                    "knows": a.knows,
                    "wants": a.wants,
                    "avoids": a.avoids,
                    "pressure_response": a.pressure_response,
                    "reaction_table": a.reaction_table,
                    "secret": a.secret,
                    "arc_status": a.status,
                    "recurrence_priority": "high" if "antagon" in a.role.lower() else "medium",
                },
                "source_ref": a.source_ref,
                "source_status": a.source_status,
                "is_preserved_from_pdf": a.is_preserved_from_pdf,
                "confidence": a.confidence,
            }
            for a in definition.actors
        ],
        "locations": [
            {
                "id": l.id,
                "name": l.name,
                "description": l.description,
                "type": l.type,
                "visual_identity": l.visual_identity,
                "gameplay_function": l.gameplay_function,
                "concrete_features": l.concrete_features,
                "hazards": l.hazards,
                "exits": l.exits,
                "locked_paths": l.locked_paths,
                "clue_slots": l.clue_slots,
                "tactical_features": l.tactical_features,
                "has_combat_potential": bool((l.tactical_map or {}).get("enabled")),
                "tactical_map": l.tactical_map,
                "source_ref": l.source_ref,
                "source_status": l.source_status,
                "is_preserved_from_pdf": l.is_preserved_from_pdf,
                "original_room_number": l.original_room_number,
                "original_section": l.original_section,
                "confidence": l.confidence,
            }
            for l in definition.locations
        ],
        "event_clocks": [
            {
                "id": c.id,
                "label": c.label,
                "value": c.value,
                "max": c.max_value,
                "consequence": c.consequence,
                "on_complete": c.on_complete,
                "steps": c.steps,
                "active": c.active,
                "source_ref": c.source_ref,
                "source_status": c.source_status,
                "is_explicit_from_source": c.is_explicit_from_source,
                "is_inferred": c.is_inferred,
                "confidence": c.confidence,
            }
            for c in definition.event_clocks
        ],
        "events": [
            {
                "id": f"{c.id}_step_{step.get('step') or idx}",
                "clock_id": c.id,
                "label": step.get("world_state_change") or step.get("event") or c.label,
                "scene_prompt": step.get("scene_prompt") or "",
                "possible_player_response": step.get("possible_player_response") or "",
                "location_id": step.get("location_id") or "",
                "source_status": c.source_status,
            }
            for c in definition.event_clocks
            for idx, step in enumerate(c.steps or [], start=1)
            if isinstance(step, dict)
        ],
    }


def compile_from_raw_structure(raw: dict, *, source_type: str, title: str = "", genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> dict:
    definition = definition_from_compiler_json(
        raw,
        source_type=source_type,
        title=title,
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )
    definition.legacy_adventure = legacy_adventure_from_definition(definition)
    runtime_state = initialize_runtime_state(definition)
    validation = validate_adventure_definition(definition)
    return {
        "adventure_definition": definition,
        "runtime_state": runtime_state,
        "validation_report": validation,
    }


def _apply_llm_metadata(
    text: str,
    structure: dict,
    archetype_profile: dict,
    genre_hint: str | None,
    *,
    title: str = "",
    source_mode: str = "pdf_import",
) -> tuple[dict, str | None, dict | None]:
    """Try the LLM classifier and merge its output with the heuristic profile.

    Returns ``(archetype_profile, genre_hint, llm_meta)``. The LLM result wins
    when (a) no genre hint was supplied by the caller, or (b) the LLM is at
    least as confident as the heuristic. Heuristic secondaries are preserved
    as a union when the LLM ones overlap.
    """
    llm_meta = classify_adventure_metadata(
        text or "",
        source_cards=structure.get("source_cards") if isinstance(structure, dict) else None,
        title=title,
    )
    if not llm_meta:
        return archetype_profile, genre_hint, None

    heuristic_confidence = float(archetype_profile.get("confidence") or 0.0)
    llm_confidence = float(llm_meta.get("confidence") or 0.0)

    # Heuristic remains authoritative if it's clearly more confident.
    if llm_confidence + 0.05 < heuristic_confidence:
        archetype_profile = dict(archetype_profile)
        archetype_profile["llm_metadata"] = llm_meta
        return archetype_profile, genre_hint, llm_meta

    primary = llm_meta["primary_archetype"]
    archetype_def = get_archetype(primary)
    merged_secondaries = list(llm_meta.get("secondary_archetypes") or [])
    for fallback in archetype_profile.get("secondary_archetypes") or []:
        if fallback and fallback not in merged_secondaries and fallback != primary:
            merged_secondaries.append(fallback)
    merged_secondaries = merged_secondaries[:4]

    new_profile = {
        "primary_archetype": primary,
        "secondary_archetypes": merged_secondaries,
        "confidence": round(max(llm_confidence, heuristic_confidence * 0.8), 2),
        "reason": llm_meta.get("reason") or archetype_profile.get("reason") or f"LLM classifier: {primary}",
        "definition": archetype_def,
        "source": "llm",
        "llm_metadata": llm_meta,
        "heuristic_primary": archetype_profile.get("primary_archetype"),
    }
    if source_mode in {"pdf_import", "pdf_import_fallback"}:
        new_profile["structure_authority"] = "label_only_do_not_compress"

    # Caller may have left genre_hint empty; let the LLM fill it. We never
    # override an explicit user hint here — the user knows their material.
    chosen_genre_hint = genre_hint or llm_meta.get("genre")
    return new_profile, chosen_genre_hint, llm_meta


def _compile_pdf_structure_to_runtime(
    text: str,
    structure: dict,
    *,
    title: str = "",
    genre_hint: str | None = None,
    runtime_profile_hint: str | None = None,
) -> dict:
    counts = structure.get("counts") or {}
    has_playable_material = any(int(counts.get(k) or 0) > 0 for k in ("rooms", "clues", "npcs", "factions", "encounters", "events", "maps"))
    if not has_playable_material:
        raise ValueError(
            "Il PDF non sembra un modulo avventura giocabile: non ho trovato stanze, indizi, PNG, incontri, eventi o mappe riconoscibili."
        )
    archetype_profile = detect_archetypes_from_pdf_structure("pdf_import", structure, genre_hint or "", {"length": len(text or "")})
    archetype_profile, genre_hint, _llm_meta = _apply_llm_metadata(
        text, structure, archetype_profile, genre_hint, title=title, source_mode="pdf_import",
    )
    enriched_clues = extract_clues_with_llm(text, structure, title=title)
    if enriched_clues is not None:
        structure = dict(structure)
        structure["clues"] = enriched_clues
        counts = dict(structure.get("counts") or {})
        counts["clues"] = len(enriched_clues)
        structure["counts"] = counts
    enriched_actors = enrich_actors_with_llm(text, structure, title=title)
    if enriched_actors is not None:
        structure = dict(structure)
        structure["npcs"] = enriched_actors
    deduction_revelations = build_deduction_graph_with_llm(text, structure, title=title)
    if deduction_revelations is not None:
        structure = dict(structure)
        structure["revelations"] = deduction_revelations
    policy = build_preservation_policy("pdf_import", structure, archetype_profile)
    raw = build_shape_for_pdf_import(
        text or "",
        structure,
        archetype_profile,
        policy,
        title=title,
        genre_hint=genre_hint,
    )
    if runtime_profile_hint:
        raw["runtime_profiles"] = [runtime_profile_hint]
    llm_meta = archetype_profile.get("llm_metadata") or {}
    synthesis = synthesize_narrative_with_llm(
        text,
        structure,
        title=title,
        genre=genre_hint or llm_meta.get("genre", ""),
        archetype=archetype_profile.get("primary_archetype", ""),
        tone=llm_meta.get("tone", ""),
    )
    if synthesis:
        for key, value in synthesis.items():
            raw[key] = value
    if llm_meta.get("tone"):
        raw["tone"] = llm_meta["tone"]
    return compile_from_raw_structure(
        raw,
        source_type="pdf_text",
        title=title,
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )


def compile_pdf_to_runtime(text: str, *, title: str = "", genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> dict:
    structure = extract_pdf_structure(text or "")
    return _compile_pdf_structure_to_runtime(
        text or "",
        structure,
        title=title,
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )


def compile_pdf_pages_to_runtime(text_pages: list[str], *, title: str = "", genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> dict:
    cleaned_pages = [page for page in (text_pages or []) if str(page or "").strip()]
    text = "\n\n".join(cleaned_pages)
    structure = extract_pdf_structure_from_pages(cleaned_pages)
    return _compile_pdf_structure_to_runtime(
        text,
        structure,
        title=title,
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )


def compile_structured_text_to_runtime(text: str, *, title: str = "", genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> dict:
    structure = extract_pdf_structure(text or "")
    archetype_profile = detect_archetypes_from_pdf_structure("raw_text", structure, genre_hint or "", {"length": len(text or "")})
    archetype_profile, genre_hint, _llm_meta = _apply_llm_metadata(
        text, structure, archetype_profile, genre_hint, title=title, source_mode="raw_text",
    )
    enriched_clues = extract_clues_with_llm(text, structure, title=title)
    if enriched_clues is not None:
        structure = dict(structure)
        structure["clues"] = enriched_clues
        counts = dict(structure.get("counts") or {})
        counts["clues"] = len(enriched_clues)
        structure["counts"] = counts
    enriched_actors = enrich_actors_with_llm(text, structure, title=title)
    if enriched_actors is not None:
        structure = dict(structure)
        structure["npcs"] = enriched_actors
    deduction_revelations = build_deduction_graph_with_llm(text, structure, title=title)
    if deduction_revelations is not None:
        structure = dict(structure)
        structure["revelations"] = deduction_revelations
    policy = build_preservation_policy("pdf_import", structure, archetype_profile)
    policy["source_mode"] = "raw_text"
    policy["reason"] = "raw_text strutturato = preserve before shaping"
    raw = build_shape_for_pdf_import(
        text or "",
        structure,
        archetype_profile,
        policy,
        title=title,
        genre_hint=genre_hint,
    )
    raw["source_mode"] = "raw_text"
    if runtime_profile_hint:
        raw["runtime_profiles"] = [runtime_profile_hint]
    llm_meta = archetype_profile.get("llm_metadata") or {}
    synthesis = synthesize_narrative_with_llm(
        text,
        structure,
        title=title,
        genre=genre_hint or llm_meta.get("genre", ""),
        archetype=archetype_profile.get("primary_archetype", ""),
        tone=llm_meta.get("tone", ""),
    )
    if synthesis:
        for key, value in synthesis.items():
            raw[key] = value
    if llm_meta.get("tone"):
        raw["tone"] = llm_meta["tone"]
    return compile_from_raw_structure(
        raw,
        source_type="raw_text",
        title=title,
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )


def compile_ai_generated_to_runtime(text: str, *, title: str = "", genre_hint: str | None = None, runtime_profile_hint: str | None = None) -> dict:
    archetype_profile = detect_archetypes_from_ai_prompt(text or "", genre_hint or "")
    raw = build_shape_for_ai_generated(text or "", archetype_profile, title=title, genre_hint=genre_hint)
    if runtime_profile_hint:
        raw["runtime_profiles"] = [runtime_profile_hint]
    return compile_from_raw_structure(
        raw,
        source_type="raw_text",
        title=title,
        genre_hint=genre_hint,
        runtime_profile_hint=runtime_profile_hint,
    )
