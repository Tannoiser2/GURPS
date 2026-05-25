"""Verifica F3a + F3c: la progressione clue rispetta l'outcome del tiro.

- successo critico / successo pieno -> clues_found e clue_progress applicati
- successo parziale -> clues_found demoted a clue_progress
- fallimento / fallimento critico -> nessuna progressione, solo costo narrativo
"""
import unittest

from App.engine import apply_story_updates
from App.models import (
    CanonClue,
    GameState,
    StoryState,
    StoryThread,
    TeamSetupState,
)


def _state_with_thread() -> GameState:
    thread = StoryThread(
        id="T1",
        question="Chi ha ucciso Murgahd?",
        required_clues=2,
        minimum_clues_to_deduce=2,
    )
    clue_a = CanonClue(id="clue_a", thread_id="T1", label="Pendente gioiellato")
    clue_b = CanonClue(id="clue_b", thread_id="T1", label="Pugnale nascosto")
    story = StoryState(
        threads=[thread],
        canonical_clues=[clue_a, clue_b],
    )
    return GameState(
        turn=1,
        log="",
        team_setup=TeamSetupState(),
        story=story,
    )


def _thread(state: GameState) -> StoryThread:
    return state.story.threads[0]


class FailureBlocksProgressionTests(unittest.TestCase):
    def test_fallimento_does_not_advance_clue_found(self):
        state = _state_with_thread()
        updates = {"clues_found": ["clue_a"]}
        apply_story_updates(state, updates, outcome="fallimento")
        clue = next(c for c in state.story.canonical_clues if c.id == "clue_a")
        self.assertFalse(clue.is_discovered)
        self.assertNotIn("clue_a", _thread(state).collected_clue_ids)

    def test_fallimento_does_not_advance_clue_progress(self):
        state = _state_with_thread()
        updates = {"clue_progress": [{"clue_id": "clue_a", "note": "tracce vaghe"}]}
        apply_story_updates(state, updates, outcome="fallimento")
        self.assertNotIn("clue_a", _thread(state).partial_clues)

    def test_fallimento_critico_does_not_advance(self):
        state = _state_with_thread()
        updates = {"clues_found": ["clue_a"], "clue_progress": [{"clue_id": "clue_b"}]}
        apply_story_updates(state, updates, outcome="fallimento critico")
        clue = next(c for c in state.story.canonical_clues if c.id == "clue_a")
        self.assertFalse(clue.is_discovered)
        self.assertNotIn("clue_b", _thread(state).partial_clues)

    def test_fallimento_drops_clue_for_thread_facts(self):
        state = _state_with_thread()
        updates = {"discovered_facts": [{"text": "fatto", "clue_for_thread": "T1"}]}
        apply_story_updates(state, updates, outcome="fallimento")
        self.assertNotIn("fatto", _thread(state).collected_clue_ids)


class PartialSuccessDemotesTests(unittest.TestCase):
    def test_partial_success_demotes_found_to_progress(self):
        state = _state_with_thread()
        updates = {"clues_found": ["clue_a"]}
        apply_story_updates(state, updates, outcome="successo parziale")
        clue = next(c for c in state.story.canonical_clues if c.id == "clue_a")
        # clue NOT fully discovered
        self.assertFalse(clue.is_discovered)
        self.assertNotIn("clue_a", _thread(state).collected_clue_ids)
        # but progress IS recorded
        self.assertIn("clue_a", _thread(state).partial_clues)

    def test_partial_keeps_existing_clue_progress(self):
        state = _state_with_thread()
        updates = {
            "clues_found": ["clue_a"],
            "clue_progress": [{"clue_id": "clue_b", "note": "indizio gia in corso"}],
        }
        apply_story_updates(state, updates, outcome="successo parziale")
        partials = _thread(state).partial_clues
        self.assertIn("clue_a", partials)
        self.assertIn("clue_b", partials)


class FullSuccessAcceptsTests(unittest.TestCase):
    def test_successo_pieno_marks_clue_discovered(self):
        state = _state_with_thread()
        updates = {"clues_found": ["clue_a"]}
        apply_story_updates(state, updates, outcome="successo pieno")
        clue = next(c for c in state.story.canonical_clues if c.id == "clue_a")
        self.assertTrue(clue.is_discovered)
        self.assertIn("clue_a", _thread(state).collected_clue_ids)

    def test_successo_critico_marks_clue_discovered(self):
        state = _state_with_thread()
        updates = {"clues_found": ["clue_b"]}
        apply_story_updates(state, updates, outcome="critico")
        clue = next(c for c in state.story.canonical_clues if c.id == "clue_b")
        self.assertTrue(clue.is_discovered)

    def test_default_outcome_keeps_backward_compat(self):
        # Old callers that don't pass `outcome` keep working as "successo pieno".
        state = _state_with_thread()
        apply_story_updates(state, {"clues_found": ["clue_a"]})
        clue = next(c for c in state.story.canonical_clues if c.id == "clue_a")
        self.assertTrue(clue.is_discovered)


if __name__ == "__main__":
    unittest.main()
