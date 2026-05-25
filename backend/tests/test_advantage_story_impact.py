import unittest
from unittest.mock import patch

from App.claude_service import _player_sheet
from App.character_creation import advantage_cost
from App.data_advantages import (
    advantage_dodge_bonus,
    advantage_night_vision,
    advantage_skill_bonus,
    advantage_will_modifier,
    trait_cost,
    traits_requiring_self_control,
)
from App.engine import roll_for_player_action


class AdvantageStoryImpactTests(unittest.TestCase):
    def test_vista_imperfetta_penalizes_visual_actions(self):
        base = {
            "name": "Vedetta",
            "role": "Scout",
            "stats": {"forza": 10, "agilita": 12, "intelligenza": 12, "empatia": 10},
            "skills": {"osservare": 12},
            "advantages": [],
            "disadvantages": [],
            "items": [],
            "status": "ok",
        }
        impaired = dict(base)
        impaired["disadvantages"] = ["Vista Imperfetta"]
        with patch("App.engine.random.randint", side_effect=[3, 3, 3, 3, 3, 3]):
            normal = roll_for_player_action(base, "osservo il simbolo inciso sulla parete", 0, [])
            penalized = roll_for_player_action(impaired, "osservo il simbolo inciso sulla parete", 0, [])
        self.assertEqual(normal["skill"], "osservare")
        self.assertEqual(penalized["skill"], "osservare")
        self.assertLess(penalized["effective_skill"], normal["effective_skill"])
        self.assertTrue(any(x["name"] == "Vista Imperfetta" and x["delta"] < 0 for x in penalized["adv_breakdown"]))

    def test_fortuna_can_turn_a_failed_roll_into_better_roll(self):
        player = {
            "name": "Fortunato",
            "role": "Investigatore",
            "stats": {"forza": 10, "agilita": 10, "intelligenza": 10, "empatia": 10},
            "skills": {"investigare": 10},
            "advantages": ["Fortuna"],
            "disadvantages": [],
            "items": [],
            "status": "ok",
        }
        # Primo tiro 18, ritiri 6 e 12: Fortuna sceglie il 6.
        with patch("App.engine.random.randint", side_effect=[6, 6, 6, 2, 2, 2, 4, 4, 4]):
            result = roll_for_player_action(player, "cerco indizi nella stanza", 0, [])
        self.assertEqual(result["rolled"], 6)
        self.assertIsNotNone(result["luck"])
        self.assertEqual(result["luck"]["trait"], "Fortuna")

    def test_traits_are_exposed_to_narrative_prompt(self):
        sheet = _player_sheet({
            "name": "Mira",
            "role": "Tiratrice",
            "stats": {"forza": 10, "agilita": 12, "intelligenza": 10, "empatia": 10},
            "skills": {"mira": 13, "osservare": 9},
            "advantages": ["Fortuna"],
            "disadvantages": ["Vista Imperfetta"],
        })
        self.assertIn("Tratti attivi in fiction", sheet)
        self.assertIn("Fortuna", sheet)
        self.assertIn("Vista Imperfetta", sheet)

    def test_levelled_advantages_scale_cost_and_bonus(self):
        self.assertEqual(trait_cost("Vista Acuta 3"), 6)
        self.assertEqual(advantage_cost("Intrepido 4"), 8)
        self.assertEqual(advantage_skill_bonus(["Vista Acuta 3"], "osservare"), 3)
        self.assertEqual(advantage_skill_bonus(["Talento (Artificiere) 2"], "meccanica"), 2)
        self.assertEqual(advantage_will_modifier(["Intrepido 2"]), 2)
        self.assertEqual(advantage_night_vision(["Visione Notturna 6"]), 6)

    def test_new_lite_advantages_have_mechanical_effects(self):
        self.assertEqual(advantage_dodge_bonus(["Difesa Migliorata (Schivata)"]), 1)
        self.assertEqual(advantage_skill_bonus(["Bilanciamento Perfetto"], "equilibrio"), 6)
        self.assertEqual(advantage_skill_bonus(["Flessuoso"], "arrampicarsi"), 3)
        self.assertEqual(advantage_skill_bonus(["Snodato"], "arrampicarsi"), 5)

    def test_lite_disadvantages_costs_and_penalties(self):
        self.assertEqual(trait_cost("Codice d'Onore (Gentiluomo)"), -10)
        self.assertEqual(trait_cost("Senso del Dovere (Ogni Vivente)"), -20)
        self.assertEqual(trait_cost("Vista Imperfetta Non Correggibile"), -25)
        self.assertEqual(advantage_skill_bonus(["Sincerità"], "ingannare"), -5)
        self.assertEqual(advantage_skill_bonus(["Sordità Parziale"], "osservare"), -4)
        self.assertEqual(advantage_skill_bonus(["Pacifismo (Riluttante a Uccidere)"], "mira"), -4)
        self.assertEqual(advantage_skill_bonus(["Vista Imperfetta"], "osservare"), -6)

    def test_self_control_disadvantages_are_exposed(self):
        controls = traits_requiring_self_control(["Avidità", "Curiosità", "Sincerità", "Voto Minore"])
        self.assertEqual([x["name"] for x in controls], ["Avidità", "Curiosità", "Sincerità"])
        self.assertTrue(all(x["target"] == 12 for x in controls))


if __name__ == "__main__":
    unittest.main()
