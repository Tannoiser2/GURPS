import os
import unittest
from unittest.mock import patch

from App import llm_extractors
from App.adventure_compiler import compile_pdf_to_runtime


class LlmExtractorGuardTests(unittest.TestCase):
    def test_disabled_by_default_returns_none(self):
        os.environ.pop("GURPS_ENABLE_LLM_EXTRACTORS", None)
        self.assertIsNone(
            llm_extractors.extract_clues_with_llm("text", {"clues": []}, title="X")
        )

    def test_returns_none_when_opted_in_but_no_provider(self):
        with patch.dict(os.environ, {"GURPS_ENABLE_LLM_EXTRACTORS": "1"}):
            with patch("App.claude_service._text_provider_available", return_value=False):
                self.assertIsNone(
                    llm_extractors.extract_clues_with_llm("text", {"clues": []}, title="X")
                )


class LlmClueMergeTests(unittest.TestCase):
    def test_llm_clues_enrich_structure_and_appear_in_definition(self):
        fake_merged = [
            {
                "id": "llm_clue_1",
                "label": "Fotografia compromettente",
                "text": "Una foto del sospetto sul molo durante la notte del crimine.",
                "type": "physical_evidence",
                "source_location": "Molo 13",
                "reveals": "Il sospetto era sulla scena.",
                "hidden_implication": "Aveva un complice locale.",
                "payoff": "Sblocca interrogatorio del docker.",
                "possible_actions": ["confrontare il sospetto", "cercare il complice"],
                "source_ref": {"section": "Molo 13"},
                "source_status": "inferred",
                "is_preserved_from_pdf": False,
                "llm_extracted": True,
                "confidence": 0.8,
            },
            {
                "id": "llm_clue_2",
                "label": "Documenti del sindacato",
                "text": "Registri di carico che mostrano sparizioni regolari.",
                "type": "document",
                "source_location": "Ufficio del sindacato",
                "reveals": "Merce sparisce con cadenza.",
                "hidden_implication": "Il sindacato e complice.",
                "payoff": "Apre pista politica.",
                "possible_actions": ["affrontare il delegato"],
                "source_ref": {"section": "Ufficio del sindacato"},
                "source_status": "inferred",
                "is_preserved_from_pdf": False,
                "llm_extracted": True,
                "confidence": 0.78,
            },
        ]

        text = "\n".join([
            "1. Molo 13. Una banchina deserta sotto la pioggia.",
            "2. Ufficio del sindacato. Schedari in disordine.",
        ])

        with patch(
            "App.adventure_compiler.extract_clues_with_llm",
            return_value=fake_merged,
        ):
            compiled = compile_pdf_to_runtime(text, title="Molo", genre_hint="detective_classico")

        definition = compiled["adventure_definition"]
        labels = [c.label for c in definition.clues]
        self.assertIn("Fotografia compromettente", labels)
        self.assertIn("Documenti del sindacato", labels)
        photo = next(c for c in definition.clues if c.label == "Fotografia compromettente")
        self.assertEqual(photo.type, "physical_evidence")
        self.assertEqual(photo.source_status, "inferred")
        self.assertFalse(photo.is_preserved_from_pdf)
        self.assertEqual(photo.source_location, "Molo 13")
        self.assertIn("confrontare il sospetto", photo.possible_actions)

    def test_no_llm_means_structure_unchanged(self):
        text = "Indizio: chiave sotto il tappeto\nIndizio: scontrino macchiato"
        compiled = compile_pdf_to_runtime(text, title="Default", genre_hint="detective_classico")
        labels = [c.label for c in compiled["adventure_definition"].clues]
        self.assertTrue(any("chiave" in l.lower() for l in labels))
        self.assertTrue(any("scontrino" in l.lower() for l in labels))


class LlmActorEnrichmentTests(unittest.TestCase):
    def test_disabled_by_default_returns_none(self):
        os.environ.pop("GURPS_ENABLE_LLM_EXTRACTORS", None)
        self.assertIsNone(
            llm_extractors.enrich_actors_with_llm(
                "text",
                {"npcs": [{"label": "TOCKMAN", "text": "lawyer"}]},
                title="X",
            )
        )

    def test_enrichment_populates_actor_state(self):
        # The regex pass found Tockman; the LLM fills in the agenda fields.
        text = (
            "1. Banca centrale. Caveau con orari di apertura programmati.\n"
            "Indizio: planimetria del caveau\n"
            "William Tockman is a lawyer with terminal illness who turns to crime."
        )
        enriched_npcs = [{
            "label": "WILLIAM TOCKMAN",
            "name": "William Tockman",
            "text": "lawyer with terminal illness who turns to crime",
            "role": "antagonist",
            "goal": "rubare il diamante prima di morire",
            "fear": "morire senza aver provveduto alla sorella",
            "secret": "ha pochi mesi di vita",
            "current_plan": "studiare il caveau della banca",
            "fallback_plan": "ricattare il direttore con foto compromettenti",
            "knows": ["orari guardie", "punti ciechi telecamere"],
            "wants": ["denaro per la sorella"],
            "avoids": ["arresto pubblico"],
            "relationships": [{"name": "Sorella", "type": "family", "note": "vive in ospedale"}],
            "pressure_response": {
                "low": "rinvia il colpo di un giorno",
                "medium": "elimina un testimone",
                "high": "anticipa il colpo",
                "critical": "prende ostaggi",
            },
            "llm_enriched": True,
        }]

        with patch(
            "App.adventure_compiler.enrich_actors_with_llm",
            return_value=enriched_npcs,
        ):
            compiled = compile_pdf_to_runtime(text, title="Heist", genre_hint="detective_classico")

        definition = compiled["adventure_definition"]
        self.assertTrue(definition.actors, "expected at least one actor in definition")
        tockman = next((a for a in definition.actors if "tockman" in a.name.lower()), None)
        self.assertIsNotNone(tockman)
        self.assertEqual(tockman.role, "antagonist")
        self.assertEqual(tockman.goal, "rubare il diamante prima di morire")
        self.assertEqual(tockman.fear, "morire senza aver provveduto alla sorella")
        self.assertNotEqual(tockman.pressure_response["medium"], "tratta")
        self.assertIn("ostaggi", tockman.pressure_response["critical"])
        self.assertEqual(tockman.relationships[0]["type"], "family")
        self.assertTrue(tockman.llm_enriched)
        self.assertFalse(tockman.inferred_agenda)


if __name__ == "__main__":
    unittest.main()
