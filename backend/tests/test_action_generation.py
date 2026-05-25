"""Test F2: le azioni generate da actions_for_scene usano possible_actions LLM,
non il template 'Cercare X a Y', e sono filtrate per location.
"""
import unittest

from App.runtime_models import ActorState, AdventureDefinition, LocationState, RuntimeClue
from App.scene_context import actions_for_scene


def _thrusher_manor_definition() -> AdventureDefinition:
    locations = [
        LocationState(
            id="loc_manor",
            name="Thrusher Manor",
            exits=["Port de Médard"],
        ),
        LocationState(
            id="loc_porto",
            name="Port de Médard",
            exits=["Thrusher Manor"],
        ),
    ]
    clues = [
        RuntimeClue(
            id="clue_pendant",
            label="Pendente gioiellato",
            type="physical_evidence",
            source_location="Thrusher Manor",
            possible_actions=["Esaminare il pendente trovato dai coccodrilli"],
        ),
        RuntimeClue(
            id="clue_dagger",
            label="Pugnale nascosto",
            type="physical_evidence",
            source_location="Port de Médard",
            possible_actions=["Confrontare Ysabeau col pugnale trovato al porto"],
        ),
        RuntimeClue(
            id="clue_global",
            label="Sussurri sul Conte",
            type="testimony",
            source_location="",  # global
            possible_actions=["Raccogliere voci sul Conte tra gli abitanti"],
        ),
    ]
    actors = [
        ActorState(
            id="actor_ysabeau",
            name="Ysabeau Dupont",
            role="rival",
            location_id="Port de Médard",
            goal="nascondere il pugnale",
        ),
        ActorState(
            id="actor_blackwell",
            name="Blackwell",
            role="ally",
            location_id="Thrusher Manor",
            goal="aiutare la squadra",
        ),
    ]
    return AdventureDefinition(
        id="adv_thrusher",
        title="Thrusher Manor",
        locations=locations,
        clues=clues,
        actors=actors,
    )


class ActionGenerationTests(unittest.TestCase):

    def test_uses_llm_possible_actions_not_template(self):
        """Le etichette delle azioni vengono da possible_actions[0], non da template."""
        defn = _thrusher_manor_definition()
        actions = actions_for_scene(None, defn, "Thrusher Manor")
        labels = [a["label"] for a in actions]
        # Il label LLM deve essere presente
        self.assertIn("Esaminare il pendente trovato dai coccodrilli", labels)
        # Il vecchio template NON deve apparire
        self.assertFalse(
            any("Cercare" in l and "a " in l for l in labels),
            f"Template 'Cercare X a Y' trovato nelle azioni: {labels}",
        )

    def test_filters_clues_by_location(self):
        """Solo indizi della scena corrente appaiono nelle azioni."""
        defn = _thrusher_manor_definition()
        actions = actions_for_scene(None, defn, "Thrusher Manor")
        target_ids = {a["target_id"] for a in actions if a["kind"] == "clue"}
        # pendant è a Thrusher Manor → presente
        self.assertIn("clue_pendant", target_ids)
        # dagger è al Porto → assente
        self.assertNotIn("clue_dagger", target_ids)

    def test_global_clue_appears_in_all_scenes(self):
        """Un indizio con source_location vuota è visibile ovunque."""
        defn = _thrusher_manor_definition()
        for scene in ("Thrusher Manor", "Port de Médard"):
            with self.subTest(scene=scene):
                actions = actions_for_scene(None, defn, scene)
                ids = {a["target_id"] for a in actions if a["kind"] == "clue"}
                self.assertIn("clue_global", ids)

    def test_actors_filtered_by_location(self):
        """Solo gli attori presenti nella scena appaiono come azioni."""
        defn = _thrusher_manor_definition()
        manor_actions = actions_for_scene(None, defn, "Thrusher Manor")
        manor_actors = {a["target_id"] for a in manor_actions if a["kind"] == "actor"}
        self.assertIn("actor_blackwell", manor_actors)
        self.assertNotIn("actor_ysabeau", manor_actors)

        porto_actions = actions_for_scene(None, defn, "Port de Médard")
        porto_actors = {a["target_id"] for a in porto_actions if a["kind"] == "actor"}
        self.assertIn("actor_ysabeau", porto_actors)
        self.assertNotIn("actor_blackwell", porto_actors)

    def test_move_actions_from_exits(self):
        """Le uscite della location generano azioni di movimento."""
        defn = _thrusher_manor_definition()
        actions = actions_for_scene(None, defn, "Thrusher Manor")
        move_labels = [a["label"] for a in actions if a["kind"] == "move"]
        self.assertTrue(
            any("Port de Médard" in l for l in move_labels),
            f"Nessuna azione di movimento verso Porto: {move_labels}",
        )

    def test_discovered_clues_skipped(self):
        """Gli indizi già scoperti non appaiono nelle azioni."""
        defn = _thrusher_manor_definition()
        defn.clues[0].state = "discovered"  # pendant scoperto
        actions = actions_for_scene(None, defn, "Thrusher Manor")
        ids = {a["target_id"] for a in actions if a["kind"] == "clue"}
        self.assertNotIn("clue_pendant", ids)

    def test_fallback_explore_when_empty(self):
        """Con nessun indizio/attore/uscita, compare 'Esplora attivamente'."""
        defn = AdventureDefinition(
            id="empty",
            locations=[LocationState(id="loc_void", name="Sala Vuota")],
        )
        actions = actions_for_scene(None, defn, "loc_void")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "explore")
        self.assertIn("Sala Vuota", actions[0]["label"])

    def test_skill_hints_present(self):
        """Ogni azione ha un skill_hint (può essere None per move)."""
        defn = _thrusher_manor_definition()
        actions = actions_for_scene(None, defn, "Thrusher Manor")
        for a in actions:
            self.assertIn("skill_hint", a, f"Manca skill_hint in {a}")


if __name__ == "__main__":
    unittest.main()
