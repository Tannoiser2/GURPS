import unittest
from unittest.mock import patch

from App.adventure_compiler import compile_ai_generated_to_runtime, compile_from_raw_structure, compile_pdf_to_runtime, compile_structured_text_to_runtime
from App.claude_service import _normalize_adventure_canon
from App.claude_service import compile_adventure_to_runtime


class PdfVsAiGeneratedModeTests(unittest.TestCase):
    def test_modes_are_distinct(self):
        pdf = compile_pdf_to_runtime("1. Sala A\n2. Sala B\n3. Sala C", title="PDF", genre_hint="fantasy")
        ai = compile_ai_generated_to_runtime("Crea un colpo heist con sicurezza e fuga", title="AI", genre_hint="action")

        self.assertEqual(pdf["adventure_definition"].source_mode, "pdf_import")
        self.assertEqual(ai["adventure_definition"].source_mode, "ai_generated")
        self.assertTrue(pdf["adventure_definition"].preservation_policy["forbid_structural_compression"])
        self.assertNotEqual(len(ai["adventure_definition"].locations), 3)
        self.assertNotEqual(len(ai["adventure_definition"].clues), 3)

    def test_structured_raw_text_preserves_shape_without_pdf_mode(self):
        raw = compile_structured_text_to_runtime("1. Sala A\n2. Sala B\n3. Sala C", title="Raw", genre_hint="fantasy")
        definition = raw["adventure_definition"]

        self.assertEqual(definition.source_mode, "raw_text")
        self.assertTrue(definition.preservation_policy["forbid_structural_compression"])
        self.assertEqual(len(definition.locations), 3)

    def test_ai_generated_ritual_has_concrete_threads(self):
        compiled = compile_ai_generated_to_runtime(
            "Crea una missione fantasy con rituale, altare e conto alla rovescia",
            title="Rituale",
            genre_hint="fantasy",
        )
        definition = compiled["adventure_definition"]
        statements = [r.statement.lower() for r in definition.revelations]
        self.assertFalse(any("quale leva della struttura" in s for s in statements))
        self.assertFalse(any("ritual_countdown" in s for s in statements))
        self.assertTrue(any("rito" in s or "rituale" in s for s in statements))

    def test_pdf_without_adventure_material_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_pdf_to_runtime(
                "Guards who claim hand-weapon ability will fight in training. "
                "Entertainers, cooks, and most other applicants will be interviewed.",
                title="Rules Text",
                genre_hint="fantasy",
            )

    def test_ai_generated_threads_are_repaired_from_real_clues(self):
        compiled = compile_from_raw_structure(
            {
                "source_mode": "ai_generated",
                "title": "Il Dente del Drago",
                "genre": "fantasy",
                "win_condition": "Scoprire la biblioteca e impedire al Barone di usare l'artefatto.",
                "hidden_truth": "Il pendente e la chiave della biblioteca dimenticata.",
                "story_threads": [
                    {
                        "id": "T1",
                        "question": "Quale fatto concreto su Dente Drago Aelys ritrova appesa balconcino cambia la scelta dei giocatori?",
                        "true_answer": "Quale fatto concreto su Dente Drago Aelys ritrova appesa balconcino cambia la scelta dei giocatori?",
                    }
                ],
                "clues": [
                    {
                        "id": "clue_mappa",
                        "label": "Mappa della Biblioteca",
                        "type": "document",
                        "thread_id": "T1",
                        "source_location": "Biblioteca del monastero",
                        "reveals": "La posizione dell'antica biblioteca.",
                        "payoff": "Direziona il gruppo verso il luogo corretto per il finale.",
                    },
                    {
                        "id": "clue_sigillo",
                        "label": "Sigillo del Barone",
                        "type": "physical_evidence",
                        "thread_id": "T2",
                        "source_location": "Stanza privata del Barone",
                        "reveals": "Il Barone ha accesso a documenti riservati.",
                        "payoff": "Permette di accedere a zone del castello altrimenti chiuse.",
                    },
                ],
                "locations": [{"name": "Biblioteca del Monastero"}, {"name": "Castello del Barone"}],
            },
            source_type="raw_text",
            title="Il Dente del Drago",
            genre_hint="fantasy",
        )
        legacy_threads = compiled["adventure_definition"].legacy_adventure["story_threads"]
        questions = " ".join(t["question"].lower() for t in legacy_threads)
        answers = " ".join(t["true_answer"].lower() for t in legacy_threads)

        self.assertNotIn("quale fatto concreto", questions)
        self.assertNotIn("cambia la scelta dei giocatori", answers)
        self.assertIn("mappa", questions)
        self.assertIn("biblioteca", answers)

    def test_fantasy_tactical_maps_are_location_specific(self):
        normalized = _normalize_adventure_canon(
            {
                "title": "Il Dente del Drago",
                "genre": "fantasy",
                "win_condition": "Fermare il Barone.",
                "hidden_truth": "Il Dente apre la biblioteca.",
                "clues": [{"id": "c1", "label": "Mappa", "thread_id": "T1", "location": "Biblioteca del Monastero"}],
                "locations": [
                    {
                        "name": "Taverna dell'Anello di Ferro",
                        "tactical_map": {"role": "neutral", "trigger": "ritrovo di Gareth"},
                    },
                    {"name": "Bosco Antico", "has_combat_potential": True},
                    {"name": "Biblioteca del Monastero", "has_combat_potential": True},
                ],
            },
            source="generated",
        )
        tavern = normalized["locations"][0]
        forest = normalized["locations"][1]["tactical_map"]
        library = normalized["locations"][2]["tactical_map"]

        self.assertFalse((tavern.get("tactical_map") or {}).get("enabled", False))
        self.assertTrue(any("tronchi" in f or "radici" in f for f in forest["features"]))
        self.assertTrue(any("scaffali" in f for f in library["features"]))
        self.assertFalse(any("sarcof" in f.lower() for f in forest["features"] + library["features"]))

    def test_pdf_weak_structure_without_ai_fails_loudly(self):
        with patch("App.claude_service._text_provider_available", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                compile_adventure_to_runtime(
                    "This page mostly explains generic rules and has no keyed rooms, clues, NPCs or encounters.",
                    source_type="pdf_text",
                    title="Weak PDF",
                    genre_hint="fantasy",
                )
        self.assertIn("Meglio fermarsi", str(ctx.exception))

    def test_ai_generated_actor_placeholders_are_replaced_by_canon_names(self):
        compiled = compile_from_raw_structure(
            {
                "source_mode": "ai_generated",
                "title": "Il Respiro del Drago Dormiente",
                "genre": "fantasy",
                "win_condition": "Fermare il gas e riportare il villaggio al sicuro.",
                "hidden_truth": (
                    "Non esiste alcun drago. Durgan ha scoperto un deposito di gas. "
                    "Selira ha corrotto Tobin per rompere i sigilli; Edrin ha visto Tobin fuggire."
                ),
                "actors": [
                    {
                        "id": "actor_ai_1",
                        "name": "Custode della leva 1",
                        "role": "witness",
                        "goal": "portare avanti una leva dell'avventura senza aggiungere sottotrame gratuite",
                        "secret": "conosce o controlla un pezzo della soluzione",
                    },
                    {
                        "id": "actor_ai_3",
                        "name": "Oppositore 3",
                        "role": "antagonist",
                        "goal": "portare avanti una leva dell'avventura senza aggiungere sottotrame gratuite",
                        "secret": "conosce o controlla un pezzo della soluzione",
                    },
                ],
                "clues": [
                    {"id": "c1", "label": "Borsa di Durgan", "thread_id": "T1", "reveals": "Durgan sapeva della manomissione", "source_location": "Miniera"},
                    {"id": "c2", "label": "Registro di Selira", "thread_id": "T2", "reveals": "Selira ha pagato Tobin", "source_location": "Locanda"},
                    {"id": "c3", "label": "Testimonianza di Edrin", "thread_id": "T1", "reveals": "Edrin ha visto Tobin nella miniera", "source_location": "Villaggio"},
                ],
                "locations": [{"name": "Miniera"}, {"name": "Locanda"}, {"name": "Baracche"}],
            },
            source_type="raw_text",
            title="Il Respiro del Drago Dormiente",
            genre_hint="fantasy",
        )
        names = [a.name for a in compiled["adventure_definition"].actors]
        joined = " ".join(names).lower()

        self.assertNotIn("custode della leva", joined)
        self.assertNotIn("oppositore 3", joined)
        self.assertIn("durgan", joined)
        self.assertIn("selira", joined)
        self.assertIn("tobin", joined)


if __name__ == "__main__":
    unittest.main()
