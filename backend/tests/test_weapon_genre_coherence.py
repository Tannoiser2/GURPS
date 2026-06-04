"""Verifica dei fix su armi/genere.

Bug segnalati: "la pistola 9mm è sempre lì" (anche in fantasy) e "il caricamento
di armi fallisce sempre" (western). Cause: genere non normalizzato/non passato →
fallback ERA_MODERN → pistola_9mm; e typo "colt_45" (id inesistente) → arma non
caricata.
"""
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App.data_weapons import default_weapon_for_archetype, WEAPON_BY_ID  # noqa: E402


class TestWeaponGenreCoherence(unittest.TestCase):
    def test_fantasy_does_not_get_9mm(self):
        wid, _ = default_weapon_for_archetype("detective", "fantasy")
        self.assertNotEqual(wid, "pistola_9mm")
        self.assertIn(wid, WEAPON_BY_ID)  # arma reale, non fantasma

    def test_western_loads_a_valid_weapon(self):
        # prima ritornava "colt_45" (id inesistente) → arma non caricata
        wid, _ = default_weapon_for_archetype("gunslinger", "western")
        self.assertEqual(wid, "colt45")
        self.assertIn(wid, WEAPON_BY_ID)

    def test_western_fallback_id_is_valid(self):
        wid, _ = default_weapon_for_archetype("archetipo_ignoto", "western")
        self.assertIsNotNone(WEAPON_BY_ID.get(wid), f"{wid} non nel catalogo")

    def test_genre_normalization_avoids_modern_default(self):
        # "Sci-Fi" (trattino/maiuscole) deve mappare su sci_fi → blaster, non 9mm
        wid, _ = default_weapon_for_archetype("detective", "Sci-Fi")
        self.assertNotEqual(wid, "pistola_9mm")
        self.assertIn(wid, WEAPON_BY_ID)

    def test_no_fallback_returns_phantom_id(self):
        for genre in ("fantasy", "western", "sci_fi", "horror", "steampunk",
                      "action", "cyberpunk", "post_apocalypse"):
            wid, _ = default_weapon_for_archetype("zzz_sconosciuto", genre)
            if wid:
                self.assertIn(wid, WEAPON_BY_ID, f"{genre} → {wid!r} non esiste nel catalogo")


if __name__ == "__main__":
    unittest.main()
