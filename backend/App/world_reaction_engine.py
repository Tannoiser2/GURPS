from __future__ import annotations


def generate_world_reactions(
    *,
    player_action_result: dict | None = None,
    clock_state: dict | None = None,
    npc_agendas: list[dict] | None = None,
    current_location: dict | None = None,
) -> list[dict]:
    """Produce reazioni concrete del mondo senza inventare nuova trama.

    Le reazioni sono piccoli cambi di stato utilizzabili dal renderer AI:
    allarmi, blocchi, movimenti di PNG, testimoni che si nascondono, prove a rischio.
    """
    result = player_action_result or {}
    clock_state = clock_state or {}
    current_location = current_location or {}
    npc_agendas = npc_agendas or []
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

    return [r for r in reactions if r.get("world_state_change")]
