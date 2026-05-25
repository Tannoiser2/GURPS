import unittest
from unittest.mock import patch

from App.claude_service import (
    _fallback_pdf_adventure,
    _normalize_adventure_canon,
    _safe_master_refusal_fallback,
    _validate_master_state_updates,
)
from App.adventure_runtime import build_adventure_runtime
from App.narrative_director import make_director_decision
from App.state_validator import merge_engine_and_ai_updates
from App.world_simulator import simulate_world_state
from App.adventure_compiler import compile_from_raw_structure, initialize_runtime_state, legacy_adventure_from_definition
from App.adventure_validator import validate_adventure_definition
from App.engine import roll_for_player_action
from App.engine import start_game_from_selection
from App.escalation_limiter import compute_allowed_escalation_tier
from App.genre_constraints import get_genre_profile
from App.state_validator import validate_ai_state_updates
from App.models import GameState, TeamSetupState, Player, MapState, MapNode, WorldNPC
from App import main as main_module


class NarrativeCanonTests(unittest.TestCase):
    def sample_adventure(self):
        return _normalize_adventure_canon({
            "title": "La Cripta",
            "hidden_truth": "Aldric protegge la valle dal morbo.",
            "win_condition": "Rinnovare il patto senza liberare il morbo.",
            "npcs": [{"id": "npc_1", "name": "Aldric", "role": "antagonista", "secret": "custode forzato"}],
            "locations": [{"id": "loc_1", "name": "Cripta", "description": "Altare sigillato"}],
            "clues": [
                {"id": "c1", "text": "Diario di Aldric", "thread_id": "T1", "reveals": "L'altare è sotto Elara", "location": "Cripta"},
                {"id": "c2", "text": "Sigillo di ferro", "thread_id": "T1", "reveals": "Serve un custode volontario", "location": "Sarcofago"},
                {"id": "c3", "text": "Lettera dei Vorn", "thread_id": "T2", "reveals": "Lysander ha rotto il sigillo", "location": "Torre"},
            ],
        }, source="test")

    def test_every_clue_has_valid_thread(self):
        adventure = self.sample_adventure()
        thread_ids = {t["id"] for t in adventure["story_threads"]}
        self.assertGreaterEqual(len(adventure["clues"]), 3)
        self.assertTrue(all(c["thread_id"] in thread_ids for c in adventure["clues"]))

    def test_state_updates_block_runtime_threads_but_allow_richer_state_changes(self):
        adventure = self.sample_adventure()
        clean = _validate_master_state_updates(
            {
                "clues_found": ["c1", "c2"],
                "clue_progress": [{"clue_id": "c3", "note": "traccia parziale"}],
                "new_threads": ["Un mistero inventato"],
            },
            adventure=adventure,
            game_state_data={"clues_found": []},
            prerolled={"success": True},
        )
        self.assertEqual(clean["clues_found"], ["c1", "c2"])
        self.assertEqual(clean["clue_progress"], [{"clue_id": "c3", "note": "traccia parziale", "ticks": 1}])
        self.assertEqual(clean["new_threads"], [])

    def test_thread_reaches_ready_to_deduce_threshold(self):
        adventure = self.sample_adventure()
        clean = _validate_master_state_updates(
            {"story_over": True, "victory": True},
            adventure=adventure,
            game_state_data={"clues_found": ["c1", "c2"]},
            prerolled={"success": True},
        )
        self.assertFalse(clean["story_over"], "Il finale non parte senza thread risolti o finale_condition esplicita")

        thread = next(t for t in adventure["story_threads"] if t["id"] == "T1")
        discovered = [cid for cid in thread["required_clues"] if cid in {"c1", "c2"}]
        self.assertGreaterEqual(len(discovered), thread["minimum_clues_to_deduce"])

    def test_failure_creates_persistent_change(self):
        adventure = self.sample_adventure()
        clean = _validate_master_state_updates(
            {},
            adventure=adventure,
            game_state_data={"clues_found": []},
            prerolled={"success": False},
        )
        self.assertGreaterEqual(clean["threat_increase"], 1)

    def test_hot_and_final_locations_get_tactical_maps(self):
        adventure = self.sample_adventure()
        hot_locations = [
            loc for loc in adventure["locations"]
            if (loc.get("tactical_map") or {}).get("enabled")
        ]
        self.assertGreaterEqual(len(hot_locations), 1)
        final = adventure["locations"][-1]
        self.assertTrue(final["has_combat_potential"])
        self.assertEqual(final["tactical_map"]["role"], "finale")
        self.assertIn(final["tactical_map"]["layout"], {"room", "narrow", "open"})

    def test_pdf_refusal_fallback_still_returns_playable_bible(self):
        adventure = _fallback_pdf_adventure(
            "La Cripta di Vhal\nSala del Sigillo\nPadre Aldric custodisce il passaggio\nCappella Finale",
            "fantasy",
            [],
            reason="test",
        )
        self.assertTrue(adventure["fallback_used"])
        self.assertGreaterEqual(len(adventure["clues"]), 3)
        self.assertGreaterEqual(len(adventure["story_threads"]), 3)
        self.assertTrue((adventure["locations"][-1]["tactical_map"] or {}).get("enabled"))

    def test_master_refusal_fallback_never_exposes_raw_refusal(self):
        adventure = self.sample_adventure()
        result = _safe_master_refusal_fallback(
            adventure=adventure,
            active_name="Ranger",
            player_action="indaga sulla cripta",
            prerolled={"success": False, "outcome": "fallimento", "rolled": 16, "effective_skill": 10, "margin": -6},
            active_player_id=1,
        )
        self.assertNotIn("can't assist", result["narrative"].lower())
        self.assertTrue(result["state_updates"]["clue_progress"] or result["state_updates"]["threat_increase"])

    def test_state_driven_runtime_simulates_before_ai(self):
        adventure = self.sample_adventure()
        game_state_data = {
            "clues_found": [],
            "clue_progress": {},
            "map_state": {
                "current_node_id": "loc_1",
                "nodes": {"loc_1": {"name": "Cripta", "description": "Altare sigillato"}},
            },
        }
        runtime = build_adventure_runtime(adventure, game_state_data)
        simulation = simulate_world_state(
            runtime,
            player_action="esamina l'altare nella cripta",
            prerolled={"success": True, "skill": "investigare", "outcome": "successo parziale"},
            game_state_data=game_state_data,
        )
        decision = make_director_decision(runtime, simulation, prerolled={"success": True})
        self.assertEqual(runtime.runtime_profile, "ritual_dungeon")
        self.assertTrue(simulation["proposed_updates"]["clue_progress"])
        self.assertTrue(decision["state_updates_required"]["clue_progress"])

    def test_clock_tick_deterministic_by_outcome(self):
        from App.world_simulator import _compute_clock_tick
        # Fallimento critico → +2
        self.assertEqual(_compute_clock_tick({"success": False, "margin": -6, "critical": True}), 2)
        # Fallimento semplice → +1
        self.assertEqual(_compute_clock_tick({"success": False, "margin": -2}), 1)
        # Successo parziale → +1
        self.assertEqual(_compute_clock_tick({"success": True, "outcome": "successo parziale"}), 1)
        # Successo pieno → 0
        self.assertEqual(_compute_clock_tick({"success": True, "outcome": "successo"}), 0)

    def test_clue_selected_by_location(self):
        adventure = self.sample_adventure()
        game_state_data = {
            "clues_found": [],
            "clue_progress": {},
            "map_state": {
                "current_node_id": "loc_1",
                "nodes": {"loc_1": {"name": "Cripta"}},
            },
        }
        runtime = build_adventure_runtime(adventure, game_state_data)
        simulation = simulate_world_state(
            runtime,
            player_action="cerco indizi nella cripta",
            prerolled={"success": True, "skill": "investigare", "outcome": "successo"},
            game_state_data=game_state_data,
        )
        # c1 è nella Cripta → deve essere selezionato
        clue_id = simulation["selected_clue_id"]
        self.assertEqual(clue_id, "c1")

    def test_clue_completed_after_second_tick(self):
        adventure = self.sample_adventure()
        game_state_data = {
            "clues_found": [],
            "clue_progress": {"c1": {"ticks": 1}},
            "map_state": {
                "current_node_id": "loc_1",
                "nodes": {"loc_1": {"name": "Cripta"}},
            },
        }
        runtime = build_adventure_runtime(adventure, game_state_data)
        simulation = simulate_world_state(
            runtime,
            player_action="esamino il diario di Aldric",
            prerolled={"success": True, "skill": "investigare", "outcome": "successo"},
            game_state_data=game_state_data,
        )
        # Secondo tick con successo → clue completata
        self.assertIn("c1", simulation["proposed_updates"]["clues_found"])
        self.assertEqual(simulation["proposed_updates"]["clue_progress"], [])

    def test_clock_trigger_detected_at_boundary(self):
        adventure = self.sample_adventure()
        # Threat al massimo meno 1 tick — un fallimento fa scattare il clock
        game_state_data = {"clues_found": [], "clue_progress": {}, "threat_level": 7}
        runtime = build_adventure_runtime(adventure, game_state_data)
        simulation = simulate_world_state(
            runtime,
            player_action="cerco uscita",
            prerolled={"success": False, "margin": -2},
            game_state_data=game_state_data,
        )
        self.assertEqual(simulation["clock_tick"], 1)
        self.assertTrue(simulation["clock_triggers"], "Il clock dovrebbe scattare a 8/8")

    def test_npc_introduced_under_high_threat(self):
        adventure = self.sample_adventure()
        # Modifica l'NPC per avere agenda_pressure alta
        adventure["npcs"][0]["threat_to_player"] = 3
        game_state_data = {"clues_found": [], "clue_progress": {}, "threat_level": 2}
        runtime = build_adventure_runtime(adventure, game_state_data)
        simulation = simulate_world_state(
            runtime,
            player_action="osservo la sala",
            prerolled={"success": True, "outcome": "successo"},
            game_state_data=game_state_data,
        )
        # threat_pct = 2/8 = 25% >= 20% con agenda_pressure=3 → introduce Aldric
        self.assertEqual(simulation["npcs_to_introduce"], ["npc_1"])

    def test_director_produces_single_concrete_directive(self):
        adventure = self.sample_adventure()
        game_state_data = {
            "clues_found": [],
            "clue_progress": {},
            "map_state": {"current_node_id": "loc_1", "nodes": {"loc_1": {"name": "Cripta"}}},
        }
        runtime = build_adventure_runtime(adventure, game_state_data)
        simulation = simulate_world_state(
            runtime,
            player_action="esamina l'altare",
            prerolled={"success": True, "skill": "investigare", "outcome": "successo parziale"},
            game_state_data=game_state_data,
        )
        decision = make_director_decision(runtime, simulation, prerolled={"success": True})
        directive = decision.get("scene_directive", "")
        # La direttiva deve essere una stringa non vuota con il clue id
        self.assertIsInstance(directive, str)
        self.assertGreater(len(directive), 20)
        self.assertIn("c1", directive)

    def test_engine_updates_take_precedence_over_ai_updates(self):
        merged = merge_engine_and_ai_updates(
            {"clue_progress": [{"clue_id": "c1", "note": "motore", "ticks": 1}], "threat_increase": 1},
            {"clue_progress": [{"clue_id": "c2", "note": "ai", "ticks": 1}], "new_threads": ["mistero"], "threat_increase": 0},
        )
        self.assertEqual(merged["new_threads"], [])
        self.assertEqual(merged["threat_increase"], 1)
        self.assertEqual(len(merged["clue_progress"]), 2)

    def test_adventure_compiler_builds_definition_runtime_and_legacy_bridge(self):
        compiled = compile_from_raw_structure({
            "title": "Miniera Nera",
            "genre": "fantasy",
            "runtime_profiles": ["investigation_graph", "ritual_dungeon"],
            "premise": "La miniera canta di notte.",
            "objectives": [{"id": "obj_stop", "label": "Fermare il canto", "success_conditions": ["scoprire la fonte"]}],
            "revelations": [{"id": "rev_source", "thread_id": "T1", "statement": "Il canto viene da un sigillo", "required_clues": ["clue_song"]}],
            "clues": [{"id": "clue_song", "label": "Polvere nera che vibra", "thread_id": "T1", "source_location": "Ingresso", "revelation_ids": ["rev_source"]}],
            "locations": [{"id": "loc_entry", "name": "Ingresso", "type": "room", "access_state": "open"}],
            "event_clocks": [{"id": "clock_canto", "label": "Canto", "max": 6, "on_complete": "la miniera si apre"}],
            "finale_conditions": [{"id": "finale_stop", "label": "Spezzare il sigillo", "depends_on": ["obj_stop"]}],
        }, source_type="raw_text", title="Miniera Nera", genre_hint="fantasy")
        definition = compiled["adventure_definition"]
        runtime = compiled["runtime_state"]
        report = compiled["validation_report"]
        self.assertTrue(report["playable"])
        self.assertEqual(runtime.definition_id, definition.id)
        self.assertEqual(runtime.thread_to_revelation_ids["T1"], ["rev_source"])
        self.assertEqual(runtime.clue_to_revelation_ids["clue_song"], ["rev_source"])
        self.assertIn("finale_stop", runtime.finale_runtime)
        self.assertTrue(definition.legacy_adventure["from_runtime_compiler"])
        self.assertTrue(definition.legacy_adventure["clues"])

    def test_runtime_state_resolves_legacy_thread_tokens_to_revelations(self):
        compiled = compile_from_raw_structure({
            "title": "Miniera Nera",
            "genre": "fantasy",
            "objectives": [{"id": "obj_stop", "label": "Fermare il canto", "success_conditions": ["scoprire la fonte"]}],
            "revelations": [{"id": "rev_source", "thread_id": "T1", "statement": "Il canto viene da un sigillo", "required_clues": ["clue_song"]}],
            "clues": [{"id": "clue_song", "label": "Polvere nera che vibra", "thread_id": "T1", "source_location": "Ingresso", "revelation_ids": ["rev_source"]}],
            "locations": [{"id": "loc_entry", "name": "Ingresso", "type": "room", "access_state": "open"}],
            "finale_conditions": [{"id": "finale_stop", "label": "Spezzare il sigillo", "required_threads": ["T1"], "required_clues": ["clue_song"]}],
        }, source_type="raw_text", title="Miniera Nera", genre_hint="fantasy")
        definition = compiled["adventure_definition"]
        runtime = compiled["runtime_state"]
        main_module.game_state = GameState(
            turn=1,
            log="test",
            team_setup=TeamSetupState(genre="fantasy"),
            adventure_definition=definition,
            adventure_runtime_state=runtime,
        )

        main_module._sync_runtime_state_from_updates(
            {"clues_found": ["clue_song"], "closed_threads": ["T1 → Il sigillo e la fonte"]},
            "La deduzione chiude la pista.",
        )

        rt = main_module.game_state.adventure_runtime_state
        self.assertIn("rev_source", rt.resolved_revelation_ids)
        self.assertNotIn("rev_source", rt.active_revelation_ids)
        self.assertEqual(rt.finale_runtime["finale_stop"]["status"], "available")

    def test_master_validator_accepts_structured_runtime_updates(self):
        adventure = self.sample_adventure()
        adventure["locations"][0]["id"] = "loc_1"
        adventure["objectives"] = [{"id": "obj_main", "label": "Rinnovare il patto"}]
        adventure["factions"] = [{"id": "culto", "name": "Culto"}]
        adventure["finale_conditions"] = [{"id": "fin_main", "label": "Patto"}]
        clean = _validate_master_state_updates(
            {
                "location_updates": [{"id": "loc_1", "status": "changed", "access_state": "unlocked"}],
                "objective_updates": [{"id": "obj_main", "status": "active"}],
                "faction_updates": [{"id": "culto", "status": "escalating", "pressure": 7}],
                "finale_updates": [{"id": "fin_main", "status": "seeded"}],
                "flags": {"patto_visto": "la squadra ha visto il sigillo"},
            },
            adventure=adventure,
            game_state_data={"clues_found": []},
            prerolled={"success": True},
        )

        self.assertEqual(clean["location_updates"], [{"id": "loc_1", "status": "changed", "access_state": "unlocked"}])
        self.assertEqual(clean["objective_updates"], [{"id": "obj_main", "status": "active"}])
        self.assertEqual(clean["faction_updates"], [{"id": "culto", "status": "escalating", "pressure": 7}])
        self.assertEqual(clean["finale_updates"], [{"id": "fin_main", "status": "seeded"}])
        self.assertEqual(clean["flags"]["patto_visto"], "la squadra ha visto il sigillo")

    def test_runtime_opening_is_italian_and_not_placeholder(self):
        compiled = compile_from_raw_structure({
            "title": "Crown Jewels",
            "genre": "action",
            "premise": "The PCs are fleeing from a crime boss through secret tunnels.",
            "initial_hook": "The PCs are fleeing from a crime boss through secret tunnels.",
            "objectives": [{"id": "obj", "label": "Recover the Irish Crown Jewels", "success_conditions": ["Bring the Jewels to Safety"]}],
            "revelations": [{"id": "rev", "thread_id": "T1", "statement": "The Irish Crown Jewels are hidden on Speirling Island, located in an eternal fog bank.", "required_clues": ["clue_1"]}],
            "clues": [{"id": "clue_1", "label": "Tunnel map", "thread_id": "T1", "source_location": "Predjama Castle Tunnels", "revelation_ids": ["rev"]}],
            "locations": [{"id": "tunnels", "name": "Predjama Castle Tunnels"}, {"id": "vienna", "name": "University of Vienna"}],
        }, source_type="raw_text", title="Crown Jewels", genre_hint="action")
        opening = main_module._opening_context_from_definition(compiled["adventure_definition"])
        options = main_module._initial_runtime_options(compiled["adventure_definition"], [{"id": 1, "skills": {"osservare": 13, "sopravvivenza": 11}}])

        self.assertIn("personaggi", opening["narrative"].lower())
        self.assertIn("boss criminale", opening["narrative"].lower())
        self.assertNotIn("The PCs", opening["narrative"])
        self.assertNotEqual(options[0]["text"], "Esaminare la zona iniziale")
        self.assertTrue(options[0]["text"])

    def test_compiled_adventure_start_bypasses_legacy_procedural_canon(self):
        compiled = compile_from_raw_structure({
            "title": "Torre Calda",
            "genre": "fantasy",
            "premise": "La torre nasconde un sigillo.",
            "objectives": [{"id": "obj", "label": "Spezzare il sigillo", "success_conditions": ["raggiungere la cima"]}],
            "revelations": [{"id": "rev", "thread_id": "T1", "statement": "Il sigillo e nella cima", "required_clues": ["clue"]}],
            "clues": [{"id": "clue", "label": "Scala incisa", "thread_id": "T1", "source_location": "Atrio"}],
            "locations": [
                {"id": "atrium", "name": "Atrio", "type": "room", "access_state": "open"},
                {"id": "summit", "name": "Cima", "type": "room", "access_state": "open", "tactical_map": {"enabled": True, "role": "finale"}},
            ],
            "finale_conditions": [{"id": "fin", "label": "Confronto in cima", "depends_on": ["obj"]}],
        }, source_type="raw_text", title="Torre Calda", genre_hint="fantasy")
        player = Player(
            id=1, name="Ranger", role="Ranger", archetype="Ranger",
            stats={"forza": 10, "agilita": 10, "intelligenza": 10, "empatia": 10},
            skills={"osservare": 10},
        )
        current = GameState(
            turn=0,
            log="setup",
            team_setup=TeamSetupState(genre="fantasy", candidate_pool=[player], provider="none"),
        )
        payload = {
            **compiled["adventure_definition"].legacy_adventure,
            "adventure_definition": compiled["adventure_definition"].model_dump(),
            "runtime_state": compiled["runtime_state"].model_dump(),
        }
        with patch("App.engine.generate_actions_for_selected_team", side_effect=lambda candidates, **kwargs: candidates):
            game = start_game_from_selection(current, [1], {}, payload)
        self.assertEqual(game.scene_source, "compiled_runtime")
        self.assertEqual(game.story.narrative_mode, "compiled_runtime")
        self.assertEqual(game.mission.title, "Torre Calda")
        self.assertIn("summit", game.map_state.nodes)
        self.assertTrue(game.map_state.nodes["summit"].tactical_map.get("enabled"))

    def test_hot_zone_forces_combat_when_entered(self):
        node = MapNode(
            id="summit",
            name="Cima",
            kind="room",
            description="Sala finale",
            contains_enemy=True,
            is_final=True,
            tactical_map={
                "enabled": True,
                "role": "finale",
                "trigger": "quando la squadra entra nella sala finale",
                "layout": "room",
            },
        )
        main_module.game_state = GameState(
            turn=1,
            log="test",
            team_setup=TeamSetupState(genre="fantasy"),
            map_state=MapState(
                map_type="fantasy",
                theme="test",
                nodes={"summit": node},
                current_node_id="summit",
                start_node_id="summit",
                objective_node_id="summit",
            ),
            world_npcs=[
                WorldNPC(
                    id="aldric",
                    name="Aldric",
                    role="antagonista",
                    current_node_id="summit",
                    threat_to_player=2,
                )
            ],
            players=[Player(
                id=1,
                name="Ranger",
                role="Ranger",
                archetype="Ranger",
                stats={"forza": 10, "agilita": 10, "intelligenza": 10, "empatia": 10},
            )],
        )

        updates = main_module._force_hot_zone_combat_update(
            {"activate_combat": False, "combat_scene": None},
            "Il gruppo entra nella sala finale",
        )

        self.assertTrue(updates["activate_combat"])
        self.assertTrue(updates["combat_scene"]["forced_by_hot_zone"])
        self.assertEqual(updates["combat_scene"]["entities"][0]["name"], "Aldric")

    def test_passive_action_does_not_fallback_to_best_combat_skill(self):
        player = {
            "name": "Ranger",
            "stats": {"forza": 14, "agilita": 11, "intelligenza": 10, "empatia": 10},
            "skills": {"combattere": 18, "osservare": 9},
            "items": ["spada"],
            "status": "ok",
        }
        roll = roll_for_player_action(player, "osservo i simboli sulla porta", threat_level=0, scene_tags=[])
        self.assertEqual(roll["intent"], "observation")
        self.assertNotEqual(roll["skill"], "combattere")
        self.assertNotIn("combattere", roll["allowed_skills"])

    def test_major_event_is_blocked_without_trigger(self):
        adventure = self.sample_adventure()
        clean = _validate_master_state_updates(
            {
                "major_event": "apocalypse",
                "story_over": True,
                "victory": False,
                "threat_increase": 3,
            },
            adventure=adventure,
            game_state_data={"clues_found": [], "threat_level": 2, "threat_max": 10},
            prerolled={"success": False, "intent": "observation", "non_combat_action": True},
        )
        self.assertFalse(clean["story_over"])
        self.assertFalse(clean["victory"])
        self.assertIsNone(clean["major_event"])
        self.assertLessEqual(clean["threat_increase"], 1)
        self.assertTrue(clean["needs_alternative_narration"])
        self.assertIn("apocalypse", clean["blocked_state_updates"])

    def test_major_event_allowed_with_finale_condition(self):
        adventure = self.sample_adventure()
        clean = _validate_master_state_updates(
            {
                "major_event": "finale",
                "story_over": True,
                "victory": True,
                "explicit_trigger": "finale_condition",
                "finale_condition_met": True,
                "threat_increase": 0,
            },
            adventure=adventure,
            game_state_data={"clues_found": ["c1", "c2"], "finale_condition_met": True},
            prerolled={"success": True, "intent": "social", "non_combat_action": True},
        )
        self.assertTrue(clean["story_over"])
        self.assertTrue(clean["victory"])
        self.assertFalse(clean.get("needs_alternative_narration"))

    def test_failed_investigation_cannot_escalate_to_apocalypse(self):
        profile = get_genre_profile(["investigation_graph"], "fantasy")
        tier = compute_allowed_escalation_tier(
            {"outcome": "FALLIMENTO", "success": False},
            "observation",
            "investigation_graph",
            active_clocks=[],
            scene_context={},
            genre_profile=profile,
        )
        self.assertLessEqual(tier, 3)
        clean = validate_ai_state_updates(
            {"major_event": "apocalypse", "story_over": True, "threat_increase": 3},
            director_decision={
                "allowed_escalation_tier": tier,
                "allowed_escalation_types": profile["allowed_escalations"],
                "forbidden_escalation_types": profile["forbidden_escalations"],
                "genre_profile": profile,
                "runtime_profile": "investigation_graph",
                "reason": "test",
            },
            genre_profile=profile,
            prerolled={"intent": "observation", "success": False, "outcome": "FALLIMENTO", "non_combat_action": True},
            narrative_text="Il sole nero annuncia la fine del mondo.",
        )
        self.assertFalse(clean["story_over"])
        self.assertTrue(clean["blocked_major_events"])
        self.assertTrue(clean["downgraded_events"])
        self.assertLessEqual(clean["allowed_escalation_tier"], 3)

    def test_critical_failure_passive_blocks_terminal_but_allows_danger_tier(self):
        profile = get_genre_profile(["ritual_dungeon"], "fantasy")
        tier = compute_allowed_escalation_tier(
            {"outcome": "FALLIMENTO CRITICO", "success": False, "critical": True},
            "investigation",
            "ritual_dungeon",
            active_clocks=[],
            scene_context={},
            genre_profile=profile,
        )
        self.assertLessEqual(tier, 4)
        clean = validate_ai_state_updates(
            {"story_over": True, "major_event": "boss_release", "activate_combat": True},
            director_decision={
                "allowed_escalation_tier": tier,
                "allowed_escalation_types": profile["allowed_escalations"],
                "forbidden_escalation_types": profile["forbidden_escalations"],
                "genre_profile": profile,
                "runtime_profile": "ritual_dungeon",
            },
            genre_profile=profile,
            prerolled={"intent": "investigation", "success": False, "critical": True, "non_combat_action": True},
        )
        self.assertFalse(clean["story_over"])
        self.assertIn("terminal_event_without_finale_condition", clean["blocked_major_events"])


if __name__ == "__main__":
    unittest.main()
