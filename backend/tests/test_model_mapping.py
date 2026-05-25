import unittest

from App.adventure_compiler import compile_pdf_to_runtime
from App.runtime_models import AdventureDefinition, AdventureRuntimeState


class ModelMappingUnpackTests(unittest.TestCase):
    """Repro del bug:
        TypeError: AdventureDefinition() argument after ** must be a mapping,
        not AdventureDefinition
    `main.py` chiama ``AdventureDefinition(**compiled["adventure_definition"])``
    sull'oggetto gia istanziato dal compiler. Senza ``keys`` / ``__getitem__``
    sul model, Pydantic v2 rifiuta l'unpacking.
    """

    def test_can_unpack_adventure_definition(self):
        text = "1. Stanza A con porta.\nIndizio: chiave"
        compiled = compile_pdf_to_runtime(text, title="Unpack", genre_hint="fantasy")
        definition_obj = compiled["adventure_definition"]
        # Funziona sia con un model che con un dict — il client puo usare il
        # pattern ``AdventureDefinition(**compiled["adventure_definition"])``
        # senza preoccuparsi del tipo restituito.
        rebuilt = AdventureDefinition(**definition_obj)
        self.assertEqual(rebuilt.id, definition_obj.id)
        self.assertEqual(rebuilt.title, definition_obj.title)
        self.assertEqual(len(rebuilt.locations), len(definition_obj.locations))

    def test_can_unpack_runtime_state(self):
        text = "1. Stanza A.\nIndizio: chiave"
        compiled = compile_pdf_to_runtime(text, title="Unpack", genre_hint="fantasy")
        state_obj = compiled["runtime_state"]
        rebuilt = AdventureRuntimeState(**state_obj)
        self.assertEqual(rebuilt.definition_id, state_obj.definition_id)


if __name__ == "__main__":
    unittest.main()
