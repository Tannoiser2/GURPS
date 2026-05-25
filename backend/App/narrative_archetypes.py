from __future__ import annotations


def _arch(
    id: str,
    description: str,
    required_modules: list[str],
    optional_modules: list[str],
    runtime_focus: list[str],
    common_clue_types: list[str],
    common_failure_modes: list[str],
    ending_patterns: list[str],
    director_bias: dict | None = None,
    validator_rules: dict | None = None,
) -> dict:
    return {
        "id": id,
        "description": description,
        "required_modules": required_modules,
        "optional_modules": optional_modules,
        "runtime_focus": runtime_focus,
        "pacing_template": ["hook", "pressure", "choice", "payoff"],
        "common_clue_types": common_clue_types,
        "common_failure_modes": common_failure_modes,
        "ending_patterns": ending_patterns,
        "director_bias": director_bias or {},
        "validator_rules": validator_rules or {},
    }


ARCHETYPE_LIBRARY = {
    "investigation_graph": _arch("investigation_graph", "Piste, indizi, deduzioni e payoff.", ["clues", "revelations"], ["witnesses", "false_leads"], ["clue", "deduction"], ["physical_evidence", "testimony", "document"], ["clue_partial", "witness_closes"], ["deduction_finale"]),
    "noir_investigation": _arch("noir_investigation", "Indagine sociale con sospetti ambigui.", ["clues", "actors"], ["factions"], ["social_pressure", "contradiction"], ["testimony", "contradiction", "behavior"], ["betrayal", "false_lead"], ["moral_choice"]),
    "false_monster_investigation": _arch("false_monster_investigation", "Mostro apparente, causa umana o nascosta.", ["clues", "actors"], ["monster_signs"], ["reveal", "social_suspicion"], ["physical_evidence", "contradiction"], ["panic", "wrong_accusation"], ["truth_exposed"]),
    "revenge_thriller": _arch("revenge_thriller", "Inseguimento personale con escalation mirata.", ["actors", "clock"], ["safe_nodes"], ["target", "pressure"], ["behavior", "document"], ["target_escapes", "collateral_cost"], ["confrontation"]),
    "dungeon_exploration": _arch("dungeon_exploration", "Esplorazione di stanze, rischi e risorse.", ["locations", "encounters"], ["keys", "treasure"], ["room", "hazard", "resource"], ["location_detail", "document"], ["trap", "resource_loss"], ["boss_room"]),
    "room_keyed_dungeon": _arch("room_keyed_dungeon", "Dungeon a stanze numerate da preservare.", ["rooms"], ["encounters", "treasure"], ["room_key", "map"], ["location_detail"], ["wrong_route", "trap"], ["keyed_final_room"], validator_rules={"preserve_rooms": True}),
    "wilderness_sandbox": _arch("wilderness_sandbox", "Luoghi liberi e rotte esplorative.", ["locations", "routes"], ["random_tables"], ["travel", "survival"], ["location_detail", "testimony"], ["lost", "resource_loss"], ["discovered_site"]),
    "faction_sandbox": _arch("faction_sandbox", "Fazioni con obiettivi e reazioni offscreen.", ["factions", "actors"], ["clocks"], ["faction_pressure"], ["behavior", "testimony"], ["faction_escalates"], ["balance_shift"]),
    "heist": _arch("heist", "Bersaglio, sicurezza, ingressi, heat ed estrazione.", ["target", "security_layers", "routes"], ["heat"], ["route", "security", "resource"], ["document", "location_detail"], ["heat_tick", "alarm"], ["extraction"]),
    "survival_escape": _arch("survival_escape", "Fuga, risorse, percorsi sicuri e zone pericolose.", ["routes", "resources"], ["safe_nodes"], ["route", "resource"], ["location_detail"], ["resource_loss", "route_blocked"], ["escape"]),
    "ritual_countdown": _arch("ritual_countdown", "Rituale con condizioni, oggetti e clock.", ["clock", "ritual_conditions"], ["special_items"], ["clock", "ritual"], ["document", "physical_evidence"], ["ritual_tick"], ["ritual_stopped"]),
    "monster_hunt": _arch("monster_hunt", "Caccia a creatura con tracce e confronto.", ["monster", "tracks"], ["lair"], ["tracking", "danger"], ["physical_evidence", "behavior"], ["ambush"], ["hunt_finale"]),
    "political_intrigue": _arch("political_intrigue", "Relazioni, fazioni, segreti e alleanze.", ["factions", "actors"], ["clocks"], ["relationship", "leverage"], ["testimony", "document"], ["scandal", "betrayal"], ["coalition_choice"]),
    "military_operation": _arch("military_operation", "Obiettivi tattici, terreno, forze e vincoli.", ["objectives", "terrain", "forces"], ["clock"], ["terrain", "force", "mission"], ["location_detail", "document"], ["enemy_alerted", "objective_cost"], ["mission_result"]),
    "horror_survival": _arch("horror_survival", "Paura, risorse, minaccia crescente.", ["threat", "resources"], ["safe_nodes"], ["dread", "survival"], ["physical_evidence", "behavior"], ["panic", "separation"], ["survive_or_reveal"]),
    "cosmic_horror": _arch("cosmic_horror", "Verità inumana, conoscenza pericolosa.", ["truths", "clues"], ["sanity_pressure"], ["forbidden_truth"], ["document", "contradiction"], ["revelation_cost"], ["truth_cost"]),
    "romance_drama": _arch("romance_drama", "Relazioni, desideri, segreti personali.", ["actors", "relationships"], ["letters"], ["emotion", "choice"], ["testimony", "document", "behavior"], ["misunderstanding"], ["emotional_choice"]),
    "journey_quest": _arch("journey_quest", "Viaggio a tappe con prove e destinazione.", ["routes", "locations"], ["companions"], ["travel", "milestone"], ["location_detail"], ["delay", "route_cost"], ["arrival"]),
    "conspiracy": _arch("conspiracy", "Rete nascosta, livelli di accesso e prove.", ["clues", "actors"], ["factions"], ["layered_reveal"], ["document", "contradiction"], ["coverup"], ["network_exposed"]),
    "siege_defense": _arch("siege_defense", "Difesa di luogo, ondate, risorse e morale.", ["location", "clock", "forces"], ["factions"], ["defense", "resource"], ["location_detail"], ["breach", "morale_loss"], ["hold_or_fall"]),
}


def get_archetype(archetype_id: str) -> dict:
    return ARCHETYPE_LIBRARY.get(archetype_id, ARCHETYPE_LIBRARY["investigation_graph"])
