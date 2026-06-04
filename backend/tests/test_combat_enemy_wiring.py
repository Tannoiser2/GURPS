"""Verifica che il combattimento usi stat reali: scheda dell'NPC ostile presente
nel nodo, oppure una creatura del bestiario (non più il placeholder hp=2)."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App.engine import _combat_enemy_for_scene  # noqa: E402
from App.models import WorldNPC  # noqa: E402


def _state(world_npcs, genre="fantasy", threat_level=0):
    # duck-typing: _combat_enemy_for_scene usa solo questi attributi
    return SimpleNamespace(
        mission=SimpleNamespace(genre=genre),
        adventure_definition=None,
        world_npcs=world_npcs,
        scene=SimpleNamespace(threat_level=threat_level),
    )


class TestCombatEnemyWiring(unittest.TestCase):
    def test_hostile_npc_at_node_uses_its_sheet(self):
        npc = WorldNPC(
            id="n1", name="Bruto", role="antagonista", current_node_id="loc_a",
            status="alive", threat_to_player=3,
            combat_hp=14, combat_max_hp=14, combat_dr=2,
            combat_attack_skill=14, combat_active_defense=10,
            combat_damage_dice="1d", combat_damage_type="cut",
        )
        e = _combat_enemy_for_scene(_state([npc]), "loc_a", "Minaccia")
        self.assertIsNotNone(e)
        self.assertEqual(e.name, "Bruto")
        self.assertEqual(e.hp, 14)
        self.assertEqual(e.attack_skill, 14)
        self.assertEqual(e.type, "enemy")

    def test_npc_in_other_node_ignored(self):
        npc = WorldNPC(id="n1", name="Bruto", role="antagonista",
                       current_node_id="loc_b", status="alive", threat_to_player=3,
                       combat_hp=14)
        e = _combat_enemy_for_scene(_state([npc]), "loc_a", "Strana presenza")
        # nessun NPC qui → ripiega sul bestiario, non sull'NPC dell'altro nodo
        self.assertIsNotNone(e)
        self.assertNotEqual(e.name, "Bruto")

    def test_bestiary_gives_real_stats(self):
        e = _combat_enemy_for_scene(_state([]), "loc_x", "Bestia ignota")
        self.assertIsNotNone(e)
        self.assertGreater(e.hp, 2)          # non più il placeholder hp=2
        self.assertGreater(e.attack_skill, 0)

    def test_bestiary_deterministic_per_node(self):
        e1 = _combat_enemy_for_scene(_state([]), "loc_x", "x")
        e2 = _combat_enemy_for_scene(_state([]), "loc_x", "x")
        self.assertEqual(e1.name, e2.name)   # stessa location → stessa creatura

    def test_unknown_genre_still_returns_enemy(self):
        e = _combat_enemy_for_scene(_state([], genre="genere_strano"), "loc_y", "x")
        self.assertIsNotNone(e)


if __name__ == "__main__":
    unittest.main()
