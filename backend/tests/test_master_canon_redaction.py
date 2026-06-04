"""Verifica del gate anti-spoiler della verità canonica nel prompt del Master.

`runtime_prompt_context` iniettava la verità centrale (core_truth / hidden_truths)
a ogni turno senza gating: il Master la conosceva e la raccontava dal primo turno.
Ora la mostra solo quando il chiamante lo autorizza (reveal_canon=True, cioè thread
pronti a dedurre o tempo agli sgoccioli).
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App.adventure_runtime import build_adventure_runtime, runtime_prompt_context  # noqa: E402

_SECRET = "VROSS HA ORCHESTRATO IL GENOCIDIO DELIBERATAMENTE"


def _runtime():
    adv = {
        "title": "Veyra", "genre": "sci_fi",
        "premise": "Una stazione silenziosa.",
        "hidden_truth": _SECRET,
        "clues": [], "story_threads": [], "revelations": [],
        "locations": [], "actors": [],
    }
    return build_adventure_runtime(adv, {})


class TestCanonRedaction(unittest.TestCase):
    def test_truth_redacted_by_default(self):
        out = runtime_prompt_context(_runtime(), reveal_canon=False)
        self.assertNotIn(_SECRET, out)
        self.assertIn("RISERVATO", out)

    def test_truth_revealed_when_authorized(self):
        out = runtime_prompt_context(_runtime(), reveal_canon=True)
        self.assertIn(_SECRET, out)

    def test_default_is_redacted(self):
        # il default del parametro deve essere "non rivelare" (fail-safe)
        out = runtime_prompt_context(_runtime())
        self.assertNotIn(_SECRET, out)


if __name__ == "__main__":
    unittest.main()
