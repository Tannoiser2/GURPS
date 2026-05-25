import unittest

from App.archetype_detector import detect_archetypes_from_ai_prompt, detect_archetypes_from_pdf_structure
from App.pdf_structure_extractor import extract_pdf_structure


class ArchetypeDetectorTests(unittest.TestCase):
    def test_pdf_room_keys_are_labeled_not_compressed(self):
        text = "\n".join(f"{i}. Camera {i}" for i in range(1, 7))
        structure = extract_pdf_structure(text)
        profile = detect_archetypes_from_pdf_structure("pdf_import", structure, "fantasy")

        self.assertEqual(profile["primary_archetype"], "room_keyed_dungeon")
        self.assertEqual(profile["structure_authority"], "label_only_do_not_compress")

    def test_ai_prompt_detects_heist_without_pdf_policy(self):
        profile = detect_archetypes_from_ai_prompt("Un colpo heist con sicurezza, heat e fuga dall'hangar", "action")
        self.assertEqual(profile["primary_archetype"], "heist")


if __name__ == "__main__":
    unittest.main()
