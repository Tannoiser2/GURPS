"""La recovery delle piste fantasma deve produrre piste REALI, non stub vuoti.

Prima del fix, gli ID di pista citati dagli indizi ma non definiti in
``story_threads`` venivano materializzati come stub con ``true_answer`` e
``clue_plan`` vuoti: questo eliminava il warning "pista fantasma" ma aggiungeva
due suggestion (manca risposta / manca indizio), facendo a volte SCENDERE il
punteggio. Ora la pista viene collegata agli indizi che la citano e riceve una
``true_answer`` derivata da revelation/payoff.
"""
from App.adventure_doctor import _recover_phantom_threads, audit


def _base_definition():
    return {
        "title": "Test",
        "genre": "mystery",
        "premise": "Un omicidio in una villa isolata.",
        "story_threads": [],
        "clues": [
            {"id": "c1", "label": "Lettera bruciata", "thread_id": "T_movente",
             "payoff": "Rivela il debito tra la vittima e il maggiordomo",
             "linked_npcs": ["a_maggiordomo"]},
        ],
        "revelations": [
            {"id": "r1", "thread_id": "T_movente",
             "statement": "Il maggiordomo ha ucciso per cancellare il debito."},
        ],
        "actors": [{"id": "a_maggiordomo", "name": "Il Maggiordomo", "role": "villain"}],
    }


def test_phantom_thread_becomes_real():
    enriched = _base_definition()
    phantom = {"T_movente": ["c1", "rev:r1"]}
    n = _recover_phantom_threads(enriched, phantom)

    assert n == 1
    threads = enriched["story_threads"]
    assert len(threads) == 1
    t = threads[0]
    assert t["id"] == "T_movente"
    # risposta canonica derivata dalla revelation, non vuota
    assert t["true_answer"].strip(), "la pista recuperata deve avere una true_answer"
    # indizio che la cita collegato esplicitamente
    assert "c1" in t["collected_clue_ids"]
    # PNG collegato raccolto dall'indizio
    assert "a_maggiordomo" in t["linked_npcs"]


def test_recovered_thread_not_flagged_as_phantom_or_empty():
    enriched = _base_definition()
    _recover_phantom_threads(enriched, {"T_movente": ["c1", "rev:r1"]})

    findings = audit(enriched)
    thread_findings = [f for f in findings if f.category == "thread" and f.entity_id == "T_movente"]
    msgs = " ".join(f.message for f in thread_findings)

    assert "fantasma" not in msgs, "non deve più risultare pista fantasma"
    assert "risposta canonica" not in msgs, "non deve mancare la true_answer"
    assert "non ha indizi collegati" not in msgs, "deve avere indizi collegati"
