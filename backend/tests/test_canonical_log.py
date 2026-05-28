"""T7 — Canonical event log consistency tests

Coverage:
- _extract_canonical_events: converte state_updates in eventi canonici
- Tutti i tipi di evento (clue_revealed, clue_partial, npc_state, thread_closed, fact, clock_triggered)
- director_prompt_context include le ultime 10 voci del log come FATTI GIÀ STABILITI
- Con più di 10 voci, solo le ultime 10 appaiono nel prompt
- Con log vuoto, nessuna sezione FATTI nel prompt
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tests.conftest  # noqa: F401 — installs stubs before App imports

from App.claude_service import _extract_canonical_events
from App.narrative_director import director_prompt_context


class TestExtractCanonicalEvents(unittest.TestCase):
    def test_clue_found_produces_clue_revealed(self):
        events = _extract_canonical_events({"clues_found": ["c1", "c2"]}, turn=3)
        types = [e["type"] for e in events]
        self.assertEqual(types.count("clue_revealed"), 2)
        ids = [e["clue_id"] for e in events]
        self.assertIn("c1", ids)
        self.assertIn("c2", ids)

    def test_clue_revealed_event_has_correct_turn(self):
        events = _extract_canonical_events({"clues_found": ["c1"]}, turn=7)
        self.assertEqual(events[0]["turn"], 7)

    def test_clue_partial_progress(self):
        su = {"clue_progress": [{"clue_id": "c3", "progress": 1}]}
        events = _extract_canonical_events(su, turn=2)
        partial = [e for e in events if e["type"] == "clue_partial"]
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0]["clue_id"], "c3")

    def test_npc_terminal_status_logged(self):
        for status in ("dead", "captured", "exposed", "resolved"):
            with self.subTest(status=status):
                su = {"npc_updates": [{"id": "npc_1", "name": "Aldric", "status": status}]}
                events = _extract_canonical_events(su, turn=5)
                npc_events = [e for e in events if e["type"] == "npc_state"]
                self.assertEqual(len(npc_events), 1)
                self.assertEqual(npc_events[0]["status"], status)

    def test_npc_non_terminal_status_not_logged(self):
        su = {"npc_updates": [{"id": "npc_1", "name": "Aldric", "status": "available"}]}
        events = _extract_canonical_events(su, turn=5)
        npc_events = [e for e in events if e["type"] == "npc_state"]
        self.assertEqual(len(npc_events), 0)

    def test_thread_closed_logged(self):
        su = {"closed_threads": ["thread_1", "thread_2"]}
        events = _extract_canonical_events(su, turn=8)
        closed = [e for e in events if e["type"] == "thread_closed"]
        self.assertEqual(len(closed), 2)
        thread_ids = [e["thread_id"] for e in closed]
        self.assertIn("thread_1", thread_ids)

    def test_discovered_fact_logged(self):
        su = {"discovered_facts": [{"text": "Il bibliotecario era complice."}]}
        events = _extract_canonical_events(su, turn=4)
        facts = [e for e in events if e["type"] == "fact"]
        self.assertEqual(len(facts), 1)
        self.assertIn("bibliotecario", facts[0]["text"])

    def test_clock_trigger_logged(self):
        su = {"clock_triggers": [{"id": "clock_1", "label": "Prove distrutte"}]}
        events = _extract_canonical_events(su, turn=6)
        clock_events = [e for e in events if e["type"] == "clock_triggered"]
        self.assertEqual(len(clock_events), 1)
        self.assertEqual(clock_events[0]["clock_id"], "clock_1")

    def test_empty_state_updates_returns_empty(self):
        events = _extract_canonical_events({}, turn=1)
        self.assertEqual(events, [])

    def test_same_turn_multiple_event_types(self):
        su = {
            "clues_found": ["c1"],
            "closed_threads": ["t1"],
            "discovered_facts": [{"text": "Un fatto importante."}],
        }
        events = _extract_canonical_events(su, turn=10)
        types = {e["type"] for e in events}
        self.assertIn("clue_revealed", types)
        self.assertIn("thread_closed", types)
        self.assertIn("fact", types)
        self.assertTrue(all(e["turn"] == 10 for e in events))


class TestDirectorPromptCanonicalLog(unittest.TestCase):
    def _make_log(self, n: int) -> list[dict]:
        return [{"turn": i, "type": "clue_revealed", "clue_id": f"c{i}"} for i in range(1, n + 1)]

    def test_empty_log_produces_no_fatti_section(self):
        prompt = director_prompt_context({}, canonical_log=[])
        self.assertNotIn("FATTI", prompt)

    def test_none_log_produces_no_fatti_section(self):
        prompt = director_prompt_context({}, canonical_log=None)
        self.assertNotIn("FATTI", prompt)

    def test_log_entries_appear_in_prompt(self):
        log = [{"turn": 3, "type": "clue_revealed", "clue_id": "chiave_rossa"}]
        prompt = director_prompt_context({}, canonical_log=log)
        self.assertIn("FATTI", prompt)
        self.assertIn("chiave_rossa", prompt)

    def test_fact_entry_text_appears_in_prompt(self):
        log = [{"turn": 2, "type": "fact", "text": "Il sindaco era corrotto."}]
        prompt = director_prompt_context({}, canonical_log=log)
        self.assertIn("Il sindaco era corrotto.", prompt)

    def test_only_last_10_entries_shown(self):
        # 15 entries: only last 10 (c6..c15) should appear
        log = self._make_log(15)
        prompt = director_prompt_context({}, canonical_log=log)
        # c1..c5 should NOT appear
        for i in range(1, 6):
            self.assertNotIn(f"c{i}]", prompt, f"c{i} dovrebbe essere fuori dalla finestra di 10")
        # c6..c15 SHOULD appear
        for i in range(6, 16):
            self.assertIn(f"c{i}]", prompt, f"c{i} dovrebbe apparire nella finestra di 10")

    def test_exactly_10_entries_all_shown(self):
        log = self._make_log(10)
        prompt = director_prompt_context({}, canonical_log=log)
        for i in range(1, 11):
            self.assertIn(f"c{i}]", prompt)

    def test_npc_state_event_appears_in_prompt(self):
        log = [{"turn": 5, "type": "npc_state", "npc_id": "npc_1", "npc_name": "Ferrara", "status": "dead"}]
        prompt = director_prompt_context({}, canonical_log=log)
        self.assertIn("Ferrara", prompt)

    def test_thread_closed_event_appears_in_prompt(self):
        log = [{"turn": 8, "type": "thread_closed", "thread_id": "chi_ha_rubato"}]
        prompt = director_prompt_context({}, canonical_log=log)
        self.assertIn("chi_ha_rubato", prompt)


if __name__ == "__main__":
    unittest.main()
