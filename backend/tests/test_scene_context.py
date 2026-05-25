import unittest

from App.runtime_models import (
    ActorState,
    AdventureDefinition,
    AdventureRuntimeState,
    LocationState,
    RuntimeClue,
)
from App.scene_context import (
    actions_for_scene,
    current_location,
    present_actors_at,
    visible_clues_at,
)


def _build_definition() -> AdventureDefinition:
    locations = [
        LocationState(id="loc_porto", name="Port de Médard", exits=["Thrusher Manor"]),
        LocationState(id="loc_manor", name="Thrusher Manor", exits=["Port de Médard"]),
        LocationState(id="loc_gaming", name="Gaming Parlor"),
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
            source_location="Gaming Parlor",
            possible_actions=["Confrontare Ysabeau col pugnale"],
        ),
        RuntimeClue(
            id="clue_global",
            label="Sussurri sul Conte",
            type="testimony",
            source_location="",  # global -> visibile ovunque
        ),
        RuntimeClue(
            id="clue_port",
            label="Registri del porto",
            type="document",
            source_location="Port de Médard",
        ),
    ]
    actors = [
        ActorState(id="actor_ysabeau", name="Ysabeau Dupont", role="rival", location_id="Gaming Parlor", goal="nascondere il pugnale"),
        ActorState(id="actor_blackwell", name="Blackwell", role="ally", location_id="loc_porto"),
        ActorState(id="actor_montmorency", name="Montmorency", role="patron", location_id=""),
    ]
    return AdventureDefinition(
        id="adv_test",
        title="Thrusher Manor test",
        locations=locations,
        clues=clues,
        actors=actors,
    )


class SceneContextVisibilityTests(unittest.TestCase):
    def test_visible_clues_filtered_by_scene_name(self):
        definition = _build_definition()
        clues = visible_clues_at(None, definition, scene_id="Thrusher Manor")
        ids = {c.id for c in clues}
        self.assertIn("clue_pendant", ids)
        self.assertIn("clue_global", ids)  # global clue always shown
        self.assertNotIn("clue_dagger", ids)
        self.assertNotIn("clue_port", ids)

    def test_visible_clues_use_current_scene_id_from_runtime(self):
        definition = _build_definition()
        runtime = AdventureRuntimeState(definition_id="adv_test", current_scene_id="Port de Médard")
        clues = visible_clues_at(runtime, definition)
        ids = {c.id for c in clues}
        self.assertIn("clue_port", ids)
        self.assertIn("clue_global", ids)
        self.assertNotIn("clue_pendant", ids)

    def test_visible_clues_tolerant_prefix_match(self):
        definition = _build_definition()
        # Simulate an LLM-tagged clue with a wider name than the canonical
        # location id — caso reale Lupo di Kosmar.
        definition.clues.append(RuntimeClue(
            id="clue_torre",
            label="Pelli di lupo",
            source_location="Torre - Stanza 4",
        ))
        definition.locations.append(LocationState(id="loc_stanza4", name="Stanza 4"))
        clues = visible_clues_at(None, definition, scene_id="Stanza 4")
        self.assertIn("clue_torre", {c.id for c in clues})

    def test_present_actors_filtered_by_scene(self):
        definition = _build_definition()
        actors = present_actors_at(None, definition, scene_id="Gaming Parlor")
        self.assertEqual({a.id for a in actors}, {"actor_ysabeau"})
        actors = present_actors_at(None, definition, scene_id="loc_porto")
        self.assertEqual({a.id for a in actors}, {"actor_blackwell"})

    def test_present_actors_excludes_offstage(self):
        definition = _build_definition()
        actors = present_actors_at(None, definition, scene_id="Thrusher Manor")
        self.assertEqual(actors, [])  # nessuno a Thrusher Manor

    def test_current_location_resolves_by_id_or_name(self):
        definition = _build_definition()
        self.assertEqual(current_location(definition, "loc_porto").id, "loc_porto")
        self.assertEqual(current_location(definition, "Thrusher Manor").id, "loc_manor")
        self.assertIsNone(current_location(definition, "Nonexistent"))


class SceneContextActionTests(unittest.TestCase):
    def test_actions_use_llm_possible_actions_verbatim(self):
        definition = _build_definition()
        actions = actions_for_scene(None, definition, scene_id="Thrusher Manor")
        labels = [a["label"] for a in actions]
        self.assertIn("Esaminare il pendente trovato dai coccodrilli", labels)
        # NO "Cercare X a Thrusher Manor" template noise
        self.assertFalse(any(l.startswith("Cercare ") for l in labels))

    def test_actions_include_present_actors(self):
        definition = _build_definition()
        actions = actions_for_scene(None, definition, scene_id="Gaming Parlor")
        labels = [a["label"] for a in actions]
        self.assertTrue(any("Avvicinare Ysabeau" in l for l in labels))

    def test_actions_include_exit_movement(self):
        definition = _build_definition()
        actions = actions_for_scene(None, definition, scene_id="Port de Médard")
        kinds = {a["kind"] for a in actions}
        self.assertIn("move", kinds)
        labels = [a["label"] for a in actions]
        self.assertTrue(any("Spostarsi verso Thrusher Manor" in l for l in labels))

    def test_actions_fallback_when_scene_empty(self):
        # A location with no clues, actors or exits should still produce a
        # non-empty action list so the player never sees a dead scene.
        definition = AdventureDefinition(
            id="empty",
            locations=[LocationState(id="loc_empty", name="Empty Hall")],
        )
        actions = actions_for_scene(None, definition, scene_id="loc_empty")
        self.assertEqual(len(actions), 1)
        self.assertIn("Esplora attivamente Empty Hall", actions[0]["label"])

    def test_actions_skip_discovered_clues(self):
        definition = _build_definition()
        definition.clues[0].state = "discovered"
        actions = actions_for_scene(None, definition, scene_id="Thrusher Manor")
        labels = [a["label"] for a in actions]
        # the discovered clue must not be re-offered
        self.assertFalse(any("pendente" in l.lower() for l in labels))


if __name__ == "__main__":
    unittest.main()
