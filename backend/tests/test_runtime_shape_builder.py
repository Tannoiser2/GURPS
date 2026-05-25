import unittest

from App.archetype_detector import detect_archetypes_from_pdf_structure
from App.pdf_structure_extractor import extract_pdf_structure
from App.preservation_policy import build_preservation_policy
from App.runtime_shape_builder import build_shape_for_pdf_import


class RuntimeShapeBuilderTests(unittest.TestCase):
    def test_pdf_shape_preserves_room_count(self):
        text = "\n".join(f"{i}. Sala {i}" for i in range(1, 12))
        structure = extract_pdf_structure(text)
        profile = detect_archetypes_from_pdf_structure("pdf_import", structure, "fantasy")
        policy = build_preservation_policy("pdf_import", structure, profile)
        raw = build_shape_for_pdf_import(text, structure, profile, policy, title="Shape")

        self.assertEqual(len(raw["locations"]), 11)
        self.assertTrue(raw["preservation_policy"]["forbid_structural_compression"])
        self.assertEqual(len(raw["original_structure_map"]["room_ids"]), 11)


if __name__ == "__main__":
    unittest.main()
