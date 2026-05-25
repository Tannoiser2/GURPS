import unittest

from App.pdf_cleanup import clean_pdf_pages, clean_pdf_text
from App.pdf_structure_extractor import extract_npc_blocks


class PdfCleanupTests(unittest.TestCase):
    def test_strips_inline_eg_parenthetical(self):
        text = (
            "The penguin holds compromising photographs "
            "(e.g., the photograph of him with another woman gal goods off a trawler) "
            "and uses them as leverage."
        )
        cleaned = clean_pdf_text(text)
        self.assertNotIn("e.g.", cleaned.lower())
        self.assertNotIn("trawler", cleaned)
        self.assertIn("compromising photographs", cleaned)
        self.assertIn("leverage", cleaned)

    def test_strips_multiline_eg_parenthetical(self):
        text = (
            "Possible leads include\n"
            "(e.g., the photograph of him with another woman\n"
            "gal goods off a trawler, the Penny Plunderer,\n"
            "off the docks in Gotham\n"
            "\n"
            "Next paragraph stays."
        )
        cleaned = clean_pdf_text(text)
        self.assertNotIn("Plunderer", cleaned)
        self.assertIn("Next paragraph stays", cleaned)

    def test_dehyphenates_word_break(self):
        self.assertIn("dungeon", clean_pdf_text("dun-\ngeon"))

    def test_drops_running_header(self):
        pages = [
            f"Gotham by Gaslight\n{i}\nActual content for page {i}."
            for i in range(1, 6)
        ]
        cleaned = clean_pdf_pages(pages)
        for page in cleaned:
            self.assertNotIn("Gotham by Gaslight", page)
            self.assertIn("Actual content", page)

    def test_idempotent_on_clean_input(self):
        text = "Clean prose with no artifacts."
        self.assertEqual(clean_pdf_text(clean_pdf_text(text)), clean_pdf_text(text))

    def test_collapses_doubled_letter_tokens(self):
        # pdfplumber stroked-text artifact
        text = "TThheeyy ffrroomm tthhee CCoommeett are HHaattcchheedd."
        cleaned = clean_pdf_text(text)
        self.assertIn("They from the Comet", cleaned)
        self.assertIn("Hatched", cleaned)
        self.assertNotIn("HHaattcchheedd", cleaned)

    def test_preserves_normal_double_letters(self):
        # Words like "letter", "look", "off" must survive unchanged.
        text = "The book looks off in the letter."
        cleaned = clean_pdf_text(text)
        self.assertIn("book", cleaned)
        self.assertIn("looks", cleaned)
        self.assertIn("letter", cleaned)


class GurpsActorDescriptionTests(unittest.TestCase):
    def test_npc_description_uses_preceding_paragraph_not_stat_block(self):
        text = (
            "William Tockman is a cunning lawyer with terminal illness who turns to crime "
            "to provide for his sister. He plans clockwork-themed robberies across Gotham.\n"
            "\n"
            "WILLIAM TOCKMAN\n"
            "ST 10; DX 11; IQ 13; HT 10\n"
            "Basic Speed 5.25; Move 5; Dodge 8\n"
        )
        blocks = extract_npc_blocks(text)
        self.assertTrue(blocks, "expected a GURPS actor block to be extracted")
        tockman = next((b for b in blocks if "TOCKMAN" in b["label"]), None)
        self.assertIsNotNone(tockman)
        self.assertIn("cunning lawyer", tockman["text"])
        self.assertNotIn("Basic Speed", tockman["text"])
        self.assertNotIn("ST 10", tockman["text"])


if __name__ == "__main__":
    unittest.main()
