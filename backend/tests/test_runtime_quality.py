import unittest

from App.adventure_compiler import compile_from_raw_structure
from App.adventure_validator import validate_adventure_definition


class RuntimeQualityTests(unittest.TestCase):
    def test_compiler_outputs_concrete_runtime_quality(self):
        compiled = compile_from_raw_structure(
            {
                "title": "Operazione Punto Cieco",
                "genre": "action",
                "runtime_profiles": ["investigation_graph", "survival_escape"],
                "win_condition": "Raggiungere l'hangar e fermare Voss usando le prove.",
                "hidden_truth": "Voss cancella le prove per fuggire dall'hangar.",
                "npcs": [{"id": "voss", "name": "Voss", "role": "antagonist"}],
                "locations": [
                    {"id": "server", "name": "Sala Server Blindata"},
                    {"id": "hangar", "name": "Hangar Finale", "has_combat_potential": True},
                ],
                "clues": [
                    {"id": "badge", "label": "Traccia accesso laterale", "thread_id": "T1", "location": "Sala Server Blindata"},
                    {"id": "log", "label": "Contraddizione nella copertura", "thread_id": "T2", "location": "Sala Server Blindata"},
                    {"id": "protocollo", "label": "Procedura incompleta", "thread_id": "T3", "location": "Hangar Finale"},
                ],
                "story_threads": [
                    {"id": "T1", "question": "Dove passa il tunnel laterale?", "required_clues": ["badge"]},
                    {"id": "T2", "question": "Chi ha cancellato i log?", "required_clues": ["log"]},
                    {"id": "T3", "question": "Come si ferma Voss?", "required_clues": ["protocollo"]},
                ],
            },
            source_type="raw_text",
            title="Operazione Punto Cieco",
            genre_hint="action",
        )
        definition = compiled["adventure_definition"]
        report = validate_adventure_definition(definition)

        self.assertTrue(report["playable"])
        self.assertGreaterEqual(report["quality"]["fiction_density_score"], 80)
        self.assertTrue(all(c.source_location for c in definition.clues))
        self.assertTrue(all(c.possible_actions for c in definition.clues))
        self.assertTrue(all(a.goal and a.pressure_response for a in definition.actors))
        self.assertTrue(all(len(clock.steps) >= 4 for clock in definition.event_clocks))
        self.assertTrue(all(len(loc.concrete_features) >= 3 for loc in definition.locations))
        self.assertGreaterEqual(len(definition.genre_runtime.get("routes", [])) + len(definition.genre_runtime.get("safe_nodes", [])), 2)
        finale = definition.finale_conditions[0]
        self.assertGreaterEqual(len(finale.required_clues), 2)
        self.assertTrue(finale.method)
        self.assertTrue(finale.concrete_choice)


if __name__ == "__main__":
    unittest.main()
