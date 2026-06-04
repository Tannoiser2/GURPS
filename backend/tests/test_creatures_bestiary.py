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


if __name__ == "__main__":
    unittest.main()
