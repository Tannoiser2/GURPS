import unittest

from App.adventure_compiler import compile_pdf_to_runtime


class PdfStructurePreservationTests(unittest.TestCase):
    def test_pdf_dungeon_with_10_rooms_preserves_10_locations(self):
        text = "\n".join(f"{i}. Stanza {i} con porta, rischio e dettaglio." for i in range(1, 11))
        compiled = compile_pdf_to_runtime(text, title="Dungeon Test", genre_hint="fantasy")
        definition = compiled["adventure_definition"]

        self.assertEqual(definition.source_mode, "pdf_import")
        self.assertGreaterEqual(len(definition.locations), 10)
        self.assertTrue(all(l.is_preserved_from_pdf for l in definition.locations[:10]))
        self.assertEqual(definition.archetype_profile["primary_archetype"], "room_keyed_dungeon")

    def test_pdf_investigation_with_8_clues_preserves_8_clues(self):
        text = "\n".join(f"Indizio: prova fisica numero {i}" for i in range(1, 9))
        compiled = compile_pdf_to_runtime(text, title="Indagine Test", genre_hint="detective_classico")
        definition = compiled["adventure_definition"]

        self.assertGreaterEqual(len(definition.clues), 8)
        self.assertTrue(all(c.is_preserved_from_pdf for c in definition.clues[:8]))
        self.assertTrue(all(c.source_status == "explicit" for c in definition.clues[:8]))

    def test_pdf_sandbox_with_3_factions_preserves_3_factions(self):
        text = "\n".join([
            "Fazione: Casata Rossa controlla il porto",
            "Fazione: Gilda Bianca compra testimoni",
            "Fazione: Clan Nero protegge il passo",
        ])
        compiled = compile_pdf_to_runtime(text, title="Sandbox Test", genre_hint="fantasy")
        definition = compiled["adventure_definition"]

        self.assertGreaterEqual(len(definition.factions), 3)
        self.assertTrue(all(f.source_status == "explicit" for f in definition.factions[:3]))

    def test_pdf_without_clock_does_not_receive_mandatory_clock(self):
        text = "\n".join(f"{i}. Stanza {i} tranquilla." for i in range(1, 5))
        compiled = compile_pdf_to_runtime(text, title="No Clock", genre_hint="fantasy")
        definition = compiled["adventure_definition"]
        report = compiled["validation_report"]

        self.assertEqual(len(definition.event_clocks), 0)
        self.assertTrue(any("senza clock" in s.lower() for s in report.get("suggestions", [])))

    def test_source_refs_present_on_preserved_elements(self):
        text = "1. Ingresso della Torre\nIndizio: chiave spezzata sotto il tappeto"
        compiled = compile_pdf_to_runtime(text, title="Source Ref", genre_hint="fantasy")
        definition = compiled["adventure_definition"]

        self.assertTrue(definition.locations[0].source_ref.get("snippet_hash"))
        self.assertTrue(definition.clues[0].source_ref.get("snippet_hash"))


if __name__ == "__main__":
    unittest.main()
