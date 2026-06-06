"""Modalità test del combattimento tattico: PC pregenerato vs bestiario/NPC."""
import unittest

import App.main as main
from App.engine import empty_game_state


class TestCombatSandbox(unittest.TestCase):
    def setUp(self):
        main.game_state = empty_game_state()

    def test_builds_combat_from_bestiary(self):
        payload = main.CombatSandboxPayload(
            creatures=["lupo", "goblin"], genre="fantasy", archetype="guerriero")
        resp = main.combat_sandbox(payload)
        self.assertNotIn("error", resp)
        self.assertEqual(resp["enemy_count"], 2)
        # PC pregenerato presente, combat-ready
        self.assertEqual(len(main.game_state.players), 1)
        p = main.game_state.players[0]
        self.assertGreater(p.max_hp, 0)
        self.assertTrue(p.actions, "il PC pregenerato deve avere almeno un'azione")
        # Scena con nemici vivi (il frontend entra in combattimento)
        self.assertIsNotNone(main.game_state.scene)
        self.assertEqual(len(main.game_state.scene.entities), 2)
        for e in main.game_state.scene.entities:
            self.assertGreater(e.hp, 0)
            self.assertGreater(e.attack_skill, 0)

    def test_random_fill_when_nothing_selected(self):
        resp = main.combat_sandbox(main.CombatSandboxPayload(genre="fantasy"))
        self.assertNotIn("error", resp)
        self.assertGreaterEqual(resp["enemy_count"], 1)

    def test_ranged_archetype_and_npc(self):
        # NPC nel mondo affrontabile
        from App.models import WorldNPC
        main.game_state.world_npcs = [WorldNPC(
            id="npc1", name="Sicario", role="antagonista", current_node_id="n1", threat_to_player=2,
            combat_hp=12, combat_max_hp=12, combat_attack_skill=13,
            combat_active_defense=9, combat_damage_dice="1d+1", combat_damage_type="imp")]
        resp = main.combat_sandbox(main.CombatSandboxPayload(
            npc_ids=["npc1"], genre="sci_fi", archetype="tiratore"))
        self.assertNotIn("error", resp)
        self.assertEqual(resp["enemy_count"], 1)
        self.assertEqual(main.game_state.scene.entities[0].name, "Sicario")


    def test_swing_thrust_resolution(self):
        from App.combat import resolve_swing_thrust
        self.assertEqual(resolve_swing_thrust("sw+1", 14), "2d+1")   # ST14 sw=2d
        self.assertEqual(resolve_swing_thrust("sw", 10), "1d")        # ST10 sw=1d
        self.assertEqual(resolve_swing_thrust("thr-1", 13), "1d-1")   # ST13 thr=1d
        self.assertEqual(resolve_swing_thrust("thr", 11), "1d-1")     # ST11 thr=1d-1
        self.assertEqual(resolve_swing_thrust("2d+1", 14), "2d+1")    # dadi intatti
        self.assertEqual(resolve_swing_thrust("1d-1", 10), "1d-1")    # dadi intatti

    def test_melee_attack_does_not_crash(self):
        # Regressione: un PC con arma sw/thr non deve far crashare l'engine.
        from App.engine import initiate_combat_action
        main.combat_sandbox(main.CombatSandboxPayload(creatures=["goblin"], genre="fantasy"))
        p = main.game_state.players[0]
        action = p.actions[0]   # Spada (damage "sw+1")
        gs = initiate_combat_action(
            main.game_state, attacker_id=0, action=action,
            target_entity_id="enemy_1", action_type="normal", distance=1)
        self.assertIsNotNone(gs.last_attack_result)


if __name__ == "__main__":
    unittest.main()
