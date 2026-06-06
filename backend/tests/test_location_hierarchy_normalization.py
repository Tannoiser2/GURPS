"""Normalizzazione gerarchia mappa nel compilatore (AI + PDF).

Bug: location con parent_location_id verso un genitore mai emesso (es.
"quartieri" citati ma non creati) sparivano dalla mappa strategica; inoltre
map_x/map_y a 0 facevano accatastare i pin. La normalizzazione in
definition_from_compiler_json riporta gli orfani a root e assegna coordinate.
"""
import unittest

from App.adventure_compiler import definition_from_compiler_json


def _raw_with_orphans():
    return {
        "title": "Test",
        "locations": [
            {"id": "loc_a", "name": "Ufficio", "location_type": "local",
             "parent_location_id": "loc_quartiere_fantasma"},
            {"id": "loc_b", "name": "Baracca", "location_type": "local",
             "parent_location_id": "loc_quartiere_fantasma"},
            {"id": "loc_c", "name": "Magazzino", "location_type": "local",
             "parent_location_id": "loc_altro_fantasma"},
        ],
    }


class TestLocationHierarchyNormalization(unittest.TestCase):
    def test_orphans_reparented_to_root(self):
        d = definition_from_compiler_json(_raw_with_orphans(), source_type="manual_json")
        for loc in d.locations:
            # nessun parent deve puntare a un id inesistente
            if loc.parent_location_id:
                self.assertIn(loc.parent_location_id, {l.id for l in d.locations})
        # tutte e 3 erano orfane → ora root
        self.assertTrue(all(loc.parent_location_id == "" for loc in d.locations))

    def test_root_locations_get_distinct_coordinates(self):
        d = definition_from_compiler_json(_raw_with_orphans(), source_type="manual_json")
        coords = [(loc.map_x, loc.map_y) for loc in d.locations]
        # nessuna a (0,0) e tutte distinte → niente accatastamento al centro
        self.assertTrue(all(x or y for x, y in coords), coords)
        self.assertEqual(len(set(coords)), len(coords), coords)

    def test_valid_parent_preserved(self):
        raw = {
            "title": "Test",
            "locations": [
                {"id": "area_1", "name": "Regione", "location_type": "strategic",
                 "parent_location_id": ""},
                {"id": "loc_x", "name": "Città", "location_type": "regional",
                 "parent_location_id": "area_1"},
            ],
        }
        d = definition_from_compiler_json(raw, source_type="manual_json")
        child = next(l for l in d.locations if l.id == "loc_x")
        self.assertEqual(child.parent_location_id, "area_1")  # genitore valido intatto


if __name__ == "__main__":
    unittest.main()
