from __future__ import annotations

from .runtime_models import AdventureRuntime
from .world_reaction_engine import generate_world_reactions


_INVESTIGATIVE_WORDS = {
    "cerca", "cerco", "indaga", "indagare", "esamina", "esaminare", "legge",
    "leggere", "interroga", "interrogare", "osserva", "analizza", "decifra",
    "studia", "ispeziona", "controlla", "traccia", "segue",
}

_TERMINAL_NPC_STATES = {"dead", "captured", "missing", "resolved"}
_WITNESS_ROLES = {"witness", "informant", "survivor", "bystander", "protected", "testimone"}

# ── E1: Profile cluster mapping ───────────────────────────────────────────────
# Raggruppa i runtime_profile in cluster di comportamento omogeneo.
_PROFILE_CLUSTER: dict[str, str] = {
    "investigation_graph":   "clue",
    "guided_sandbox":        "clue",
    "mythic_quest":          "clue",
    "journey":               "clue",
    "branching_node_graph":  "clue",
    "ritual_dungeon":        "dungeon",
    "room_keyed_dungeon":    "dungeon",
    "pursuit_thriller":      "thriller",
    "survival_escape":       "thriller",
    "escalating_horror":     "horror",
    "heist":                 "heist",
    "faction_crisis":        "faction",
}

def _profile_cluster(runtime: AdventureRuntime) -> str:
    return _PROFILE_CLUSTER.get(runtime.runtime_profile, "clue")


# ── G2: Faction reputation delta ─────────────────────────────────────────────

def _compute_faction_rep_deltas(
    runtime: AdventureRuntime,
    game_state_data: dict,
    prerolled: dict,
    player_action: str,
) -> dict[str, int]:
    """Return per-faction reputation delta for this turn (range -5→+5 total, clamped by caller)."""
    if not runtime.factions:
        return {}

    success = bool(prerolled.get("success", True))
    margin = int(prerolled.get("margin") or 0)
    current_rep: dict[str, int] = {}
    for k, v in (game_state_data.get("faction_reputation") or {}).items():
        try:
            current_rep[k] = int(v)
        except (TypeError, ValueError):
            pass

    rt_state = game_state_data.get("adventure_runtime_state") or {}
    faction_rt = rt_state.get("faction_runtime") or {} if isinstance(rt_state, dict) else {}

    action_lower = str(player_action).lower()
    is_betrayal = any(w in action_lower for w in ("tradisci", "tradisco", "tradire", "tradimento", "inganna alleato"))

    deltas: dict[str, int] = {}
    for faction in runtime.factions:
        fid = faction.id
        rt_entry = faction_rt.get(fid) or {}
        status = rt_entry.get("status") or faction.status
        cur = current_rep.get(fid, 0)

        if is_betrayal and cur > 0:
            # Tradire un alleato della fazione → -2 reputazione
            deltas[fid] = deltas.get(fid, 0) - 2
            continue

        if success and margin >= 2 and status in ("quiet", "watching"):
            # Successo netto: fazioni neutrali/in osservazione aumentano fiducia
            deltas[fid] = deltas.get(fid, 0) + 1

        if not success and margin <= -4 and cur > 0:
            # Fallimento critico: le fazioni alleate perdono fiducia nel gruppo
            deltas[fid] = deltas.get(fid, 0) - 1

    return deltas


# ── G6: Sanità mentale (solo genere horror) ───────────────────────────────────

_HORROR_NPC_ROLES = {"monster", "orrore", "entita", "entità", "cultist", "abomination", "horror_entity"}

def _compute_sanity_damage(
    runtime: AdventureRuntime,
    game_state_data: dict,
    prerolled: dict,
    clock_step_reactions: list[dict],
    npcs_to_introduce: list[str],
) -> list[dict]:
    """Restituisce lista di {player_id, delta} per la sanità — solo in cluster horror."""
    if _profile_cluster(runtime) != "horror":
        return []

    success = bool(prerolled.get("success", True))
    margin = int(prerolled.get("margin") or 0)
    critical = bool(prerolled.get("critical", False))
    player_ids = [p.get("id") for p in (game_state_data.get("players") or []) if p.get("id") is not None]
    if not player_ids:
        return []

    san_hit = 0

    # Fallimento duro in contesto horror → trauma
    if not success and margin <= -3:
        san_hit -= 1
    if not success and (critical or margin <= -5):
        san_hit -= 1  # danno extra per fallimento critico

    # Clock horror che avanza → esposizione a terrore crescente
    if clock_step_reactions:
        san_hit -= 1

    # Introduzione di un'entità horror (prima apparizione)
    actor_map = {a.id: a for a in runtime.actors}
    rt_state = game_state_data.get("adventure_runtime_state") or {}
    actor_rt = rt_state.get("actor_runtime") or {} if isinstance(rt_state, dict) else {}
    for npc_id in npcs_to_introduce:
        actor = actor_map.get(npc_id)
        if actor and actor.role.lower() in _HORROR_NPC_ROLES:
            san_hit -= 1
            break  # max -1 per entità introdotta per turno

    # Successo con margine alto in fase dread/survival → recupero parziale (+1)
    phase_str = str(game_state_data.get("narrative_phase") or "")
    if success and margin >= 3 and phase_str in ("survival", "confrontation"):
        san_hit += 1

    if san_hit == 0:
        return []

    return [{"player_id": pid, "delta": san_hit} for pid in player_ids]


def _action_is_investigative(player_action: str, skill: str = "") -> bool:
    blob = f"{player_action} {skill}".lower()
    return (
        any(w in blob for w in _INVESTIGATIVE_WORDS)
        or any(w in blob for w in ["investig", "perce", "decifr", "cultura"])
    )


