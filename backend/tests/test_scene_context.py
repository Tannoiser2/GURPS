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
    present_or_anchored_opening_actors,
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


class OpeningActorAnchoringTests(unittest.TestCase):
    def _prison(self):
        return AdventureDefinition(
            id="adv_prison", title="Prigione",
            locations=[LocationState(id="cella_1", name="Cella")],
            actors=[
                ActorState(id="marta", name="Marta", role="ally", location_id=""),
                ActorState(id="gurk", name="Gurk", role="antagonist", location_id=""),
                ActorState(id="pale", name="Pale", role="neutral", location_id="sala_consiglio"),
            ],
        )

    def test_borrows_only_nonhostile_locationless_actor(self):
        d = self._prison()
        present = present_or_anchored_opening_actors(d)
        # Marta (ally, senza location) viene ancorata; Gurk (antagonista) no;
        # Pale è collocato altrove e non viene tirato in cella.
        self.assertEqual([a.name for a in present], ["Marta"])
        self.assertEqual(d.actors[0].location_id, "cella_1")  # ancorata
        self.assertEqual(d.actors[1].location_id, "")          # villain off-stage

    def test_opening_actors_are_present_in_play(self):
        # Regressione: nessun PNG fantasma — chi è nell'apertura deve esserci in gioco.
        d = self._prison()
        present = present_or_anchored_opening_actors(d)
        rt = AdventureRuntimeState(definition_id=d.id, current_scene_id="cella_1")
        in_play = {a.name for a in present_actors_at(rt, d, "cella_1")}
        for actor in present:
            self.assertIn(actor.name, in_play)
        self.assertNotIn("Gurk", in_play)

    def test_no_anchoring_when_scene_already_populated(self):
        d = AdventureDefinition(
            id="a2", title="t",
            locations=[LocationState(id="hall", name="Hall")],
            actors=[
                ActorState(id="x", name="Cleo", role="witness", location_id="hall"),
                ActorState(id="v", name="Boss", role="villain", location_id=""),
            ],
        )
        present = present_or_anchored_opening_actors(d)
        self.assertEqual([a.name for a in present], ["Cleo"])
        self.assertEqual(d.actors[1].location_id, "")  # villain non ancorato


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
