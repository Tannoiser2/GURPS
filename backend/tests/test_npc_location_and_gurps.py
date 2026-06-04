"""Verifica dei tre miglioramenti agli NPC.

#1 — gli NPC fisicamente nella location corrente vengono introdotti (prima erano
     ignorati se la pressione narrativa era bassa).
#2 — ogni NPC riceve una scheda GURPS di base (non solo i boss).
#3 — i generi investigation/romance non cadono più sul default ERA_MODERN→9mm
     in modo incontrollato (coperti dalla mappa ere).
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App.adventure_runtime import build_adventure_runtime  # noqa: E402
from App.world_simulator import _npcs_to_introduce  # noqa: E402
from App.engine import _baseline_npc_gurps  # noqa: E402
from App.data_weapons import GENRE_ERA_MAP  # noqa: E402


def _runtime():
    adv = {
        "title": "T", "genre": "sci_fi", "premise": "p",
        "locations": [{"id": "loc_a", "name": "Sala A"}, {"id": "loc_b", "name": "Sala B"}],
        # build_adventure_runtime legge gli NPC dalla chiave "npcs"
        "npcs": [
            {"id": "npc_here", "name": "Qui", "role": "neutrale",
             "location_id": "loc_a", "status": "unintroduced", "agenda_pressure": 0},
            {"id": "npc_far", "name": "Lontano", "role": "neutrale",
             "location_id": "loc_b", "status": "unintroduced", "agenda_pressure": 0},
        ],
        "clues": [], "story_threads": [], "revelations": [],
    }
    return build_adventure_runtime(adv, {})


class TestNpcLocationIntroduction(unittest.TestCase):
    def test_npc_in_current_location_is_introduced(self):
        gsd = {"current_scene_id": "loc_a", "threat_level": 0,
               "map_state": {"current_node_id": "loc_a"}}
        result = _npcs_to_introduce(_runtime(), gsd)
        self.assertIn("npc_here", result)        # è nella stanza → entra anche con pressione 0
        self.assertNotIn("npc_far", result)      # altra stanza, pressione 0 → no

    def test_no_location_falls_back_to_pressure(self):
        # senza location corrente, nessuno entra con pressione 0 e threat 0
        result = _npcs_to_introduce(_runtime(), {"threat_level": 0})
        self.assertEqual(result, [])


class TestBaselineGurps(unittest.TestCase):
    def test_every_npc_gets_a_sheet(self):
        for threat in (0, 1, 2, 3):
            sheet = _baseline_npc_gurps("neutrale", threat)
            for field in ("gurps_fo", "gurps_de", "gurps_in", "gurps_sa",
                          "combat_hp", "combat_attack_skill"):
                self.assertIsNotNone(sheet.get(field))
            self.assertTrue(sheet["gurps_skills"])

    def test_stats_scale_with_threat(self):
        weak = _baseline_npc_gurps("civile", 0)
        boss = _baseline_npc_gurps("antagonista", 3)
        self.assertGreater(boss["combat_attack_skill"], weak["combat_attack_skill"])
        self.assertGreaterEqual(boss["combat_hp"], weak["combat_hp"])

    def test_role_picks_primary_skill(self):
        self.assertIn("combattere", _baseline_npc_gurps("antagonista", 3)["gurps_skills"])


class TestGenreCoverage(unittest.TestCase):
    def test_investigation_and_romance_covered(self):
        for g in ("investigation", "romance", "noir"):
            self.assertIn(g, GENRE_ERA_MAP)


if __name__ == "__main__":
    unittest.main()