def _compute_narrative_phase(runtime: AdventureRuntime, game_state_data: dict) -> str:
    """
    Determina la fase narrativa corrente. Logica dipende dal cluster del runtime_profile.

    Cluster clue      → investigation / extraction / delivery / escape (clue-based)
    Cluster dungeon   → exploration / confrontation / escape (clock/room-based)
    Cluster thriller  → evasion / objective_reached / escape (threat-first)
    Cluster horror    → curiosity / dread / confrontation / survival
    Cluster heist     → planning / infiltration / execution / exfil
    Cluster faction   → assessment / negotiation / confrontation / resolution
    """
    cluster = _profile_cluster(runtime)

    # Terminazione comune: finale soddisfatto
    if any(f.status == "satisfied" for f in runtime.finale_conditions):
        return "delivery"

    # Escape comune: clock terminale ≥ 80%
    for clock in runtime.event_clocks:
        if not clock.active or clock.clock_type != "terminal_defeat":
            continue
        current = _clock_runtime_value(clock.id, game_state_data)
        if clock.max_value > 0 and current / clock.max_value >= 0.80:
            # Label cluster-specifico per l'escape
            return "survival" if cluster == "horror" else "escape"

    found = set(game_state_data.get("clues_found") or [])

    # ── Dungeon ────────────────────────────────────────────────────────────────
    if cluster == "dungeon":
        # Confrontazione: payload o chiave finale trovata
        payload = [c for c in runtime.clues if c.type in ("payload_object", "finale_key")]
        if payload and any(c.id in found for c in payload):
            return "confrontation"
        # Exploration altrimenti
        return "exploration"

    # ── Thriller / Survival ────────────────────────────────────────────────────
    if cluster == "thriller":
        # Alta pressione = priorità fuga anche senza clock al 80%
        threat = int(game_state_data.get("threat_level") or 0)
        threat_max = max(1, max((c.max_value for c in runtime.event_clocks), default=8))
        if threat / threat_max >= 0.60:
            return "escape"
        required = [c for c in runtime.clues if c.is_required]
        if required and sum(1 for c in required if c.id in found) / len(required) >= 0.70:
            return "objective_reached"
        return "evasion"

    # ── Horror ────────────────────────────────────────────────────────────────
    if cluster == "horror":
        required = [c for c in runtime.clues if c.is_required]
        pct = (sum(1 for c in required if c.id in found) / len(required)) if required else 0.0
        if pct >= 0.70:
            return "confrontation"
        if pct >= 0.35:
            return "dread"
        return "curiosity"

    # ── Heist ─────────────────────────────────────────────────────────────────
    if cluster == "heist":
        objectives = runtime.objective_stack or []
        done = sum(1 for o in objectives if getattr(o, "status", "") == "completed")
        total = len(objectives) or 1
        pct = done / total
        if pct >= 1.0:
            return "exfil"
        if pct >= 0.50:
            return "execution"
        required = [c for c in runtime.clues if c.is_required]
        if required and sum(1 for c in required if c.id in found) / len(required) >= 0.50:
            return "infiltration"
        return "planning"

    # ── Faction ───────────────────────────────────────────────────────────────
    if cluster == "faction":
        required = [c for c in runtime.clues if c.is_required]
        pct = (sum(1 for c in required if c.id in found) / len(required)) if required else 0.0
        if pct >= 0.80:
            return "resolution"
        if pct >= 0.50:
            return "confrontation"
        if pct >= 0.20:
            return "negotiation"
        return "assessment"

    # ── Clue-based (default: investigation_graph e affini) ────────────────────
    ready_count = 0
    for rev in runtime.revelations:
        if rev.status == "revealed":
            ready_count += 1
            continue
        if not rev.required_clues:
            continue
        minimum = min(2, max(1, len(rev.required_clues)))
        if len([cid for cid in rev.required_clues if cid in found]) >= minimum:
            ready_count += 1
    total_revs = len(runtime.revelations)
    if total_revs > 0 and ready_count >= max(1, total_revs - 1):
        return "extraction"

    payload_clues = [c for c in runtime.clues if c.type in ("payload_object", "finale_key", "evidence")]
    if payload_clues and sum(1 for c in payload_clues if c.id in found) >= max(1, len(payload_clues) // 2):
        return "extraction"

    required_clues = [c for c in runtime.clues if c.is_required]
    if required_clues:
        pct = sum(1 for c in required_clues if c.id in found) / len(required_clues)
        if pct >= 0.70:
            return "extraction"

    return "investigation"


def _fail_tier(prerolled: dict, game_state_data: dict, runtime: AdventureRuntime) -> str:
    """
    Classifica il fallimento con logica dipendente dal cluster del runtime_profile.

    - "none"     : successo, nessun costo
    - "soft"     : piccolo costo narrativo (solo in cluster permissivi)
    - "pressure" : clock avanza o situazione peggiora
    - "hard"     : conseguenza immediata — NPC compromesso, danno, allarme
    """
    success = bool(prerolled.get("success", True))
    if success:
        return "none"

    critical = bool(prerolled.get("critical", False))
    margin = int(prerolled.get("margin", 0))
    threat_level = int(game_state_data.get("threat_level") or 0)
    threat_max = max(1, max((c.max_value for c in runtime.event_clocks), default=8))
    threat_pct = threat_level / threat_max
    cluster = _profile_cluster(runtime)

    # Dungeon e Horror: nessun fallimento "soft" — ogni errore ha peso
    if cluster in ("dungeon", "horror"):
        if critical or margin <= -3:
            return "hard"
        return "pressure"

    # Thriller / Survival: alta pressione scala più velocemente
    if cluster == "thriller":
        if critical or margin <= -4 or threat_pct >= 0.50:
            return "hard"
        return "pressure"  # No "soft" — ogni passo falso è pericoloso

    # Heist: soft = sospetto alzato, pressure = allarme parziale, hard = lockdown
    if cluster == "heist":
        if critical or margin <= -5:
            return "hard"
        if threat_pct >= 0.40 or margin <= -2:
            return "pressure"
        return "soft"

    # Faction: soft = reputazione scalfita, pressure = fazione ostile, hard = conflitto
    if cluster == "faction":
        if critical or margin <= -5:
            return "hard"
        if margin <= -2:
            return "pressure"
        return "soft"

    # Clue-based (default)
    if critical or margin <= -5:
        return "hard"
    if threat_pct >= 0.60 or margin <= -3:
        return "pressure"
    return "soft"


def _clock_urgency_warnings(runtime: AdventureRuntime, game_state_data: dict) -> list[dict]:
    """
    Genera avvisi di urgenza diegetici quando clock terminali superano soglie critiche.
    Soglie: 50% (media), 70% (alta), 90% (critica).
    Restituisce solo il warning più grave per clock, solo se il clock è scoperto o quasi completo.
    """
    warnings = []
    for clock in runtime.event_clocks:
        if not clock.active or clock.clock_type != "terminal_defeat":
            continue
        current = _clock_runtime_value(clock.id, game_state_data)
        if clock.max_value <= 0:
            continue
        pct = current / clock.max_value
        if pct < 0.50:
            continue  # Ancora tranquillo, nessun avviso

        if pct >= 0.90:
            urgency = "CRITICA"
            message = (
                f"Non hai più margine di errore — devi agire subito o perdere tutto. "
                f"Conseguenza imminente: {clock.consequence or clock.on_complete}"
            )
            switch_mode = "escape"
        elif pct >= 0.70:
            urgency = "ALTA"
            message = (
                f"Non hai più tempo per approfondire l'indagine — ora devi proteggere le prove e muoverti. "
                f"Pericolo: {clock.label}"
            )
            switch_mode = "extraction"
        else:
            urgency = "MEDIA"
            message = (
                f"La pressione cresce — ogni turno di indagine aggiuntivo ha un costo reale. "
                f"Clock: {clock.label}"
            )
            switch_mode = None

        warnings.append({
            "clock_id": clock.id,
            "clock_label": clock.label,
            "urgency": urgency,
            "pct": round(pct, 2),
            "current": current,
            "max_value": clock.max_value,
            "message": message,
            "switch_mode": switch_mode,
            "discovered": _clock_is_discovered(clock, game_state_data),
        })
    # Ordina per gravità decrescente
    warnings.sort(key=lambda w: -w["pct"])
    return warnings


def _next_best_actions(
    runtime: AdventureRuntime,
    game_state_data: dict,
    ready_threads: list[str],
    found_after: set[str],
    phase: str,
) -> list[str]:
    """
    Genera azioni suggerite basate sulla fase narrativa e sulle rivelazioni pronte.
    Restituisce tag canonici che il director può usare per orientare l'AI verso scelte concrete.
    """
    actions: list[str] = []
    npc_rt = game_state_data.get("npc_runtime") or {}

    # Azione prioritaria: chiudere rivelazioni pronte
    if ready_threads:
        actions.append("dedurre_e_confermare_rivelazione")

    cluster = _profile_cluster(runtime)

    _PHASE_ACTIONS: dict[str, list[str]] = {
        # clue
        "investigation": ["seguire_la_pista_piu_calda", "interrogare_testimone_disponibile", "esaminare_prova_fisica"],
        "extraction":    ["proteggere_o_copiare_le_prove", "raggiungere_luogo_sicuro", "contattare_autorita_di_fiducia", "separare_il_testimone_dalle_prove"],
        "delivery":      ["consegnare_prove_all_autorita", "proteggere_testimonianza", "smascherare_antagonista_pubblicamente"],
        "escape":        ["evacuare_immediatamente", "consegnare_le_prove_prima_di_fuggire", "evitare_pattuglie_antagonista", "trovare_via_di_fuga"],
        # dungeon
        "exploration":   ["avanzare_con_cautela", "cercare_trappole", "forzare_porta", "mappare_il_corridoio"],
        "confrontation": ["affrontare_il_boss", "cercare_debolezza", "proteggere_il_gruppo", "usare_l_ambiente"],
        # thriller
        "evasion":          ["nascondersi", "cambiare_percorso", "creare_diversione", "segnalare_posizione_sicura"],
        "objective_reached":["recuperare_l_obiettivo", "proteggere_il_corridoio_di_fuga", "eliminare_ultima_guardia"],
        # horror
        "curiosity":     ["investigare_con_cautela", "documentare_l_anomalia", "intervistare_i_sopravvissuti"],
        "dread":         ["non_separarsi_dal_gruppo", "trovare_riparo_sicuro", "cercare_debolezza_dell_entita"],
        "confrontation_horror": ["affrontare_l_entita", "fuggire_ora", "proteggere_l_alleato_vulnerabile"],
        "survival":      ["fuggire_a_tutti_i_costi", "sacrificare_un_esca", "trovare_l_uscita"],
        # heist
        "planning":      ["raccogliere_intel_sul_bersaglio", "individuare_vulnerabilita", "reclutare_specialista"],
        "infiltration":  ["eludere_la_guardia", "disattivare_sicurezza", "avanzare_non_rilevati"],
        "execution":     ["recuperare_il_bersaglio", "mantenere_copertura", "gestire_imprevisto"],
        "exfil":         ["raggiungere_il_punto_di_estrazione", "eliminare_tracce", "aborta_se_compromessi"],
        # faction
        "assessment":    ["raccogliere_intel_sulle_fazioni", "identificare_interlocutore_chiave"],
        "negotiation":   ["proporre_accordo", "costruire_alleanza", "neutralizzare_estremisti"],
        "resolution":    ["smascherare_il_tradimento", "consolidare_l_alleanza", "pacificare_le_parti"],
    }

    phase_key = phase
    if cluster == "horror" and phase == "confrontation":
        phase_key = "confrontation_horror"

    actions += _PHASE_ACTIONS.get(phase_key, _PHASE_ACTIONS["investigation"])

    # Payload object trovati → suggerisci consegna
    payload_found = [
        c for c in runtime.clues
        if c.type in ("payload_object", "finale_key") and c.id in found_after
    ]
    if payload_found:
        for a in ("consegnare_prove_all_autorita", "proteggere_o_copiare_le_prove"):
            if a not in actions:
                actions.insert(1, a)

    # Testimoni attivi → suggerisci protezione
    for actor in runtime.actors:
        if actor.role.lower() in _WITNESS_ROLES:
            eff = actor.status
            rt_e = npc_rt.get(actor.id) or {}
            if rt_e.get("status"):
                eff = rt_e["status"]
            if eff in ("introduced", "active"):
                tag = f"proteggere_testimone:{actor.id}"
                if tag not in actions:
                    actions.insert(0, tag)
                break

    return actions[:7]


def _witness_state_check(runtime: AdventureRuntime, game_state_data: dict) -> list[dict]:
    """
    Controlla lo stato dei NPC testimone rispetto alla pressione attuale.
    Restituisce aggiornamenti di stato che il director deve narrare.

    N5: aggiunge degradazione per witness ignorati (fearful_turns_ignored >= 2)
    e popola available_witness_actions per ogni testimone attivo.
    """
    threat_level = int(game_state_data.get("threat_level") or 0)
    threat_max = max(1, max((c.max_value for c in runtime.event_clocks), default=8))
    threat_pct = threat_level / threat_max
    npc_rt = game_state_data.get("npc_runtime") or {}

    updates = []
    for actor in runtime.actors:
        if actor.role.lower() not in _WITNESS_ROLES:
            continue
        eff = actor.status
        rt_e = npc_rt.get(actor.id) or {}
        if rt_e.get("status"):
            eff = rt_e["status"]

        if eff == "unintroduced" or eff in _TERMINAL_NPC_STATES:
            continue

        current_ws = rt_e.get("witness_state") or "available"
        fearful_turns = int(rt_e.get("fearful_turns_ignored") or 0)

        new_ws = current_ws
        note = ""

        # Degrado da pressione minaccia
        if threat_pct >= 0.85 and current_ws in ("available", "fearful"):
            new_ws = "panicked"
            note = f"{actor.name} sta valutando di fuggire o ritirare la collaborazione — va calmato o messo in sicurezza subito."
        elif threat_pct >= 0.65 and current_ws == "available":
            new_ws = "fearful"
            note = f"{actor.name} è visibilmente nervoso e difficile da raggiungere — la pressione lo sta logorando."

        # N5: degrado da abbandono — 2+ turni senza intervento su witness fearful
        if current_ws == "fearful" and fearful_turns >= 2 and new_ws == "fearful":
            new_ws = "panicked"
            note = f"{actor.name} è stato ignorato troppo a lungo mentre era spaventato: ora è in preda al panico e potrebbe fuggire al prossimo turno."

        # N5: azioni disponibili per il giocatore
        available_actions: list[dict] = []
        if current_ws in ("fearful", "panicked"):
            available_actions.append({
                "action": "reassure",
                "label": f"Rassicurare {actor.name}",
                "skill_hint": "diplomazia o empatia",
                "effect": "se successo pieno: witness torna a 'available' e sblocca informazioni extra",
            })
            available_actions.append({
                "action": "protect",
                "label": f"Offrire protezione a {actor.name}",
                "skill_hint": "leadership o persuasione",
                "effect": "stabilizza lo stato (non peggiora ulteriormente), sblocca possible_action aggiuntiva",
            })

        state_changed = new_ws != current_ws
        # Include entry when state changes or when already-fearful witness has been ignored (≥1 turn)
        is_ignored_fearful = current_ws == "fearful" and fearful_turns >= 1
        if state_changed or is_ignored_fearful:
            entry: dict = {
                "npc_id": actor.id,
                "npc_name": actor.name,
                "previous_witness_state": current_ws,
                "witness_state": new_ws,
                "note": note,
                "available_witness_actions": available_actions,
                "fearful_turns_ignored": fearful_turns,
            }
            updates.append(entry)

    return updates


def _compute_clock_tick(prerolled: dict) -> int:
    """Quanti tick avanza il threat_level questo turno.
    Solo i fallimenti fanno avanzare la pressione: il successo parziale è
    'ce l'hai fatta con complicazioni', non un fallimento."""
    success = bool(prerolled.get("success", True))
    margin = int(prerolled.get("margin", 0))
    critical = bool(prerolled.get("critical", False))

    if not success:
        return 2 if (critical or margin <= -5) else 1
    return 0


def _select_clue(
    runtime: AdventureRuntime,
    game_state_data: dict,
    player_action: str,
    skill: str,
    success: bool,
) -> tuple[str | None, str]:
    """Seleziona deterministicamente UN indizio su cui agire. Ritorna (clue_id | None, motivo)."""
    found = set(game_state_data.get("clues_found") or [])
    progress = game_state_data.get("clue_progress") or {}

    current_name = ""
    map_state = game_state_data.get("map_state") or {}
    if map_state:
        node = (map_state.get("nodes") or {}).get(map_state.get("current_node_id")) or {}
        current_name = str(node.get("name") or "")

    hidden = [c for c in runtime.clues if c.id not in found and c.state != "discovered"]
    if not hidden:
        return None, "tutti gli indizi trovati"

    # Filtra per location corrente se possibile
    local = []
    if current_name:
        local = [
            c for c in hidden
            if c.source_location and (
                c.source_location.lower() in current_name.lower()
                or current_name.lower() in c.source_location.lower()
            )
        ]

    # Pool: locale se disponibile, altrimenti globale
    pool = local if local else (hidden if _action_is_investigative(player_action, skill) else [])
    if not pool:
        return None, "azione non investigativa fuori location, nessun indizio forzato"

    # Ordine: prima i più vicini al completamento (ticks alti), poi i required
    def _sort_key(c):
        ticks = int(((progress.get(c.id) or {}).get("ticks") or c.progress_ticks or 0))
        return (-ticks, not c.is_required)

    clue = sorted(pool, key=_sort_key)[0]
    ticks = int(((progress.get(clue.id) or {}).get("ticks") or clue.progress_ticks or 0))

    if success and ticks >= 1:
        return clue.id, f"completamento indizio canonico [{clue.id}]"
    return clue.id, f"avanzamento indizio canonico [{clue.id}]"


def _select_red_herring(
    runtime: AdventureRuntime,
    game_state_data: dict,
) -> dict | None:
    """N7: seleziona un red herring clue da presentare se le condizioni lo permettono.

    Condizioni:
    - Almeno una revelation ha red_herring_clues definiti
    - Il giocatore è nella stessa location di un red herring clue
    - La pressione NPC attuale è bassa (threat < 50%)
    - Il red herring non è già stato mostrato (non in clues_found né in clue_progress)

    Restituisce il RuntimeClue del red herring selezionato, o None.
    """
    threat_level = int(game_state_data.get("threat_level") or 0)
    threat_max = max(1, max((c.max_value for c in runtime.event_clocks), default=8))
    if threat_level / threat_max >= 0.5:
        return None  # pressione troppo alta, non distrarre con false piste

    found = set(game_state_data.get("clues_found") or [])
    progress_keys = set((game_state_data.get("clue_progress") or {}).keys())
    shown = found | progress_keys

    # Raccogli tutti i red herring clue IDs da tutte le revelations
    rh_ids: set[str] = set()
    for rev in runtime.revelations:
        for rhid in (rev.red_herring_clues or []):
            if rhid not in shown:
                rh_ids.add(rhid)

    if not rh_ids:
        return None

    # Filtra per location corrente
    current_name = ""
    map_state = game_state_data.get("map_state") or {}
    if map_state:
        node = (map_state.get("nodes") or {}).get(map_state.get("current_node_id")) or {}
        current_name = str(node.get("name") or "")

    candidates = [
        c for c in runtime.clues
        if c.id in rh_ids
        and (
            not current_name
            or not c.source_location
            or c.source_location.lower() in current_name.lower()
            or current_name.lower() in c.source_location.lower()
        )
    ]

    return candidates[0] if candidates else None


def _npcs_to_introduce(runtime: AdventureRuntime, game_state_data: dict) -> list[str]:
    """
    Determina quali NPC devono apparire questo turno per pressione narrativa.
    Rispetta il NPC state lock: non introduce attori in stati terminali (dead, captured, missing, resolved).
    """
    threat_level = int(game_state_data.get("threat_level") or 0)
    threat_max = max(1, max((c.max_value for c in runtime.event_clocks), default=8))
    threat_pct = threat_level / threat_max
    npc_rt = game_state_data.get("npc_runtime") or {}

    candidates = []
    for actor in runtime.actors:
        # Stato effettivo: prima il runtime override, poi lo stato canonico
        eff_status = actor.status
        rt_entry = npc_rt.get(actor.id) or {}
        if rt_entry.get("status"):
            eff_status = rt_entry["status"]

        # State lock: mai introdurre NPC in stato terminale
        if eff_status in _TERMINAL_NPC_STATES:
            continue
        if eff_status != "unintroduced":
            continue

        p = actor.agenda_pressure
        # Soglie: più alta la pressione dell'NPC, prima entra in scena
        if p >= 3 and threat_pct >= 0.20:
            candidates.append((0, actor.id))
        elif p >= 2 and threat_pct >= 0.35:
            candidates.append((1, actor.id))
        elif p >= 1 and threat_pct >= 0.55:
            candidates.append((2, actor.id))
        elif threat_pct >= 0.75:
            candidates.append((3, actor.id))

    candidates.sort()
    # Massimo 1 NPC introdotto per turno
    return [npc_id for _, npc_id in candidates[:1]]


def _clock_runtime_value(clock_id: str, game_state_data: dict) -> int:
    """Valore corrente del clock dal runtime (contatore proprio, indipendente da threat_level)."""
    rt = game_state_data.get("clock_runtime") or {}
    return int((rt.get(clock_id) or {}).get("value") or 0)


def _clock_is_discovered(clock: AdventureRuntime, game_state_data: dict) -> bool:
    """True se i giocatori sanno già di questo clock."""
    if getattr(clock, "discovered", False):
        return True
    rt = game_state_data.get("clock_runtime") or {}
    return bool((rt.get(clock.id) or {}).get("discovered", False))


def _per_clock_ticks(runtime: AdventureRuntime, prerolled: dict) -> dict[str, int]:
    """Calcola quanti tick avanza ogni clock singolo in base all'esito del tiro."""
    success = bool(prerolled.get("success", True))
    critical = bool(prerolled.get("critical", False))
    margin = int(prerolled.get("margin", 0))
    outcome = str(prerolled.get("outcome") or "").lower()
    is_partial = "parziale" in outcome

    result: dict[str, int] = {}
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        if not success:
            base = getattr(clock, "ticks_per_failure", 1)
            result[clock.id] = base + 1 if (critical or margin <= -5) else base
        elif is_partial:
            result[clock.id] = getattr(clock, "ticks_per_partial", 1)
        else:
            result[clock.id] = getattr(clock, "ticks_per_success", 0)
    return result


def _clock_is_resolved(clock, game_state_data: dict) -> bool:
    """True se i giocatori hanno già risolto questo clock trovando tutti gli indizi di risoluzione."""
    if getattr(clock, "resolved", False):
        return True
    rt = game_state_data.get("clock_runtime") or {}
    return bool((rt.get(clock.id) or {}).get("resolved", False))


def _check_clock_triggers(runtime: AdventureRuntime, game_state_data: dict, per_clock_ticks: dict[str, int]) -> list[dict]:
    """Calcola quali clock raggiungono il massimo dopo i tick di questo turno (contatori propri)."""
    triggers = []
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        if _clock_is_resolved(clock, game_state_data):
            continue
        current = _clock_runtime_value(clock.id, game_state_data)
        tick = per_clock_ticks.get(clock.id, 0)
        new_value = current + tick
        if new_value >= clock.max_value > current:
            triggers.append({
                "clock_id": clock.id,
                "label": clock.label,
                "consequence": clock.consequence,
                "on_complete": clock.on_complete,
                "discovered": _clock_is_discovered(clock, game_state_data),
                "clock_type": getattr(clock, "clock_type", "narrative"),
            })
    return triggers


def _clock_step_reactions(runtime: AdventureRuntime, game_state_data: dict, per_clock_ticks: dict[str, int]) -> list[dict]:
    reactions = []
    for clock in runtime.event_clocks:
        if not clock.active or not clock.steps:
            continue
        current = _clock_runtime_value(clock.id, game_state_data)
        tick = per_clock_ticks.get(clock.id, 0)
        if tick <= 0:
            continue
        for value in range(current + 1, min(current + tick, clock.max_value) + 1):
            step = next((s for s in clock.steps if int(s.get("step") or 0) == value), None)
            if not step:
                continue
            reactions.append({
                "clock_id": clock.id,
                "clock_label": clock.label,
                "step": value,
                "discovered": _clock_is_discovered(clock, game_state_data),
                "world_state_change": step.get("world_state_change") or step.get("event") or "",
                "scene_prompt": step.get("scene_prompt") or "",
                "possible_player_response": step.get("possible_player_response") or "",
            })
    return reactions


def _auto_discover_clocks(runtime: AdventureRuntime, game_state_data: dict, just_found_clues: list[str]) -> list[dict]:
    """Se un indizio appena trovato è la chiave di scoperta di un clock, lo svela ai giocatori."""
    just_found = set(just_found_clues)
    discoveries = []
    for clock in runtime.event_clocks:
        if not clock.active or _clock_is_discovered(clock, game_state_data):
            continue
        disc_clue = getattr(clock, "discovery_clue_id", "") or ""
        if disc_clue and disc_clue in just_found:
            discoveries.append({
                "clock_id": clock.id,
                "label": clock.label,
                "current_value": _clock_runtime_value(clock.id, game_state_data),
                "max_value": clock.max_value,
                "consequence": clock.consequence,
                "discovery_clue_id": disc_clue,
            })
    return discoveries


def simulate_world_state(
    runtime: AdventureRuntime,
    *,
    player_action: str,
    prerolled: dict | None,
    game_state_data: dict,
) -> dict:
    """Decide conseguenze minime prima della narrazione AI, usando solo elementi canonici."""
    prerolled = prerolled or {}
    success = bool(prerolled.get("success", True))
    outcome = str(prerolled.get("outcome") or "").lower()
    skill = str(prerolled.get("skill") or "")

    # ── Fase narrativa corrente ───────────────────────────────────────────────
    phase = _compute_narrative_phase(runtime, game_state_data)

    # ── Tier del fallimento (fail-forward graduato) ───────────────────────────
    fail_tier_value = _fail_tier(prerolled, game_state_data, runtime)

    # Per compatibilità: _compute_clock_tick dà il tick "generico" usato da threat_level.
    # Con fail-forward graduato: solo i fallimenti hard/pressure avanzano il clock.
    # Un soft fail non aumenta la pressione globale.
    raw_clock_tick = _compute_clock_tick(prerolled)
    clock_tick = raw_clock_tick if fail_tier_value in ("hard", "pressure", "none") else 0

    # Clock indipendenti: ogni clock ha il proprio contatore
    per_clock = _per_clock_ticks(runtime, prerolled)

    # In fase extraction/escape non selezionare nuovi indizi da raccogliere
    # (i giocatori hanno già le prove, ora devono agire)
    if phase in ("extraction", "escape", "delivery"):
        clue_id, clue_reason = None, f"fase {phase}: non si raccolgono nuovi indizi"
    else:
        clue_id, clue_reason = _select_clue(runtime, game_state_data, player_action, skill, success)

    npcs_to_introduce = _npcs_to_introduce(runtime, game_state_data)
    clock_triggers = _check_clock_triggers(runtime, game_state_data, per_clock)
    clock_step_reactions = _clock_step_reactions(runtime, game_state_data, per_clock)

    # Urgency warnings per clock terminali
    urgency_warnings = _clock_urgency_warnings(runtime, game_state_data)

    progress = game_state_data.get("clue_progress") or {}
    found = set(game_state_data.get("clues_found") or [])

    clue_progress_update: list[dict] = []
    clues_found_update: list[str] = []

    if clue_id:
        ticks = int(((progress.get(clue_id) or {}).get("ticks") or 0))
        if success and ticks >= 1:
            clues_found_update.append(clue_id)
        else:
            label = next((c.label for c in runtime.clues if c.id == clue_id), clue_id)
            clue_progress_update.append({
                "clue_id": clue_id,
                "note": f"Avanzamento verso: {label}",
                "ticks": 1,
            })

    found_after = found | set(clues_found_update)
    # Scoperta automatica di clock: se un indizio trovato ora svela un clock nascosto
    newly_discovered_clocks = _auto_discover_clocks(runtime, game_state_data, clues_found_update)
    # Auto-risoluzione: se tutti gli indizi di risoluzione di un clock sono stati trovati, il clock si ferma
    auto_resolved_clocks: list[dict] = []
    for clock in runtime.event_clocks:
        if not clock.active or _clock_is_resolved(clock, game_state_data):
            continue
        res_clues = getattr(clock, "resolution_clues", []) or []
        if res_clues and all(cid in found_after for cid in res_clues):
            auto_resolved_clocks.append({
                "clock_id": clock.id,
                "label": clock.label,
                "clock_type": getattr(clock, "clock_type", "narrative"),
                "resolution_condition": getattr(clock, "resolution_condition", "") or "",
            })

    ready = []
    for rev in runtime.revelations:
        if rev.status == "revealed" or not rev.required_clues:
            continue
        minimum = min(2, max(1, len(rev.required_clues)))
        if len([cid for cid in rev.required_clues if cid in found_after]) >= minimum:
            ready.append(rev.thread_id or rev.id)

    # Next best actions basate su fase e rivelazioni
    next_best = _next_best_actions(runtime, game_state_data, ready, found_after, phase)

    # N7: red herring candidato (solo se pressione bassa e location match)
    red_herring_candidate: dict | None = None
    if not success and phase == "investigation":
        rh = _select_red_herring(runtime, game_state_data)
        if rh:
            red_herring_candidate = {
                "id": rh.id,
                "label": rh.label,
                "type": rh.type,
                "source_location": rh.source_location,
                "immediate_information": rh.immediate_information or rh.label,
            }

    # Witness state check
    witness_updates = _witness_state_check(runtime, game_state_data)

    events: list[str] = []
    if clock_tick > 0:
        events.append(f"Clock avanza di {clock_tick} tick questo turno.")
    if not success:
        # Fail-forward graduato: messaggio specifico per tier
        if fail_tier_value == "soft":
            events.append("SOFT FAIL: piccolo costo narrativo — indizio parziale o complicazione minore. NON avanzare il clock principale.")
        elif fail_tier_value == "pressure":
            events.append("PRESSURE FAIL: il clock avanza, la situazione peggiora ma la storia non si blocca.")
        else:
            events.append("HARD FAIL: conseguenza immediata e concreta — NPC compromesso, prova a rischio o posizione esposta.")
    elif "parziale" in outcome:
        events.append("Successo parziale: progresso incompleto con costo latente.")
    if clue_id:
        if clues_found_update:
            events.append(f"Prova canonica [{clue_id}] completata: narra come viene ottenuta.")
        else:
            events.append(f"Indizio [{clue_id}] avanza di 1 tick: progresso parziale, non ancora prova.")
    if npcs_to_introduce:
        events.append(f"NPC da introdurre in questa scena: {', '.join(npcs_to_introduce)}.")
    if witness_updates:
        for wu in witness_updates:
            events.append(f"TESTIMONE [{wu['npc_name']}] → {wu['witness_state'].upper()}: {wu['note']}")
    for uw in urgency_warnings:
        if uw["urgency"] in ("ALTA", "CRITICA"):
            events.append(f"URGENZA {uw['urgency']} [{uw['clock_label']}]: {uw['message']}")
    for r in auto_resolved_clocks:
        ctype = r.get("clock_type", "narrative")
        cond = r.get("resolution_condition") or "trovando tutti gli indizi necessari"
        if ctype == "terminal_defeat":
            events.append(f"CLOCK SVENTATO [{r['label']}] (terminal_defeat): i giocatori hanno trovato tutti gli indizi e fermato il conto alla rovescia in tempo! Narra la risoluzione drammatica come salvezza all'ultimo momento.")
        elif ctype == "terminal_victory":
            events.append(f"CLOCK COMPLETATO CON VITTORIA [{r['label']}]: i giocatori hanno raggiunto la condizione di vittoria ({cond}). L'avventura si conclude con il loro trionfo.")
        else:
            events.append(f"CLOCK RISOLTO [{r['label']}]: i giocatori hanno fermato questo conto alla rovescia ({cond}). Il pericolo immediato passa.")
    for disc in newly_discovered_clocks:
        remaining = disc["max_value"] - disc["current_value"]
        events.append(
            f"CLOCK SVELATO [{disc['label']}]: i giocatori scoprono che esiste questo conto alla rovescia. "
            f"Valore attuale {disc['current_value']}/{disc['max_value']} — restano {remaining} segmenti prima che: {disc['consequence']}. "
            "Narra la rivelazione in modo drammatico."
        )
    for t in clock_triggers:
        ctype = t.get("clock_type", "narrative")
        if ctype == "terminal_defeat":
            events.append(f"CLOCK TERMINALE [{t['label']}] — SCONFITTA: {t['consequence'] or t['on_complete']}. Questo è l'ultimo turno dell'avventura. story_over=true, victory=false.")
        elif ctype == "terminal_victory":
            events.append(f"CLOCK TERMINALE [{t['label']}] — VITTORIA: {t['consequence'] or t['on_complete']}. Questo è l'ultimo turno dell'avventura. story_over=true, victory=true.")
        elif ctype == "escalation":
            events.append(f"CLOCK ESCALATION [{t['label']}]: {t['consequence'] or t['on_complete']}. La minaccia scala massivamente — threat_increase +3.")
        elif t.get("discovered"):
            events.append(f"CLOCK COMPLETO [{t['label']}] (noto ai giocatori): {t['consequence'] or t['on_complete']}.")
        else:
            events.append(f"CLOCK COMPLETO [{t['label']}] (silente — i giocatori non sapevano): {t['consequence'] or t['on_complete']}. Narra la conseguenza come evento improvviso, non come 'countdown scaduto'.")
    for reaction in clock_step_reactions:
        if reaction.get("discovered"):
            events.append(f"CLOCK STEP [{reaction['clock_label']} {reaction['step']}]: {reaction['world_state_change']}.")
        else:
            # Clock nascosto: dai solo il segnale ambiguo dal campo discovery_hint o scene_prompt
            hint = reaction.get("scene_prompt") or reaction.get("world_state_change") or ""
            if hint:
                events.append(f"SEGNALE AMBIGUO (clock nascosto {reaction['clock_label']}): {hint} — narra in modo misterioso, senza rivelare il clock.")
    if ready:
        events.append(f"Piste pronte alla deduzione: {', '.join(ready)}.")
    actor_agendas = [
        {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "goal": a.goal,
            "pressure_response": a.pressure_response,
        }
        for a in runtime.actors
    ]
    current_location = {}
    map_state = game_state_data.get("map_state") or {}
    if map_state:
        current_location = (map_state.get("nodes") or {}).get(map_state.get("current_node_id")) or {}

    # G6: compute sanity damage (horror only)
    sanity_updates = _compute_sanity_damage(runtime, game_state_data, prerolled, clock_step_reactions, npcs_to_introduce)
    for su in sanity_updates:
        delta = su["delta"]
        if delta < 0:
            events.append(f"SANITÀ {delta}: {'l' if delta <= -2 else 'un'} {'trauma grave' if delta <= -2 else 'trauma lieve'} scuote i personaggi — narra la reazione psicologica.")
        elif delta > 0:
            events.append("SANITÀ +1: il gruppo supera la paura — narra il momento di sollievo o determinazione.")

    # G2: compute faction reputation deltas and build enriched rep dict for world_reaction_engine
    faction_rep_deltas = _compute_faction_rep_deltas(runtime, game_state_data, prerolled, player_action)
    faction_rep_base: dict[str, int] = {}
    for k, v in (game_state_data.get("faction_reputation") or {}).items():
        try:
            faction_rep_base[k] = int(v)
        except (TypeError, ValueError):
            pass
    # Apply deltas provisionally for reaction engine (clamped to [-5, 5])
    faction_rep_current = {
        fid: max(-5, min(5, faction_rep_base.get(fid, 0) + delta))
        for fid, delta in faction_rep_deltas.items()
    }
    for fid, score in faction_rep_base.items():
        if fid not in faction_rep_current:
            faction_rep_current[fid] = score
    # Enrich with trusted_npc from actor roster (first ally-role actor per faction)
    ally_npc_name = next(
        (a.name for a in runtime.actors if a.role in ("ally", "contact", "allied", "alleato")),
        None
    )
    faction_rep_enriched: dict[str, dict] = {
        fid: {"score": score, "trusted_npc": ally_npc_name}
        for fid, score in faction_rep_current.items()
    }
    # G2 proactive: se reputazione > 3 con una fazione, NPC offre indizio proattivo
    for fid, score in faction_rep_current.items():
        if score > 3:
            faction_name = next((f.name for f in runtime.factions if f.id == fid), fid)
            events.append(
                f"REP ALTA [{faction_name}]: reputazione {score}/5 — un contatto della fazione si offre proattivamente di condividere un indizio utile."
            )
            break  # max 1 proactive hint per turn

    world_reactions = generate_world_reactions(
        player_action_result=prerolled,
        clock_state={
            "clock_step_reactions": clock_step_reactions,
            "threat_level": int(game_state_data.get("threat_level") or 0) + clock_tick,
        },
        npc_agendas=actor_agendas,
        current_location=current_location,
        faction_reputation=faction_rep_enriched,
    )
    for reaction in world_reactions[:2]:
        events.append(f"REAZIONE MONDO [{reaction['type']}]: {reaction['world_state_change']}.")

    npc_updates = [
        {
            "id": npc_id,
            "status": "introduced",
            "arc_status": "introduced",
            "note": "Il runtime lo introduce per pressione narrativa coerente con la sua agenda.",
        }
        for npc_id in npcs_to_introduce
    ]
    for reaction in world_reactions:
        npc_id = reaction.get("npc_id")
        if reaction.get("type") == "npc_pressure_response" and npc_id:
            npc_updates.append({
                "id": npc_id,
                "status": "active",
                "arc_status": "active",
                "note": reaction.get("world_state_change", ""),
            })
            break

    # Costruisce clock_updates: avanza il valore di ogni clock nel runtime
    auto_resolved_ids = {r["clock_id"] for r in auto_resolved_clocks}
    clock_updates = []
    for clock in runtime.event_clocks:
        if not clock.active:
            continue
        tick = per_clock.get(clock.id, 0)
        current = _clock_runtime_value(clock.id, game_state_data)
        entry: dict = {"id": clock.id, "delta": tick}
        if any(d["clock_id"] == clock.id for d in newly_discovered_clocks):
            entry["discovered"] = True
        if clock.id in auto_resolved_ids:
            entry["resolved"] = True
        clock_updates.append(entry)

    def _clock_display_value(c) -> int:
        return _clock_runtime_value(c.id, game_state_data)

    return {
        "proposed_updates": {
            "clue_progress": clue_progress_update,
            "clues_found": clues_found_update,
            "npc_updates": npc_updates[:3],
            "new_threads": [],
            "closed_threads": [],
            "threat_increase": clock_tick,
            "clock_updates": clock_updates,
            "location_access": [],
            "objective_progress": 0,
            "faction_rep_updates": faction_rep_deltas,  # G2
            "san_updates": sanity_updates,               # G6
        },
        "events": events,
        "ready_threads": ready,
        "clock_summary": "; ".join(
            f"{c.label} {_clock_display_value(c)}/{c.max_value}"
            + (" [scoperto]" if _clock_is_discovered(c, game_state_data) else " [nascosto]")
            for c in runtime.event_clocks
        ),
        # Campi strutturati per il director
        "clock_tick": clock_tick,
        "per_clock_ticks": per_clock,
        "selected_clue_id": clue_id,
        "selected_clue_reason": clue_reason,
        "npcs_to_introduce": npcs_to_introduce,
        "clock_triggers": clock_triggers,
        "clock_step_reactions": clock_step_reactions,
        "world_reactions": world_reactions,
        "newly_discovered_clocks": newly_discovered_clocks,
        "auto_resolved_clocks": auto_resolved_clocks,
        # Nuovi campi: fase narrativa, fail tier, urgenza, azioni suggerite, testimoni
        "narrative_phase": phase,
        "fail_tier": fail_tier_value,
        "urgency_warnings": urgency_warnings,
        "next_best_actions": next_best,
        "witness_updates": witness_updates,
        # N7: red herring candidato (solo in investigation con pressione bassa)
        "red_herring_candidate": red_herring_candidate,
        # N4: campi per pacing rivelazioni
        "canonical_log": game_state_data.get("canonical_log") or [],
        "current_turn": int(game_state_data.get("turn") or 0),
    }
