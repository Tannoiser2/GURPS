from __future__ import annotations


def generate_world_reactions(
    *,
    player_action_result: dict | None = None,
    clock_state: dict | None = None,
    npc_agendas: list[dict] | None = None,
    current_location: dict | None = None,
    faction_reputation: dict | None = None,
    critical_clue_proximity: dict | None = None,
    triggered_scene_changes: list[dict] | None = None,
) -> list[dict]:
    """Produce reazioni concrete del mondo senza inventare nuova trama.

    Le reazioni sono piccoli cambi di stato utilizzabili dal renderer AI:
    allarmi, blocchi, movimenti di PNG, testimoni che si nascondono, prove a rischio.

    R6: in aggiunta alle reazioni difensive, ora il mondo reagisce anche
    proattivamente ai successi del giocatore tramite ally_revealed
    (fazione amica) ed evidence_threatened (antagonista contromisure) e
    scene_change (location resa inaccessibile da eventi precedenti).
    """
    result = player_action_result or {}
    clock_state = clock_state or {}
    current_location = current_location or {}
    npc_agendas = npc_agendas or []
    faction_reputation = faction_reputation or {}
    critical_clue_proximity = critical_clue_proximity or {}
    triggered_scene_changes = triggered_scene_changes or []
    success = bool(result.get("success", True))
    margin = int(result.get("margin") or 0)
    reactions: list[dict] = []

    if not success:
        reactions.append({
            "type": "pressure_increase",
            "world_state_change": "la pressione locale aumenta e qualcuno nota l'azione della squadra",
            "scene_prompt": "Mostra un segnale concreto: allarme, porta che scatta, radio o passo nel corridoio.",
            "possible_player_response": "nascondersi, spiegarsi, cambiare percorso o proteggere una prova",
        })
    if margin <= -5:
        reactions.append({
            "type": "access_blocked",
            "world_state_change": f"un accesso in {current_location.get('name', 'questa zona')} viene bloccato o reso rischioso",
            "scene_prompt": "Rendi visibile il blocco senza chiudere ogni alternativa.",
            "possible_player_response": "cercare uscita alternativa, forzare, negoziare o usare un indizio",
        })

    for step in clock_state.get("clock_step_reactions") or []:
        reactions.append({
            "type": "clock_step",
            "world_state_change": step.get("world_state_change", ""),
            "scene_prompt": step.get("scene_prompt", ""),
            "possible_player_response": step.get("possible_player_response", ""),
        })

    pressure = int(clock_state.get("threat_level") or clock_state.get("value") or 0)
    for agenda in npc_agendas:
        response = agenda.get("pressure_response") or {}
        if not response:
            continue
        tier = "critical" if pressure >= 6 else "high" if pressure >= 4 else "medium" if pressure >= 2 else "low"
        reactions.append({
            "type": "npc_pressure_response",
            "npc_id": agenda.get("id") or agenda.get("npc_id") or agenda.get("name"),
            "world_state_change": response.get(tier) or response.get("medium") or "",
            "scene_prompt": "Fai reagire il PNG secondo la sua agenda, non come nuova sottotrama.",
            "possible_player_response": "interrogarlo, anticiparlo, tagliargli le risorse o convincerlo",
        })
        break

    # R6 — ally_revealed: alta reputazione con una fazione → alleato si manifesta
    for faction_id, rep in faction_reputation.items():
        try:
            score = int(rep.get("score") if isinstance(rep, dict) else rep)
        except (ValueError, TypeError):
            continue
        if score >= 3 and success and margin >= 3:
            ally_npc = (rep.get("trusted_npc") if isinstance(rep, dict) else None) or "un contatto di fiducia"
            reactions.append({
                "type": "ally_revealed",
                "faction_id": faction_id,
                "world_state_change": f"{ally_npc} della fazione {faction_id} appare e offre informazioni o un favore concreto",
                "scene_prompt": "Introduci il PNG alleato come reazione al successo del gruppo: deve aggiungere contesto utile (un nome, una direzione, un avvertimento), non risolvere la scena.",
                "possible_player_response": "ascoltare, chiedere un favore mirato, scambiare informazioni o proteggere l'alleato",
            })
            break  # Massimo 1 ally_revealed per turno

    # R6 — evidence_threatened: antagonista prende contromisure se clue critico vicino
    clue_id = critical_clue_proximity.get("clue_id")
    proximity = int(critical_clue_proximity.get("ticks", 0))
    is_critical = bool(critical_clue_proximity.get("is_required") or critical_clue_proximity.get("is_critical"))
    antagonist_label = critical_clue_proximity.get("antagonist") or "l'antagonista"
    if clue_id and is_critical and proximity >= 2 and proximity < 4:
        reactions.append({
            "type": "evidence_threatened",
            "clue_id": clue_id,
            "world_state_change": f"{antagonist_label} si accorge che il gruppo si avvicina alla prova {clue_id} e tenta di rimuoverla, alterarla o spostarla",
            "scene_prompt": "Mostra il tentativo di contromisure (testimone reticente, prova bruciata, terzo che osserva). Non distruggere la prova: aumenta la tensione.",
            "possible_player_response": "accelerare la ricerca, intercettare il sabotatore, mettere al sicuro la prova o usare quanto già raccolto",
        })

    # R6 — scene_change: location diventa inaccessibile dopo certi eventi
    for change in triggered_scene_changes:
        loc_name = change.get("location_name") or change.get("location_id") or "la zona"
        cause = change.get("cause") or "un evento improvviso"
        reactions.append({
            "type": "scene_change",
            "location_id": change.get("location_id"),
            "world_state_change": f"{loc_name} diventa inaccessibile o pericolosa: {cause}",
            "scene_prompt": f"Manifesta il cambio di stato di {loc_name} ({cause}) come fatto compiuto, con una via fuori o un percorso alternativo già evidente.",
            "possible_player_response": "trovare percorso alternativo, salvare ciò che si può, sfruttare il caos a proprio vantaggio",
        })

    return [r for r in reactions if r.get("world_state_change")]
