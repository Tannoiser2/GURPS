"""Verifica fix #2: gli indizi nascono già "a tre dimensioni".

Ogni indizio deve avere payoff + hidden_implication + wrong_interpretations, sia
dal prompt LLM di generazione sia dal builder skeleton di fallback, così
l'enrichment AI del doctor (`_enrich_clues`, la chiamata più costosa) non scatta
per un contenuto che andrebbe prodotto a monte.
"""
import sys
import unittest
from unittest.mock import MagicMock

# Stub delle dipendenze API pesanti prima di importare claude_service.
for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App import claude_service as cs  # noqa: E402
from App.adventure_compiler import definition_from_compiler_json  # noqa: E402
from App.adventure_doctor import _clue_rules  # noqa: E402
from App.runtime_shape_builder import build_shape_for_ai_generated  # noqa: E402


class TestClueGenerationFields(unittest.TestCase):
    def test_generation_prompt_requests_the_three_levels(self):
        scale = cs._COMPLEXITY_SCALES["standard"]
        template_key = next(iter(cs._STRUCTURAL_TEMPLATES))
        archetype = {
            "name": "Indagine", "structure": "graph",
            "threat": "minaccia", "clue_focus": "prove",
        }
        prompt = cs._build_create_adventure_prompt(
            "fantasy", "4 PG", archetype, template_key, scale
        )
        self.assertIn("hidden_implication", prompt)
        self.assertIn("wrong_interpretations", prompt)
        self.assertIn("REGOLE INDIZI", prompt)

    def test_skeleton_builder_produces_complete_clues(self):
        shape = build_shape_for_ai_generated(
            "Una stazione orbitale in crisi", {"primary_archetype": "investigation_graph"},
            title="Test", genre_hint="sci-fi",
        )
        for clue in shape["clues"]:
            self.assertTrue(clue.get("payoff"))
            self.assertTrue(clue.get("hidden_implication"))
            self.assertTrue(clue.get("wrong_interpretations"))

    def test_complete_clue_passes_audit(self):
        clue = {
            "id": "c1", "label": "X", "text": "t", "thread_id": "T1",
            "payoff": "p", "hidden_implication": "h", "wrong_interpretations": ["a", "b"],
        }
        self.assertEqual(_clue_rules([clue], {"T1"}), [])

    def test_incomplete_clue_is_flagged(self):
        clue = {"id": "c2", "label": "Y", "text": "t", "thread_id": "T1", "payoff": "p"}
        findings = _clue_rules([clue], {"T1"})
        self.assertEqual(len(findings), 2)  # hidden_implication + wrong_interpretations

    def test_compiler_preserves_clue_depth(self):
        raw = {
            "source_mode": "ai_generated", "title": "T", "genre": "fantasy",
            "premise": "p",
            "clues": [{
                "id": "clue_1", "label": "Lettera", "text": "una lettera",
                "thread_id": "T1", "payoff": "sblocca X",
                "hidden_implication": "in realtà incolpa Y",
                "wrong_interpretations": ["sembra accusare Z", "pare un falso"],
            }],
            "story_threads": [{"id": "T1", "title": "t", "question": "chi?", "true_answer": "Y"}],
        }
        defn = definition_from_compiler_json(raw, source_type="manual_json", title="T")
        clue = next(c for c in defn.clues if c.id == "clue_1")
        self.assertEqual(clue.hidden_implication, "in realtà incolpa Y")
        self.assertEqual(list(clue.wrong_interpretations), ["sembra accusare Z", "pare un falso"])


if __name__ == "__main__":
    unittest.main()
