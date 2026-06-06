"""Verifica del bestiario per incontri casuali (data_creatures)."""
import random
import sys
import unittest
from unittest.mock import MagicMock

for _m in ("anthropic", "openai", "google", "google.genai", "google.auth"):
    sys.modules.setdefault(_m, MagicMock())

from App.data_creatures import (  # noqa: E402
    CREATURE_TABLE, creature_to_entity_dict, creatures_for_genre,
    random_encounter_for,
)
from App.models import SceneEntity  # noqa: E402


class TestBestiary(unittest.TestCase):
    def test_genre_filters_by_era(self):
        fantasy = {c["id"] for c in creatures_for_genre("fantasy")}
        self.assertIn("goblin", fantasy)
        self.assertNotIn("drone_sicurezza", fantasy)  # sci-fi non in fantasy

        scifi = {c["id"] for c in creatures_for_genre("sci_fi")}
        self.assertIn("drone_sicurezza", scifi)
        self.assertNotIn("goblin", scifi)

    def test_genre_normalization(self):
        a = {c["id"] for c in creatures_for_genre("Sci-Fi")}
        b = {c["id"] for c in creatures_for_genre("sci_fi")}
        self.assertEqual(a, b)

    def test_max_threat_filter(self):
        easy = creatures_for_genre("fantasy", max_threat=1)
        self.assertTrue(all(c["threat"] <= 1 for c in easy))

    def test_random_encounter_returns_valid(self):
        c = random_encounter_for("horror", rng=random.Random(0))
        self.assertIsNotNone(c)
        self.assertIn(c["id"], {x["id"] for x in CREATURE_TABLE})

    def test_unknown_genre_defaults_modern(self):
        # genere sconosciuto → ere modern → almeno una creatura moderna
        self.assertTrue(creatures_for_genre("genere_inesistente"))

    def test_maps_to_scene_entity(self):
        c = random_encounter_for("fantasy", rng=random.Random(1))
        kwargs = creature_to_entity_dict(c, entity_id="enemy_1")
        ent = SceneEntity(**kwargs)  # non deve sollevare
        self.assertEqual(ent.type, "enemy")
        self.assertGreater(ent.hp, 0)
        self.assertEqual(ent.hp, ent.max_hp)
        self.assertIn("nemico", ent.tags)

    def test_every_creature_has_required_stats(self):
        for c in CREATURE_TABLE:
            for field in ("id", "name", "eras", "threat", "hp", "attack_skill", "damage_dice"):
                self.assertIn(field, c, f"{c.get('id')} manca {field}")

    # ── Coerenza ambientale (habitat) ────────────────────────────────────────
    def test_no_shark_in_mountains(self):
        names = {c["name"] for c in creatures_for_genre("modern", environment="alta montagna rocciosa")}
        self.assertNotIn("Squalo", names)
        self.assertNotIn("Coccodrillo", names)

    def test_shark_allowed_at_sea(self):
        names = {c["name"] for c in creatures_for_genre("modern", environment="fondale marino, scogliera sul mare")}
        self.assertIn("Squalo", names)
        self.assertNotIn("Orso", names)  # bestia di terra esclusa in mare

    def test_wilderness_beast_excluded_indoors(self):
        names = {c["name"] for c in creatures_for_genre("modern", environment="interno di un magazzino")}
        self.assertNotIn("Orso", names)
        self.assertNotIn("Lupo", names)

    def test_ubiquitous_creature_passes_any_environment(self):
        # Le creature senza habitat (zombie, non-morti, macchine) sono ubique.
        for env in ("alta montagna", "fondale marino", "interno stazione spaziale"):
            ids = {c["id"] for c in creatures_for_genre("horror", environment=env)}
            self.assertTrue(ids, f"pool vuoto per {env}")

    def test_unknown_environment_no_filter(self):
        full = creatures_for_genre("modern")
        same = creatures_for_genre("modern", environment="luogo indefinito qualunque")
        self.assertEqual({c["id"] for c in full}, {c["id"] for c in same})

    def test_environment_never_empties_pool(self):
        # Anche un ambiente estremo non deve mai azzerare il pool (fallback).
        for genre in ("fantasy", "sci_fi", "horror", "western", "modern"):
            for env in ("fondale abissale", "vetta innevata", "deserto arido", "interno bunker"):
                self.assertTrue(
                    creatures_for_genre(genre, environment=env),
                    f"pool vuoto: {genre} / {env}",
                )


if __name__ == "__main__":
    unittest.main()
