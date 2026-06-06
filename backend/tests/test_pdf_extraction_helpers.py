"""Test per gli helper di estrazione PDF: titolo, qualità text-layer, colonne."""
import unittest

from App.main import (
    _choose_pdf_title,
    _looks_like_garbled_title,
    _pdf_text_quality,
    _detect_column_gutter,
    _ocr_available,
    _ocr_page_text,
    _pdf_source_warning,
)


class TitleChoiceTests(unittest.TestCase):
    def test_garbled_cover_prefers_filename(self):
        # 'TIA MOD' è la versione mis-spaziata di 'Ti Amo da' dalla copertina
        self.assertEqual(
            _choose_pdf_title("TIA MOD", "Ti_Amo_da_morire.pdf"),
            "Ti Amo da morire",
        )

    def test_truncated_extract_prefers_filename(self):
        # estratto = prefisso del filename despaziato
        self.assertEqual(
            _choose_pdf_title("Il Richiamo delle", "il-richiamo-delle-ossa-bianche.pdf"),
            "il richiamo delle ossa bianche",
        )

    def test_good_extracted_title_kept(self):
        # titolo pulito e NON contenuto nel filename → si tiene l'estratto
        self.assertEqual(
            _choose_pdf_title("La Maschera di Ferro", "scan_042.pdf"),
            "La Maschera di Ferro",
        )

    def test_symbol_garbled_falls_back(self):
        self.assertEqual(
            _choose_pdf_title("TIA MlO> AM", "avventura_segreta.pdf"),
            "avventura segreta",
        )

    def test_no_extract_uses_filename(self):
        self.assertEqual(_choose_pdf_title("", "Mia_Avventura.pdf"), "Mia Avventura")


class GarbledTitleTests(unittest.TestCase):
    def test_detects_symbols(self):
        self.assertTrue(_looks_like_garbled_title("TIA MlO> AM"))

    def test_detects_single_letter_words(self):
        self.assertTrue(_looks_like_garbled_title("A B C D"))

    def test_detects_inner_caps(self):
        self.assertTrue(_looks_like_garbled_title("intCl Ha"))

    def test_clean_title_passes(self):
        self.assertFalse(_looks_like_garbled_title("The Haunting"))
        self.assertFalse(_looks_like_garbled_title("La Casa sul Lago"))


class TextQualityTests(unittest.TestCase):
    def test_clean_text_high_score(self):
        clean = (
            "L'investigatore privato riceve una lettera dalla sua amica d'infanzia. "
            "Chicago nel febbraio del 1929 è divisa tra polizia corrotta e mafia locale. "
            "Il detective deve scoprire la verità prima che qualcuno venga ucciso. "
        ) * 6
        q = _pdf_text_quality(clean)
        self.assertGreaterEqual(q["score"], 90)

    def test_garbled_text_low_score(self):
        garbled = (
            "EUens i ç sempre intCl putcri gioca1ore scmhrn relazlcne dò "
            "poli7,ior mihwical difftrenzad cre:u·.iond pets0m1ggiod "
        ) * 6
        q = _pdf_text_quality(garbled)
        self.assertLess(q["score"], 88)


class ColumnDetectionTests(unittest.TestCase):
    def _words(self, spans):
        return [{"x0": a, "x1": b} for a, b in spans]

    def test_two_columns_detected(self):
        # colonna sx ~[40,280], colonna dx ~[320,560], gutter a ~300
        words = []
        for row in range(40):
            words.append({"x0": 40, "x1": 280})
            words.append({"x0": 320, "x1": 560})
        gutter = _detect_column_gutter(words, width=600)
        self.assertIsNotNone(gutter)
        self.assertTrue(260 < gutter < 340, f"gutter inatteso: {gutter}")

    def test_single_column_returns_none(self):
        # parole che coprono tutta la larghezza, nessun gutter
        words = [{"x0": 40, "x1": 560} for _ in range(60)]
        self.assertIsNone(_detect_column_gutter(words, width=600))

    def test_too_few_words_returns_none(self):
        words = [{"x0": 40, "x1": 280} for _ in range(10)]
        self.assertIsNone(_detect_column_gutter(words, width=600))


class OcrFallbackTests(unittest.TestCase):
    def test_ocr_available_returns_bool(self):
        # dipende dall'ambiente: deve solo essere un bool, mai sollevare
        self.assertIsInstance(_ocr_available(), bool)

    def test_ocr_page_degrades_gracefully(self):
        # se il rendering fallisce, ritorna "" senza sollevare → si usa l'embedded
        class FakePage:
            def to_image(self, resolution=200):
                raise RuntimeError("render non disponibile")
        self.assertEqual(_ocr_page_text(FakePage()), "")

    def test_warning_empty_when_quality_good(self):
        self.assertEqual(_pdf_source_warning({"score": 95}, 0, True), "")

    def test_warning_mentions_ocr_when_unavailable(self):
        w = _pdf_source_warning({"score": 80}, 0, False)
        self.assertIn("OCR non disponibile", w)

    def test_warning_reports_recovered_pages(self):
        w = _pdf_source_warning({"score": 80}, 5, True)
        self.assertIn("5 pagine", w)


if __name__ == "__main__":
    unittest.main()
