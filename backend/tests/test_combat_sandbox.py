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


if __name__ == "__main__":
    unittest.main()
