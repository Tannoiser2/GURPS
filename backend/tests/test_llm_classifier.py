import os
import unittest
from unittest.mock import patch

from App import llm_classifier
from App.adventure_compiler import compile_pdf_to_runtime


class LlmClassifierGuardTests(unittest.TestCase):
    def test_disabled_by_default_returns_none(self):
        # Even with an API key in the env, the classifier must stay no-op
        # unless GURPS_ENABLE_LLM_CLASSIFIER is set.
        os.environ.pop("GURPS_ENABLE_LLM_CLASSIFIER", None)
        self.assertIsNone(
            llm_classifier.classify_adventure_metadata("some adventure text", source_cards=[], title="X")
        )

    def test_returns_none_when_opted_in_but_no_provider(self):
        with patch.dict(os.environ, {"GURPS_ENABLE_LLM_CLASSIFIER": "1"}):
            with patch("App.claude_service._text_provider_available", return_value=False):
                self.assertIsNone(
                    llm_classifier.classify_adventure_metadata("text", source_cards=[], title="X")
                )


class LlmClassifierMergeTests(unittest.TestCase):
    """When the classifier returns a result, the compile path must use it to
    override genre and archetype. We simulate a Gotham-39-style case: an urban
    noir investigation that the heuristic mislabels as wilderness_sandbox.
    """

    def setUp(self):
        super().setUp()
        # Keep the other LLM extractors offline so we only exercise the
        # classifier here. Without these stubs the compile path would fire
        # real Claude calls when the dev shell exports the opt-in env vars.
        for target in (
            "App.adventure_compiler.extract_clues_with_llm",
            "App.adventure_compiler.enrich_actors_with_llm",
            "App.adventure_compiler.build_deduction_graph_with_llm",
            "App.adventure_compiler.synthesize_narrative_with_llm",
        ):
            p = patch(target, return_value=None)
            p.start()
            self.addCleanup(p.stop)

    def test_llm_metadata_overrides_heuristic_archetype(self):
        fake_llm = {
            "genre": "detective_classico",
            "primary_archetype": "noir_investigation",
            "secondary_archetypes": ["investigation_graph"],
            "tone": "noir urbano",
            "confidence": 0.85,
            "reason": "Indagine urbana con fotografie compromettenti.",
            "source": "llm",
        }
        text = "\n".join([
            "Adventure Summary: indagine nella Gotham del 1939.",
            "Sezione A: deposito sul porto.",
            "Indizio: fotografia compromettente del Penny Plunderer.",
            "Indizio: documenti del sindacato dei docker.",
            "Fazione: gang del porto",
            "PNG: William Tockman, avvocato corrotto",
        ])
        with patch(
            "App.adventure_compiler.classify_adventure_metadata",
            return_value=fake_llm,
        ):
            compiled = compile_pdf_to_runtime(text, title="Gotham", genre_hint=None)
        definition = compiled["adventure_definition"]
        self.assertEqual(definition.archetype_profile["primary_archetype"], "noir_investigation")
        self.assertEqual(definition.archetype_profile["source"], "llm")
        self.assertEqual(definition.genre, "detective_classico")
        self.assertIn("llm_metadata", definition.archetype_profile)

    def test_explicit_genre_hint_is_not_overridden(self):
        fake_llm = {
            "genre": "fantasy",
            "primary_archetype": "investigation_graph",
            "secondary_archetypes": [],
            "tone": "",
            "confidence": 0.9,
            "reason": "test",
            "source": "llm",
        }
        text = "\n".join([
            "Adventure summary.",
            "Indizio: prova fisica numero 1",
            "Indizio: prova fisica numero 2",
        ])
        with patch(
            "App.adventure_compiler.classify_adventure_metadata",
            return_value=fake_llm,
        ):
            compiled = compile_pdf_to_runtime(text, title="Test", genre_hint="ww2")
        # The user-supplied genre_hint must win even if the LLM proposes
        # something else.
        self.assertEqual(compiled["adventure_definition"].genre, "ww2")


if __name__ == "__main__":
    unittest.main()
