"""T5 — Equipment coherence tests

Coverage:
- validate_gear_for_genre: weapon/item era mismatch warnings
- assign_starter_items: archetype + genre filtering
- starter_item_names: Italian name resolution
"""

import unittest

from App.equipment_coherence import (
    validate_gear_for_genre,
    assign_starter_items,
    starter_item_names,
)


class TestValidateGearForGenre(unittest.TestCase):

    def test_mitra_in_fantasy_produces_warning(self):
        """A modern SMG is not coherent with a fantasy genre."""
        warnings = validate_gear_for_genre(["mitra"], "fantasy")
        self.assertTrue(len(warnings) > 0, "Expected a warning for mitra in fantasy")
        self.assertTrue(any("mitra" in w.lower() or "Mitra" in w for w in warnings))

    def test_pistola_in_fantasy_produces_warning(self):
        """Modern handgun is not coherent with fantasy."""
        warnings = validate_gear_for_genre(["pistola 9mm"], "fantasy")
        self.assertTrue(len(warnings) > 0)

    def test_spada_in_fantasy_no_warning(self):
        """A medieval sword is compatible with fantasy."""
        warnings = validate_gear_for_genre(["spada lunga"], "fantasy")
        self.assertEqual(warnings, [], f"Unexpected warnings: {warnings}")

    def test_kit_medico_in_any_genre_no_warning(self):
        """Medical kit is universal (eras=[]) → no warning in any genre."""
        for genre in ["fantasy", "sci_fi", "horror", "medievale", "ww2"]:
            with self.subTest(genre=genre):
                warnings = validate_gear_for_genre(["kit medico"], genre)
                self.assertEqual(warnings, [], f"Unexpected warning for kit_medico in {genre}")

    def test_cotta_maglia_in_sci_fi_produces_warning(self):
        """Chain mail is medieval, not coherent with sci-fi."""
        warnings = validate_gear_for_genre(["cotta di maglia"], "sci_fi")
        self.assertTrue(len(warnings) > 0, "Expected a warning for cotta_maglia in sci_fi")

    def test_cotta_maglia_in_fantasy_no_warning(self):
        """Chain mail is explicitly tagged with 'fantasy' era."""
        warnings = validate_gear_for_genre(["cotta di maglia"], "fantasy")
        self.assertEqual(warnings, [], f"Unexpected warning: {warnings}")

    def test_giubbotto_tattico_in_fantasy_produces_warning(self):
        """Tactical vest (modern/scifi eras) is not coherent with fantasy."""
        warnings = validate_gear_for_genre(["giubbotto tattico"], "fantasy")
        self.assertTrue(len(warnings) > 0)

    def test_giubbotto_tattico_in_sci_fi_no_warning(self):
        """Tactical vest is compatible with sci_fi."""
        warnings = validate_gear_for_genre(["giubbotto tattico"], "sci_fi")
        self.assertEqual(warnings, [], f"Unexpected warning: {warnings}")

    def test_unknown_item_no_warning(self):
        """Unrecognized item names silently pass (no false alarms)."""
        warnings = validate_gear_for_genre(["oggetto_inventato_xyz"], "fantasy")
        self.assertEqual(warnings, [])

    def test_unknown_genre_no_warning(self):
        """Unknown genre → era_set is empty → nothing flagged."""
        warnings = validate_gear_for_genre(["mitra"], "genere_inesistente")
        self.assertEqual(warnings, [])

    def test_multiple_items_mixed(self):
        """Correct items don't get flagged alongside incoherent ones."""
        warnings = validate_gear_for_genre(["spada lunga", "mitra", "kit medico"], "fantasy")
        # Only mitra should warn
        self.assertEqual(len(warnings), 1)
        self.assertTrue(any("mitra" in w.lower() or "Mitra" in w for w in warnings))


class TestAssignStarterItems(unittest.TestCase):

    def test_warrior_fantasy_includes_cotta_maglia(self):
        """Warrior archetype in fantasy gets chain mail (era-compatible)."""
        ids = assign_starter_items("warrior", "fantasy")
        self.assertIn("cotta_maglia", ids)

    def test_marine_fantasy_excludes_giubbotto_tattico(self):
        """Marine's tactical vest is modern — filtered out for fantasy genre."""
        ids = assign_starter_items("marine", "fantasy")
        self.assertNotIn("giubbotto_tattico", ids)

    def test_marine_sci_fi_includes_giubbotto_tattico(self):
        """Marine in sci_fi genre keeps the tactical vest."""
        ids = assign_starter_items("marine", "sci_fi")
        self.assertIn("giubbotto_tattico", ids)

    def test_kit_medico_always_present(self):
        """kit_medico is in every genre base kit (universal)."""
        for genre in ["fantasy", "sci_fi", "horror", "medievale"]:
            with self.subTest(genre=genre):
                ids = assign_starter_items("warrior", genre)
                self.assertIn("kit_medico", ids)

    def test_no_duplicates(self):
        """Returned list has no duplicate item IDs."""
        for archetype in ["warrior", "marine", "mage", "detective"]:
            for genre in ["fantasy", "sci_fi"]:
                with self.subTest(archetype=archetype, genre=genre):
                    ids = assign_starter_items(archetype, genre)
                    self.assertEqual(len(ids), len(set(ids)), f"Duplicates in {archetype}/{genre}: {ids}")


class TestStarterItemNames(unittest.TestCase):

    def test_returns_italian_names(self):
        """starter_item_names returns human-readable Italian names."""
        names = starter_item_names("warrior", "fantasy")
        self.assertTrue(len(names) > 0)
        # All results should be non-empty strings (not raw IDs)
        for name in names:
            self.assertIsInstance(name, str)
            self.assertTrue(len(name) > 0)

    def test_warrior_fantasy_has_cotta_di_maglia_name(self):
        names = starter_item_names("warrior", "fantasy")
        self.assertIn("Cotta di maglia", names)

    def test_marine_fantasy_no_giubbotto_in_names(self):
        names = starter_item_names("marine", "fantasy")
        self.assertNotIn("Giubbotto tattico", names)


if __name__ == "__main__":
    unittest.main()
