"""Verifica che il doctor parallelo raccolga e applichi tutti gli arricchimenti.

Le chiamate AI di enrichment (hook, clocks, clues, locations, NPC) girano in
parallelo: questo test stubba le funzioni di enrichment con marcatori
deterministici e controlla che ``run_doctor(do_enrich=True)`` applichi ciascun
risultato al campo giusto — cioè che la raccolta dei future sia corretta.
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

import App.adventure_doctor as doc  # noqa: E402


def _definition():
    return {
        "title": "Stazione", "genre": "sci-fi", "premise": "p" * 60,
        # niente initial_hook -> job hook
        "actors": [{"id": "a1", "name": "Reeves"}],  # magro -> finding npc
        "clues": [{"id": "c1", "label": "Log", "text": "t", "thread_id": "T1", "payoff": "p"}],
        "story_threads": [{"id": "T1", "title": "t", "question": "chi?", "true_answer": "a",
                            "required_clues": ["c1"]}],
        "event_clocks": [{"id": "ck1", "label": "Conto alla rovescia"}],  # incompleto -> finding clock
        "locations": [{"id": f"l{i}", "name": f"L{i}"} for i in range(6)],  # >=5 senza parent
    }


class TestDoctorParallelEnrich(unittest.TestCase):
    def setUp(self):
        # Stub deterministici delle chiamate AI.
        self._orig = {name: getattr(doc, name) for name in (
            "_enrich_structure_balance", "_enrich_initial_hook", "_enrich_npc",
            "_enrich_clocks", "_enrich_clues", "_enrich_location_hierarchy",
            "_enrich_locations",
        )}
        doc._enrich_structure_balance = lambda enriched, findings: enriched
        doc._enrich_initial_hook = lambda enriched: "HOOK_OK"
        doc._enrich_npc = lambda a, ctx: {**a, "_enriched": True}
        doc._enrich_clocks = lambda clocks, ctx: [{**c, "_enriched": True} for c in clocks]
        doc._enrich_clues = lambda clues, ctx: [
            {**c, "hidden_implication": "h", "wrong_interpretations": ["a", "b"]} for c in clues
        ]
        doc._enrich_location_hierarchy = lambda locs, ctx: [{**l, "_hier": True} for l in locs]
        doc._enrich_locations = lambda locs, ctx: [{**l, "_enriched": True} for l in locs]

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(doc, name, fn)

    def test_all_enrichments_applied(self):
        res = doc.run_doctor(_definition(), do_enrich=True)
        enr = res["enriched_definition"]
        self.assertIsNotNone(enr)
        # ogni job parallelo ha scritto il proprio campo
        self.assertEqual(enr["initial_hook"], "HOOK_OK")
        self.assertTrue(all(a.get("_enriched") for a in enr["actors"]))
        self.assertTrue(all(c.get("_enriched") for c in enr["event_clocks"]))
        self.assertTrue(all(c.get("hidden_implication") for c in enr["clues"]))
        self.assertTrue(all(l.get("_enriched") for l in enr["locations"]))
        self.assertTrue(all(l.get("_hier") for l in enr["locations"]))
        self.assertIsInstance(res["score_after"], float)

    def test_audit_only_does_not_enrich(self):
        res = doc.run_doctor(_definition(), do_enrich=False)
        self.assertIsNone(res["enriched_definition"])
        self.assertIn("findings", res)


if __name__ == "__main__":
    unittest.main()
