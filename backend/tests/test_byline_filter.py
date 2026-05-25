import unittest

from App.pdf_structure_extractor import extract_pdf_sections


class BylineFilterTests(unittest.TestCase):
    def test_drops_byline_section(self):
        text = "By J.C. Connors\nThe Comet adventure begins on a windy night."
        sections = extract_pdf_sections(text)
        titles = [s["title"] for s in sections]
        self.assertFalse(any(t.lower().startswith("by j.c.") for t in titles))

    def test_drops_uppercase_byline_heading(self):
        text = "ADVENTURE BY CONNORS\nThe scene opens in the woods."
        sections = extract_pdf_sections(text)
        titles = [s["title"] for s in sections]
        self.assertFalse(any("BY CONNORS" in t for t in titles))

    def test_preserves_real_section_headings(self):
        text = "The Garage\nA disused workshop full of tools."
        sections = extract_pdf_sections(text)
        titles = [s["title"] for s in sections]
        self.assertTrue(any("Garage" in t for t in titles))


if __name__ == "__main__":
    unittest.main()
