from __future__ import annotations

from .runtime_models import AdventureRuntime
from .escalation_limiter import compute_allowed_escalation_tier, TIER_DESCRIPTIONS
from .genre_constraints import get_genre_profile
from .scene_context import present_actors_at, visible_clues_at
from .revelation_controller import pacing_score, suggest_revelation_timing


_PHASE_LABELS = {
    "investigation": "INDAGINE",
    "extraction":    "ESTRAZIONE PROVE",
    "escape":        "FUGA / SOPRAVVIVENZA",
    "delivery":      "CONSEGNA / FINALE",
}

_EXTRACTION_DIRECTIVE = (
    "MODALITÀ ESTRAZIONE PROVE: i giocatori hanno già raccolto prove sufficienti. "
    "Non proporre ulteriori attività investigative. "
    "L'obiettivo ora è: proteggere le prove, mettere in sicurezza i testimoni, "
    "raggiungere un'autorità affidabile o un luogo sicuro, evitare la polizia corrotta. "
    "Ogni scena deve muovere il gruppo verso la consegna delle prove o la fuga."
)

_ESCAPE_DIRECTIVE = (
    "MODALITÀ FUGA CRITICA: il tempo è quasi scaduto. "
    "Non si raccolgono nuovi indizi — la priorità assoluta è sopravvivere e portare le prove in salvo. "
    "Ogni turno di esitazione ha un costo immediato. "
    "Proponi solo azioni di movimento, evasione, protezione o consegna urgente."
)

_DELIVERY_DIRECTIVE = (
    "MODALITÀ CONSEGNA / FINALE: le condizioni per il finale sono soddisfatte. "
    "Prepara la scena conclusiva: consegna delle prove, confronto finale con l'antagonista, "
    "o fuga con il testimone al sicuro."
)


