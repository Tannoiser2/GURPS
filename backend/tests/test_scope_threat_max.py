"""Verifica del doom-clock proporzionale alla scala dell'avventura.

Un'avventura epica (molti indizi/thread) non deve condividere lo stesso fuso di
una scena breve, altrimenti scade in sconfitta prima che l'indagine sia
completabile (caso reale: "Il Silenzio di Veyra-9", 18 indizi, finita al turno 19).
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App.claude_service import _scope_threat_max  # noqa: E402


def _adv(n_clues, n_threads, threat_max=None):
    a = {"clues": [{"id": f"c{i}"} for i in range(n_clues)],
         "story_threads": [{"id": f"T{i}"} for i in range(n_threads)]}
    if threat_max is not None:
        a["threat_max_turns"] = threat_max
    return a


class TestScopeThreatMax(unittest.TestCase):
    def test_short_adventure_stays_tense(self):
        # poche prove → fuso al floor (resta teso)
        self.assertEqual(_scope_threat_max(_adv(5, 2)), 8)

    def test_epic_gets_longer_fuse(self):
        # 18 indizi + 5 thread → fuso ampio, non più 8
        self.assertEqual(_scope_threat_max(_adv(18, 5)), 20)
        self.assertGreater(_scope_threat_max(_adv(18, 5)), 8)

    def test_unset_threat_max_uses_scope(self):
        # caso Veyra-9: threat_max_turns assente → non più il default 8
        self.assertEqual(_scope_threat_max(_adv(18, 5, threat_max=None)), 20)

    def test_explicit_low_value_is_raised(self):
        # un valore esplicito troppo stretto viene alzato alla stima di scala
        self.assertEqual(_scope_threat_max(_adv(18, 5, threat_max=8)), 20)

    def test_explicit_high_value_is_respected(self):
        # se il designer ha messo un fuso più lungo, lo rispettiamo
        self.assertEqual(_scope_threat_max(_adv(5, 2, threat_max=30)), 30)


if __name__ == "__main__":
    unittest.main()
