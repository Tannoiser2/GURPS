"""T6 — Character creation end-to-end tests

Coverage:
- validate_draft: stat fuori range, budget overflow, troppi svantaggi
- Derivate GURPS: basic_speed = (agilita + empatia) / 4, move = int(basic_speed)
- build_custom_player: auto-assegna item se non specificati
- build_custom_player: mantiene item espliciti
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tests.conftest  # noqa: F401 — installs stubs before App imports

from App.character_creation import validate_draft, build_custom_player
from App.models import CharacterDraft


def _draft(**kwargs) -> CharacterDraft:
    """Crea un CharacterDraft con stat base valide; sovrascrivibile via kwargs."""
    defaults = dict(
        name="Test",
        role="warrior",
        archetype="warrior",
        genre="fantasy",
        stats={"forza": 10, "agilita": 10, "intelligenza": 10, "empatia": 10},
    )
    defaults.update(kwargs)
    return CharacterDraft(**defaults)


class TestValidateDraftStats(unittest.TestCase):
    def test_stat_below_minimum_is_error(self):
        result = validate_draft(_draft(stats={"forza": 5, "agilita": 10, "intelligenza": 10, "empatia": 10}))
        self.assertFalse(result.valid)
        self.assertTrue(any("forza" in e for e in result.errors))

    def test_stat_above_maximum_is_error(self):
        result = validate_draft(_draft(stats={"forza": 17, "agilita": 10, "intelligenza": 10, "empatia": 10}))
        self.assertFalse(result.valid)
        self.assertTrue(any("forza" in e for e in result.errors))

    def test_stat_at_minimum_is_valid(self):
        result = validate_draft(_draft(stats={"forza": 6, "agilita": 6, "intelligenza": 6, "empatia": 6}))
        # Stat valide ma molti punti risparmiati → solo warning, no stat-errors
        stat_errors = [e for e in result.errors if "sotto il minimo" in e or "sopra il massimo" in e]
        self.assertEqual(stat_errors, [])

    def test_stat_at_maximum_is_valid(self):
        result = validate_draft(_draft(stats={"forza": 16, "agilita": 10, "intelligenza": 10, "empatia": 10}))
        # forza 16 = +60pt, within budget 100 — no stat range error
        stat_errors = [e for e in result.errors if "sopra il massimo" in e]
        self.assertEqual(stat_errors, [])


class TestValidateDraftBudget(unittest.TestCase):
    def test_budget_overflow_is_error(self):
        # agilita 15 = +100pt, forza 12 = +20pt → totale 120pt > 100
        result = validate_draft(_draft(stats={"forza": 12, "agilita": 15, "intelligenza": 10, "empatia": 10}))
        self.assertFalse(result.valid)
        self.assertTrue(any("punti" in e.lower() or "budget" in e.lower() for e in result.errors))

    def test_budget_exact_is_valid(self):
        # agilita 15 = +100pt soli, tutto il resto a 10
        result = validate_draft(_draft(stats={"forza": 10, "agilita": 15, "intelligenza": 10, "empatia": 10}))
        budget_errors = [e for e in result.errors if "punti" in e.lower() or "budget" in e.lower()]
        self.assertEqual(budget_errors, [])

    def test_under_budget_gives_warning_not_error(self):
        # Tutti a 10 → 0 pt spesi, 100 rimasti → warning
        result = validate_draft(_draft())
        self.assertTrue(result.valid)
        self.assertTrue(any("non spesi" in w or "sottopotenziato" in w for w in result.warnings))


class TestValidateDraftDisadvantages(unittest.TestCase):
    def test_too_many_disadvantages_is_error(self):
        # "Vista Imperfetta Non Correggibile" costa -25,
        # "Senso del Dovere (Ogni Vivente)" costa -20 → totale -45 < -40
        disadvs = ["Vista Imperfetta Non Correggibile", "Senso del Dovere (Ogni Vivente)"]
        result = validate_draft(_draft(disadvantages=disadvs))
        self.assertFalse(result.valid)
        self.assertTrue(any("svantag" in e.lower() or "limite" in e.lower() for e in result.errors))

    def test_disadvantages_within_limit_is_ok(self):
        # "Avidità" costa -15 solo → dentro il limite -40
        result = validate_draft(_draft(disadvantages=["Avidità"]))
        disadv_errors = [e for e in result.errors if "svantag" in e.lower() and "limite" in e.lower()]
        self.assertEqual(disadv_errors, [])


class TestDerivedStats(unittest.TestCase):
    def test_basic_speed_formula(self):
        # basic_speed = (agilita + empatia) / 4
        result = validate_draft(_draft(stats={"forza": 10, "agilita": 12, "intelligenza": 10, "empatia": 10}))
        self.assertAlmostEqual(result.basic_speed, (12 + 10) / 4.0)

    def test_move_is_floor_of_basic_speed(self):
        # agilita=12, empatia=10 → basic_speed=5.5 → move=5
        result = validate_draft(_draft(stats={"forza": 10, "agilita": 12, "intelligenza": 10, "empatia": 10}))
        self.assertEqual(result.move, int((12 + 10) / 4.0))

    def test_max_hp_equals_forza(self):
        result = validate_draft(_draft(stats={"forza": 12, "agilita": 10, "intelligenza": 10, "empatia": 10}))
        self.assertEqual(result.max_hp, 12)

    def test_max_fp_equals_empatia(self):
        result = validate_draft(_draft(stats={"forza": 10, "agilita": 10, "intelligenza": 10, "empatia": 13}))
        self.assertEqual(result.max_fp, 13)

    def test_will_equals_intelligenza(self):
        result = validate_draft(_draft(stats={"forza": 10, "agilita": 10, "intelligenza": 11, "empatia": 10}))
        self.assertEqual(result.will, 11)


class TestBuildCustomPlayer(unittest.TestCase):
    def test_auto_assigns_items_when_none_specified(self):
        d = _draft(archetype="warrior", genre="fantasy", items=[])
        player = build_custom_player(d)
        self.assertGreater(len(player.items), 0, "dovrebbe auto-assegnare item per warrior/fantasy")

    def test_keeps_explicit_items(self):
        d = _draft(archetype="warrior", genre="fantasy", items=["spada_lunga"])
        player = build_custom_player(d)
        item_ids = [i if isinstance(i, str) else (i.get("id") or i.get("name") or "") for i in player.items]
        self.assertIn("spada_lunga", item_ids)

    def test_player_has_correct_name(self):
        d = _draft(name="Aldric")
        player = build_custom_player(d)
        self.assertEqual(player.name, "Aldric")

    def test_player_derived_stats_populated(self):
        d = _draft(stats={"forza": 10, "agilita": 12, "intelligenza": 10, "empatia": 10})
        player = build_custom_player(d)
        self.assertIsNotNone(player.basic_speed)
        self.assertGreater(player.move, 0)


if __name__ == "__main__":
    unittest.main()