def make_director_decision(
    runtime: AdventureRuntime,
    simulation: dict,
    *,
    prerolled: dict | None = None,
    current_scene_id: str | None = None,
    investigation_progress: int = 0,
) -> dict:
    """Trasforma lo stato simulato in una direttiva singola e concreta per il renderer AI."""
    prerolled = prerolled or {}
    success = bool(prerolled.get("success", True))
    ready = list(simulation.get("ready_threads") or [])
    clue_id = simulation.get("selected_clue_id")
    npcs_to_introduce = simulation.get("npcs_to_introduce") or []
    clock_tick = int(simulation.get("clock_tick") or 0)
    clock_triggers = simulation.get("clock_triggers") or []
    action_intent = str(prerolled.get("intent") or "")
    phase = simulation.get("narrative_phase") or "investigation"
    fail_tier = simulation.get("fail_tier") or "none"
    urgency_warnings = simulation.get("urgency_warnings") or []
    next_best_actions = simulation.get("next_best_actions") or []
    witness_updates = simulation.get("witness_updates") or []

    # N4: pacing control — anti-dump e cadenza rivelazioni
    _canonical_log = simulation.get("canonical_log") or []
    _current_turn = int(simulation.get("current_turn") or 0)
    _pacing = pacing_score(_canonical_log, _current_turn)
    _rev_timing = suggest_revelation_timing(_pacing, available_revelations=len(ready))
    if _rev_timing == "hold" and ready and not clock_triggers:
        # Blocca la prima ready revelation per anti-dump; la riprende al turno prossimo
        ready = ready[1:]

    genre_profile = runtime.genre_profile.model_dump() if hasattr(runtime.genre_profile, "model_dump") else (runtime.genre_profile or {})
    if not genre_profile:
        genre_profile = get_genre_profile([runtime.runtime_profile], runtime.genre)
    allowed_tier = compute_allowed_escalation_tier(
        prerolled,
        action_intent,
        runtime.runtime_profile,
        active_clocks=[{"completed": bool(clock_triggers), "tick": clock_tick}],
        scene_context={
            "completed_clock": bool(clock_triggers),
            "finale_condition_met": any(f.status == "satisfied" for f in runtime.finale_conditions),
        },
        genre_profile=genre_profile,
        investigation_progress=investigation_progress,
    )
    primary_archetype = (runtime.archetype_profile or {}).get("primary_archetype") or runtime.runtime_profile
    archetype_bias = {
        "investigation_graph": "Bias archetipo: privilegia indizi, deduzioni, testimoni e conflitti sociali; evita combattimenti gratuiti.",
        "room_keyed_dungeon": "Bias archetipo: privilegia esplorazione stanza, accessi, rischi, risorse e mappa.",
        "heist": "Bias archetipo: privilegia security response, heat, route choices e risorse di estrazione.",
        "survival_escape": "Bias archetipo: privilegia route, safe node, risorse, pericolo e ritirata possibile.",
        "horror_survival": "Bias archetipo: privilegia dread, informazione parziale e costi locali senza catastrofi non autorizzate.",
        "romance_drama": "Bias archetipo: privilegia relazione, scelta emotiva, segreti personali e conseguenze sociali.",
        "military_operation": "Bias archetipo: privilegia obiettivi tattici, terreno, forze, vincoli e tempo.",
        "faction_sandbox": "Bias archetipo: privilegia agende di fazione, eventi offscreen e cambi di alleanza.",
    }.get(primary_archetype, "")

    # ── Gerarchia di priorità ────────────────────────────────────────────────
    # 1. Clock completo (conseguenza inevitabile)
    # 2. Fase escape/extraction/delivery (override investigativo)
    # 3. Deduzione pronta (pista quasi chiusa)
    # 4. Testimone in crisi
    # 5. NPC da introdurre
    # 6. Indizio da avanzare (solo fase investigation)
    # 7. Fallimento / idle

    if clock_triggers:
        t = clock_triggers[0]
        scene_directive = (
            f"CLOCK COMPLETO [{t['label']}]: la conseguenza si manifesta ora. "
            f"Narra: {t['consequence'] or t['on_complete']}. Non è evitabile."
        )
    elif phase == "escape":
        scene_directive = _ESCAPE_DIRECTIVE
    elif phase == "delivery":
        scene_directive = _DELIVERY_DIRECTIVE
    elif phase == "extraction":
        # In extraction, la deduzione di pista è ancora possibile ma poi si passa all'azione
        if ready:
            rev = next((r for r in runtime.revelations if (r.thread_id or r.id) == ready[0]), None)
            statement = rev.statement if rev else ready[0]
            scene_directive = (
                f"DEDUZIONE FINALE sulla pista '{ready[0]}': {statement}. "
                f"Dopo la deduzione, spingi immediatamente verso l'estrazione prove. {_EXTRACTION_DIRECTIVE}"
            )
        else:
            scene_directive = _EXTRACTION_DIRECTIVE
    elif ready:
        rev = next((r for r in runtime.revelations if (r.thread_id or r.id) == ready[0]), None)
        statement = rev.statement if rev else ready[0]
        scene_directive = (
            f"Offri una scena di deduzione sulla pista '{ready[0]}': {statement}. "
            f"Non aprire nuovi filoni prima di aver chiuso questa."
        )
    elif witness_updates:
        wu = witness_updates[0]
        ws = wu["witness_state"]
        ws_desc = {
            "fearful": "è visibilmente spaventato e difficile da raggiungere",
            "panicked": "sta per fuggire o ritirarsi — i giocatori devono calmarlo o proteggerlo subito",
        }.get(ws, f"è in stato {ws}")
        scene_directive = (
            f"TESTIMONE [{wu['npc_name']}] {ws_desc}. "
            f"Crea una scena in cui questo cambiamento di stato è percepibile e richiede una risposta."
        )
    elif npcs_to_introduce:
        npc_id = npcs_to_introduce[0]
        actor = next((a for a in runtime.actors if a.id == npc_id), None)
        if actor:
            scene_directive = (
                f"Introduci l'attore canonico '{actor.name}' ({actor.role}) in questa scena. "
                f"Obiettivo dell'NPC: {actor.goal or 'non dichiarato'}."
            )
        else:
            scene_directive = f"Introduci l'NPC canonico '{npc_id}' in questa scena."
    elif clue_id:
        clue = next((c for c in runtime.clues if c.id == clue_id), None)
        label = clue.label if clue else clue_id
        clue_role = getattr(clue, "type", "clue") if clue else "clue"
        found_update = simulation.get("proposed_updates", {}).get("clues_found") or []
        if found_update:
            if clue_role in ("payload_object", "finale_key"):
                scene_directive = (
                    f"Narra il recupero dell'OGGETTO CRITICO [{clue_id}]: {label}. "
                    f"Questo è materiale che va fisicamente portato fuori — non basta saperlo, bisogna averlo."
                )
            else:
                scene_directive = (
                    f"Narra l'ottenimento definitivo dell'indizio canonico [{clue_id}]: {label}. "
                    f"Il personaggio lo recupera, legge o conferma in modo chiaro."
                )
        else:
            scene_directive = (
                f"Fai progredire l'indizio canonico [{clue_id}]: {label}. "
                f"Solo avanzamento parziale — non ancora prova completa."
            )
    elif not success:
        # Fail-forward: diversifica la risposta per tier
        if fail_tier == "soft":
            scene_directive = (
                "SOFT FAIL: narra una piccola complicazione o un costo minore (malinteso, ritardo, indizio parziale). "
                "La storia avanza comunque — nessuna conseguenza bloccante."
            )
        elif fail_tier == "hard":
            scene_directive = (
                "HARD FAIL: narra una conseguenza immediata e concreta — un NPC si chiude, "
                "una prova viene a rischio, la posizione del gruppo viene esposta. "
                "La storia non si blocca, ma il costo è reale e visibile."
            )
        else:
            scene_directive = (
                "PRESSURE FAIL: il clock avanza — la minaccia si fa più vicina. "
                "Narra un segnale ambientale che comunica l'aumento di pressione senza chiudere la storia."
            )
    else:
        scene_directive = (
            "Muovi un elemento canonico: NPC che cambia posizione, "
            "clock che si fa sentire nel mondo, o location che rivela qualcosa di nuovo."
        )

    final_directive = f"{scene_directive} {archetype_bias}".strip()

    # Elementi canonici visibili nella scena corrente (per vincoli di visibilità F4)
    scene_clues: list[dict] = []
    scene_actors: list[dict] = []
    if current_scene_id:
        for c in visible_clues_at(None, runtime, current_scene_id):  # type: ignore[arg-type]
            if c.state not in {"discovered", "spent"}:
                scene_clues.append({"id": c.id, "label": c.label, "type": c.type or ""})
        for a in present_actors_at(None, runtime, current_scene_id):  # type: ignore[arg-type]
            if a.status not in {"dead", "captured", "resolved"}:
                scene_actors.append({
                    "id": a.id,
                    "name": a.name,
                    "role": a.role or "",
                    "goal": a.goal or "",
                    "fear": a.fear or "",
                    "current_plan": a.current_plan or "",
                    "pressure_response": a.pressure_response or {},
                })

    return {
        "scene_directive": final_directive,
        "director_notes": simulation.get("events") or [],
        "renderer_priorities": [final_directive],  # backward compat
        "state_updates_required": simulation.get("proposed_updates", {}),
        "runtime_profile": runtime.runtime_profile,
        "genre_profile": genre_profile,
        "allowed_escalation_tier": allowed_tier,
        "allowed_escalation_types": list(genre_profile.get("allowed_escalations") or []),
        "forbidden_escalation_types": list(genre_profile.get("forbidden_escalations") or []),
        "reason": (
            f"Roll={prerolled.get('outcome','?')}; intent={action_intent or '?'}; "
            f"profile={runtime.runtime_profile}; archetype={primary_archetype}; clock_triggers={len(clock_triggers)}; "
            f"phase={phase}; fail_tier={fail_tier}"
        ),
        "director_authorization": allowed_tier >= 5 and bool(clock_triggers),
        # Strutturati
        "selected_clue_id": clue_id,
        "npcs_to_introduce": npcs_to_introduce,
        "clock_tick": clock_tick,
        "clock_triggers": clock_triggers,
        "ready_threads": ready,
        "scene_clues": scene_clues,
        "scene_actors": scene_actors,
        "current_scene_id": current_scene_id or "",
        # Nuovi campi di fase
        "narrative_phase": phase,
        "fail_tier": fail_tier,
        "urgency_warnings": urgency_warnings,
        "next_best_actions": next_best_actions,
        "witness_updates": witness_updates,
        # N4 pacing
        "revelation_pacing": _pacing,
        "revelation_timing": _rev_timing,
    }


