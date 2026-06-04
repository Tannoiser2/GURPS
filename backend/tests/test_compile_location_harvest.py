"""Verifica del fix "location orfane" nel compiler delle avventure AI.

Bug: il modello produce attori ricchi (ognuno in un luogo con nome reale) ma
lascia vuoto l'array ``locations``. Il compiler ripiegava su placeholder
generici (loc_ai_N), orfanando ogni riferimento ``actor.location_id``.

Fix: ``_harvest_referenced_locations`` materializza le location dai nomi che
attori/indizi già citano, e il resolver in ``definition_from_compiler_json``
mappa i riferimenti (per id, nome o slug) all'id reale.
"""
import unittest

from App.adventure_compiler import (
    _harvest_referenced_locations,
    definition_from_compiler_json,
)


def _ai_raw(**over):
    raw = {
        "source_mode": "ai_generated",
        "title": "Stazione in crisi",
        "genre": "sci-fi",
        "premise": "Una stazione orbitale sull'orlo del collasso.",
        "actors": [
            {"id": "npc_1", "name": "Cap. Reeves", "location_id": "Sala operativa principale"},
            {"id": "npc_2", "name": "Dr. Osei", "location_id": "Infermeria centrale"},
            {"id": "npc_3", "name": "Jax Keller", "location": "Deposito armi", "location_id": ""},
        ],
        "clues": [
            {"id": "c1", "label": "Log di sistema", "source_location": "Sala server", "text": "..."},
        ],
    }
    raw.update(over)
    return raw


class TestLocationHarvest(unittest.TestCase):
    def test_actors_no_longer_orphaned(self):
        """Senza array locations, gli attori atterrano comunque su location reali."""
        defn = definition_from_compiler_json(
            _ai_raw(), source_type="manual_json", title="Stazione in crisi"
        )
        loc_ids = {l.id for l in defn.locations}
        orphans = [a for a in defn.actors if a.location_id and a.location_id not in loc_ids]
        self.assertEqual(orphans, [], f"attori orfani residui: {[a.name for a in orphans]}")

    def test_real_location_names_materialized(self):
        """Le location create portano i NOMI reali citati, non placeholder generici."""
        defn = definition_from_compiler_json(
            _ai_raw(), source_type="manual_json", title="Stazione in crisi"
        )
        names = {l.name for l in defn.locations}
        self.assertIn("Sala operativa principale", names)
        self.assertIn("Infermeria centrale", names)
        self.assertNotIn("Apertura", names)  # niente seed-scheletro generico

    def test_harvest_skips_machine_ids(self):
        """Gli id-macchina (loc_ai_N, actor_x, ...) non diventano location."""
        harvested = _harvest_referenced_locations({
            "actors": [
                {"id": "a1", "location_id": "loc_ai_2"},
                {"id": "a2", "location_id": "section_3"},
                {"id": "a3", "location_id": "Biblioteca segreta"},
            ],
        })
        names = {l["name"] for l in harvested}
        self.assertEqual(names, {"Biblioteca segreta"})

    def test_existing_real_locations_not_overridden(self):
        """Se il raw ha già location reali, l'harvest non le sostituisce."""
        raw = _ai_raw(locations=[
            {"id": "loc_ponte", "name": "Ponte di comando"},
            {"id": "loc_hangar", "name": "Hangar"},
            {"id": "loc_mensa", "name": "Mensa"},
            {"id": "loc_motori", "name": "Sala motori"},
        ])
        defn = definition_from_compiler_json(
            raw, source_type="manual_json", title="Stazione in crisi"
        )
        names = {l.name for l in defn.locations}
        self.assertIn("Ponte di comando", names)
        self.assertIn("Hangar", names)

    def test_resolver_maps_name_reference_to_id(self):
        """Un attore che cita una location per NOME viene mappato al suo id reale."""
        raw = _ai_raw(
            actors=[{"id": "npc_1", "name": "Custode", "location_id": "Archivio centrale"}],
            locations=[
                {"name": "Archivio centrale"},
                {"name": "Atrio"},
                {"name": "Cripta"},
                {"name": "Torre"},
            ],
        )
        defn = definition_from_compiler_json(
            raw, source_type="manual_json", title="Stazione in crisi"
        )
        archivio = next(l for l in defn.locations if l.name == "Archivio centrale")
        custode = next(a for a in defn.actors if a.name == "Custode")
        self.assertEqual(custode.location_id, archivio.id)


if __name__ == "__main__":
    unittest.main()
