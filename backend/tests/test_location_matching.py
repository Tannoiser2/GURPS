"""Test del matcher azione-di-viaggio → location (radice del loop "Casa di Corbitt").

Prima del fix, le azioni di viaggio in prosa generate dall'AI ("Recarsi alla
Stazione", "Tornare alla dimora di Corbitt ...") non aggiornavano la posizione:
il director restava sulla location sbagliata → scontri fuori luogo e loop.
"""
import unittest

from App.location_matching import match_destination

# Location reali compilate da "La Casa di Corbitt" (The Haunting).
LOCS = [
    ("loc_boston_globe", "Il Boston Globe"),
    ("loc_biblioteca_centrale", "Biblioteca Centrale"),
    ("loc_municipio", "Municipio"),
    ("loc_stazione_polizia", "Alta Corte; Stazione Centrale di Polizia"),
    ("loc_vicinato", "Il Vicinato"),
    ("loc_roxbury_sanitarium", "Roxbury Sanitarium"),
    ("loc_cappella", "La Cappella della Contemplazione"),
    ("loc_dimora_corbitt_pt", "La Vecchia Dimora di Corbitt - Piano Terra"),
    ("loc_dimora_corbitt_ps", "La Vecchia Dimora di Corbitt - Piano Superiore"),
    ("loc_cantine_corbitt", "Le Cantine"),
]


class TestMatchDestination(unittest.TestCase):
    def test_prose_travel_actions_resolve(self):
        cases = {
            "Recarsi alla Stazione Centrale di Polizia per cercare il rapporto": "loc_stazione_polizia",
            "Visitare il Municipio per controllare i registri catastali": "loc_municipio",
            "Recarsi al Roxbury Sanitarium per intervistare pazienti": "loc_roxbury_sanitarium",
            "Spostarsi verso Il Vicinato": "loc_vicinato",
        }
        for action, expected in cases.items():
            self.assertEqual(match_destination(action, LOCS), expected, msg=action)

    def test_long_trailing_clause_still_matches(self):
        # Il bug originale: la coda lunga faceva fallire il fuzzy-match.
        action = ("Tornare alla dimora di Corbitt armato delle informazioni "
                  "raccolte — è tempo di esplorare la cantina e affrontare ciò "
                  "che si nasconde là sotto")
        self.assertIn(match_destination(action, LOCS),
                      {"loc_dimora_corbitt_pt", "loc_dimora_corbitt_ps"})

    def test_destination_named_first_wins(self):
        # "il Vicinato" è la meta; "della dimora di Corbitt" è solo un qualificatore.
        action = "Visitare il Vicinato della dimora di Corbitt per intervistare i residenti"
        self.assertEqual(match_destination(action, LOCS), "loc_vicinato")

    def test_non_travel_actions_do_not_move(self):
        # Azioni che NON sono spostamenti devono restituire None (resta sul posto).
        for action in [
            "Consultare i vecchi articoli di giornale su Corbitt",
            "Osservare attentamente la dimora di Corbitt dall'esterno",
            "Cercare l'indirizzo del Roxbury Sanitarium",
            "Interrogare il vecchio sul significato di 'maledetta'",
        ]:
            self.assertIsNone(match_destination(action, LOCS), msg=action)

    def test_empty_and_no_candidates(self):
        self.assertIsNone(match_destination("", LOCS))
        self.assertIsNone(match_destination("Recarsi al Municipio", []))


if __name__ == "__main__":
    unittest.main()