def director_prompt_context(decision: dict, canonical_log: list | None = None) -> str:
    directive = decision.get("scene_directive") or "renderizza lo stato corrente"
    notes = "; ".join(decision.get("director_notes") or []) or "nessuna nota"
    required = decision.get("state_updates_required") or {}
    allowed_tier = int(decision.get("allowed_escalation_tier", 3))
    allowed_types = decision.get("allowed_escalation_types") or []
    forbidden_types = decision.get("forbidden_escalation_types") or []

    clue_id = decision.get("selected_clue_id")
    npcs = decision.get("npcs_to_introduce") or []
    clock_tick = int(decision.get("clock_tick") or 0)
    triggers = decision.get("clock_triggers") or []
    ready = decision.get("ready_threads") or []
    rev_timing = decision.get("revelation_timing") or "now"
    scene_clues = decision.get("scene_clues") or []
    scene_actors = decision.get("scene_actors") or []
    current_scene_id = decision.get("current_scene_id") or ""
    phase = decision.get("narrative_phase") or "investigation"
    fail_tier = decision.get("fail_tier") or "none"
    urgency_warnings = decision.get("urgency_warnings") or []
    next_best_actions = decision.get("next_best_actions") or []
    witness_updates = decision.get("witness_updates") or []

    phase_label = _PHASE_LABELS.get(phase, phase.upper())
    tier_desc = TIER_DESCRIPTIONS.get(allowed_tier, f"tier {allowed_tier}")

    lines = [
        "\nNARRATIVE DIRECTOR — ISTRUZIONI VINCOLANTI:",
        "LINGUA: tutta la narrazione, i dialoghi, le descrizioni e le azioni proposte DEVONO essere in ITALIANO. Anche se il materiale sorgente è in inglese. Nomi propri e titoli di luogo possono restare nella lingua originale.",
    ]

    # Canonical event log — fatti già stabiliti dal motore in turni precedenti
    if canonical_log:
        _recent = canonical_log[-10:]
        _canon_lines: list[str] = []
        for _ev in _recent:
            _t = _ev.get("turn", "?")
            _etype = _ev.get("type", "")
            if _etype == "clue_revealed":
                _canon_lines.append(f"  T{_t}: indizio [{_ev.get('clue_id','')}] scoperto definitivamente")
            elif _etype == "clue_partial":
                _canon_lines.append(f"  T{_t}: indizio [{_ev.get('clue_id','')}] parzialmente avanzato")
            elif _etype == "npc_state":
                _canon_lines.append(f"  T{_t}: NPC {_ev.get('npc_name', _ev.get('npc_id',''))} → {_ev.get('status','')}")
            elif _etype == "thread_closed":
                _canon_lines.append(f"  T{_t}: pista [{_ev.get('thread_id','')}] deduzione completata")
            elif _etype == "clock_resolved":
                _canon_lines.append(f"  T{_t}: clock [{_ev.get('clock_id','')}] sventato dai giocatori")
            elif _etype == "clock_triggered":
                _canon_lines.append(f"  T{_t}: clock [{_ev.get('clock_id','')}] COMPLETATO — conseguenza attivata")
            elif _etype == "fact":
                _canon_lines.append(f"  T{_t}: fatto stabilito: {_ev.get('text','')[:80]}")
        if _canon_lines:
            lines.append(
                "FATTI GIÀ STABILITI (non contraddire, non ripetere come sorprese):\n"
                + "\n".join(_canon_lines)
            )

    lines += [
        f"FASE NARRATIVA CORRENTE: {phase_label} — questa fase determina cosa deve fare il gruppo ADESSO.",
        f"DIRETTIVA SCENA: {directive}",
        f"MAX ESCALATION TIER: {allowed_tier} — {tier_desc}",
        f"ESCALATION CONSENTITE: {', '.join(allowed_types[:10]) or 'solo conseguenze locali'}",
        f"ESCALATION VIETATE: {', '.join(forbidden_types[:12]) or 'nessuna dichiarata'}",
    ]

    # Regole fail-forward per tier
    if fail_tier == "soft":
        lines.append(
            "FAIL-FORWARD SOFT: il fallimento produce solo una piccola complicazione narrativa. "
            "NON avanzare il clock principale. NON compromettere NPC. NON mettere prove a rischio. "
            "threat_increase=0."
        )
    elif fail_tier == "pressure":
        lines.append(
            "FAIL-FORWARD PRESSURE: il clock avanza di 1, la situazione si deteriora leggermente. "
            "Narra pressione e tensione, ma nessuna conseguenza irreversibile. threat_increase=1."
        )
    elif fail_tier == "hard":
        lines.append(
            "FAIL-FORWARD HARD: conseguenza concreta e immediata. "
            "Un NPC può cambiare stato (si chiude, fugge, viene catturato), "
            "una prova può essere a rischio, o la posizione del gruppo viene esposta. threat_increase=1."
        )
    else:
        lines.append(
            "SOFT ESCALATION: threat_increase=0 se i giocatori hanno trovato un indizio o chiuso un thread in questo turno. "
            "threat_increase=1 solo su fallimento netto o 3+ turni senza progressi. "
            "MAI threat_increase=2 salvo clock completato."
        )

    # Urgency warnings
    if urgency_warnings:
        top = urgency_warnings[0]
        lines.append(
            f"URGENZA CLOCK {top['urgency']} [{top['clock_label']}] ({int(top['pct']*100)}%): "
            f"{top['message']} — "
            f"{'CAMBIA OBIETTIVO: ' + top['switch_mode'].upper() if top.get('switch_mode') else 'aumenta la pressione narrativa senza bloccare la storia'}."
        )

    # Vincoli di visibilità NPC state lock
    lines.append(
        "NPC STATE LOCK: non narrare NPC morti, catturati, scomparsi o risolti come presenti o disponibili. "
        "Solo NPC con stato 'introduced', 'active', 'exposed', 'allied', 'hostile' possono agire in scena."
    )

    # N2 — Voce NPC in scena: guida comportamentale per coerenza caratteriale
    _voice_actors = [a for a in scene_actors if a.get("goal") or a.get("fear") or a.get("current_plan")]
    if _voice_actors:
        _voice_lines: list[str] = []
        for _a in _voice_actors[:4]:
            _parts: list[str] = []
            if _a.get("goal"):
                _parts.append(f"vuole: {_a['goal'][:70]}")
            if _a.get("fear"):
                _parts.append(f"teme: {_a['fear'][:60]}")
            if _a.get("current_plan"):
                _parts.append(f"piano attuale: {_a['current_plan'][:60]}")
            _pr = _a.get("pressure_response")
            if isinstance(_pr, dict):
                for _k, _v in list(_pr.items())[:2]:
                    _parts.append(f"se {_k}: {str(_v)[:50]}")
            if _parts:
                _voice_lines.append(f"  {_a['name']}: " + " | ".join(_parts))
        if _voice_lines:
            lines.append(
                "VOCE NPC IN SCENA (usa nel tono e nei dialoghi — non svelare direttamente):\n"
                + "\n".join(_voice_lines)
            )

    if current_scene_id:
        if scene_clues:
            clue_list = "; ".join(f"{c['label']} [{c['id']}]" for c in scene_clues[:8])
            lines.append(f"INDIZI PRESENTI IN SCENA ({current_scene_id}): {clue_list}")
        else:
            lines.append(f"INDIZI PRESENTI IN SCENA ({current_scene_id}): nessuno disponibile in questa location")
        if scene_actors:
            actor_list = "; ".join(f"{a['name']} ({a['role']}) [{a['id']}]" for a in scene_actors[:6])
            lines.append(f"NPC PRESENTI IN SCENA: {actor_list}")
        else:
            lines.append(f"NPC PRESENTI IN SCENA: nessuno fisicamente qui ora")
        lines.append(
            "REGOLA VISIBILITÀ: non narrare indizi o NPC assenti da questa lista come fisicamente presenti. "
            "Elementi non in lista possono essere menzionati solo come lontani, voci o ricordi."
        )

    if witness_updates:
        for wu in witness_updates:
            ws = wu["witness_state"]
            lines.append(
                f"TESTIMONE IN CRISI [{wu['npc_name']}]: stato → {ws.upper()}. "
                f"{wu['note']} — Il tuo intervento per calmare/proteggere questo NPC è narrativamente prioritario."
            )
            for wa in (wu.get("available_witness_actions") or []):
                lines.append(
                    f"  AZIONE DISPONIBILE — {wa['label']} "
                    f"(skill: {wa['skill_hint']}): {wa['effect']}"
                )

    if clue_id:
        found_update = required.get("clues_found") or []
        clue_type = "OTTENIMENTO DEFINITIVO" if found_update else "AVANZAMENTO PARZIALE"
        lines.append(f"INDIZIO MOTORE [{clue_type}]: usa solo id={clue_id}. Non creare altri indizi.")
    if npcs:
        lines.append(f"NPC DA INTRODURRE: {', '.join(npcs)}. Devono comparire fisicamente in scena.")
    if clock_tick > 0:
        lines.append(f"CLOCK +{clock_tick}: la minaccia cresce — fallo sentire nel tono e nel contesto.")
    if triggers:
        lines.append(
            f"CLOCK COMPLETO — conseguenza narrativa obbligatoria: "
            f"{triggers[0]['consequence'] or triggers[0]['on_complete']}"
        )
    if ready:
        lines.append(f"PISTE PRONTE: {', '.join(ready)}. Non aprire nuovi filoni prima di offrire deduzione.")
    if rev_timing == "hold":
        lines.append(
            "ANTI-DUMP ATTIVO: troppe rivelazioni recenti. NON presentare ora una deduzione o revelation. "
            "Costruisci tensione o muovi un NPC — la revelation arriva al prossimo turno."
        )
    elif rev_timing == "wait":
        lines.append(
            "PACING REVELATION: il ritmo è già alto. Se possibile, ritarda la deduzione di 1 turno. "
            "Concentra la scena su azione, atmosfera o dialogo."
        )
    if next_best_actions and phase in ("extraction", "escape", "delivery"):
        clean = [a.replace("proteggere_testimone:", "proteggere_testimone ") for a in next_best_actions[:5]]
        lines.append(
            f"AZIONI SUGGERITE DAL MOTORE (fase {phase_label}): "
            + ", ".join(clean)
            + ". Usa queste come opzioni concrete da proporre o da narrare come conseguenza naturale."
        )
    lines.append(f"Note stato: {notes}")
    lines.append(f"State updates decisi dal motore: {required}")
    lines.append(f"Motivo limite escalation: {decision.get('reason','')}")
    lines.append("La AI aggiunge dettagli narrativi, ma NON può contraddire queste istruzioni.")

    return "\n".join(lines)
