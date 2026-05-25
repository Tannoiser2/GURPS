import unittest

from App.semantic_concretizer import (
    concretize_adventure_raw,
    concretize_clue,
    concretize_clock_events,
    concretize_location_features,
    concretize_npc_goal,
)


class SemanticConcretizerTests(unittest.TestCase):
    def test_abstract_clue_becomes_concrete_and_actionable(self):
        clue = concretize_clue(
            {"id": "c1", "label": "Contraddizione nella copertura", "thread_id": "T1", "location": "Sala Server"},
            genre="sci_fi",
            locations=[{"name": "Sala Server"}],
        )
        self.assertIn("log", clue["label"].lower())
        self.assertEqual(clue["source_location"], "Sala Server")
        self.assertTrue(clue["possible_actions"])
        self.assertTrue(clue["hidden_implication"])

    def test_location_gets_playable_features(self):
        loc = concretize_location_features({"id": "loc_1", "name": "Sala Server Blindata", "has_combat_potential": True}, genre="sci_fi")
        self.assertGreaterEqual(len(loc["concrete_features"]), 3)
        self.assertGreaterEqual(len(loc["hazards"]), 2)
        self.assertGreaterEqual(len(loc["tactical_features"]), 3)
        self.assertTrue(loc["visual_identity"])

    def test_npc_goal_gets_operational_agenda(self):
        npc = concretize_npc_goal({"id": "voss", "name": "Voss", "role": "antagonist"}, locations=[{"name": "Hangar"}], clues=[{"id": "c1", "label": "Log"}])
        self.assertTrue(npc["goal"])
        self.assertTrue(npc["current_plan"])
        self.assertTrue(npc["fallback_plan"])
        self.assertIn("high", npc["pressure_response"])

    def test_clock_has_concrete_steps(self):
        clock = concretize_clock_events({"id": "clock_main", "label": "Voss cancella le prove", "max_value": 6}, antagonist="Voss")
        self.assertGreaterEqual(len(clock["steps"]), 4)
        self.assertTrue(clock["steps"][0]["world_state_change"])
        self.assertTrue(clock["steps"][0]["possible_player_response"])

    def test_survival_profile_gets_routes_and_resources(self):
        raw = concretize_adventure_raw({
            "title": "Fuga",
            "runtime_profiles": ["survival_escape"],
            "locations": [{"id": "start", "name": "Ingresso"}, {"id": "exit", "name": "Uscita"}],
            "clues": [{"id": "c1", "label": "Traccia accesso laterale", "thread_id": "T1", "location": "Ingresso"}],
        }, genre_hint="action")
        self.assertGreaterEqual(len(raw["genre_runtime"]["routes"]) + len(raw["genre_runtime"]["safe_nodes"]), 2)
        self.assertGreaterEqual(len(raw["resources"]), 2)

    def test_fantasy_clues_do_not_all_become_parchments(self):
        raw = concretize_adventure_raw({
            "title": "Yoren",
            "genre": "fantasy",
            "source_mode": "ai_generated",
            "locations": [
                {"id": "forest", "name": "Foresta adiacente al villaggio"},
                {"id": "hut", "name": "Capanna della Veggente"},
            ],
            "clues": [
                {
                    "id": "c1",
                    "label": "Indizio",
                    "type": "physical_evidence",
                    "thread_id": "T1",
                    "source_location": "Foresta adiacente al villaggio",
                    "reveals": "La presenza di magie antiche nella foresta",
                },
                {
                    "id": "c2",
                    "label": "Indizio",
                    "type": "testimony",
                    "thread_id": "T1",
                    "source_location": "Capanna della Veggente",
                    "reveals": "L'importanza di fermare il rituale e il luogo esatto nella foresta",
                },
                {
                    "id": "c3",
                    "label": "Movimenti di Kira",
                    "type": "behavior",
                    "thread_id": "T2",
                    "source_location": "Villaggio",
                    "reveals": "Kira e a conoscenza di qualcosa che non ha condiviso",
                },
            ],
        }, genre_hint="fantasy")
        labels = [c["label"].lower() for c in raw["clues"]]
        types = [c["type"] for c in raw["clues"]]

        self.assertFalse(all("pergamena cerata" in label for label in labels))
        self.assertTrue(any("rune" in label or "cerchio" in label for label in labels))
        self.assertTrue(any("testimonianza" in label for label in labels))
        self.assertIn("testimony", types)
        self.assertEqual(len(labels), len(set(labels)))


if __name__ == "__main__":
    unittest.main()
