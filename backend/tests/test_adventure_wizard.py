"""A3 — Adventure creation wizard tests

Coverage:
- GET /adventure/wizard/steps returns step schema
- POST /adventure/wizard/step creates draft and advances steps
- Missing required fields return validation_errors
- Incomplete draft cannot be compiled
- Full wizard flow produces compilable draft
- Draft retrieval by id
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from App.adventure_wizard import (
    _drafts as _wizard_drafts,
    WIZARD_STEPS as _WIZARD_STEPS,
    WIZARD_STEP_SCHEMA as _WIZARD_STEP_SCHEMA,
    apply_step,
    get_draft,
    validate_step,
)


class _FakeHTTPException(Exception):
    def __init__(self, status_code, detail=""):
        self.status_code = status_code
        self.detail = detail


def wizard_get_steps():
    return {"steps": _WIZARD_STEPS, "schema": _WIZARD_STEP_SCHEMA}


def wizard_submit_step(payload):
    step = payload.step
    draft_id = payload.draft_id
    data = payload.data
    if step not in _WIZARD_STEPS:
        raise _FakeHTTPException(400, f"Step sconosciuto: {step}")
    return apply_step(draft_id, step, data)


def wizard_get_draft(draft_id):
    result = get_draft(draft_id)
    if result is None:
        raise _FakeHTTPException(404, f"Bozza '{draft_id}' non trovata")
    return result


# Minimal payload stub — mirrors WizardStepPayload without Pydantic/FastAPI
class WizardStepPayload:
    def __init__(self, draft_id: str, step: str, data: dict):
        self.draft_id = draft_id
        self.step = step
        self.data = data


HTTPException = _FakeHTTPException


def _step(draft_id: str, step: str, data: dict) -> dict:
    payload = WizardStepPayload(draft_id=draft_id, step=step, data=data)
    return wizard_submit_step(payload)


_TITLE_DATA = {"title": "Test Avventura", "genre": "investigation"}
_PREMISE_DATA = {
    "premise": "Un furto è avvenuto nella biblioteca.",
    "hidden_truth": "Il bibliotecario ha rubato il codice per vendita.",
    "win_condition": "Recuperare il codice e smascherare il colpevole.",
    "threat_description": "Il codice sta per essere venduto.",
}
_NPCS_DATA = {"npcs": [
    {"id": "npc_1", "name": "Bibliotecario", "role": "antagonist", "goal": "Nascondere il furto", "location": "Biblioteca", "attitude": "neutral"},
    {"id": "npc_2", "name": "Custode", "role": "witness", "goal": "Raccontare cosa ha visto", "location": "Biblioteca", "attitude": "friendly"},
]}
_CLOCKS_DATA = {"clocks": [
    {"id": "clock_1", "label": "Vendita del codice", "max_value": 6, "consequence": "Il codice sparisce per sempre", "clock_type": "terminal_defeat"},
]}
_CLUES_DATA = {
    "clues": [
        {"id": "clue_1", "label": "Registro mancante", "type": "document", "thread_id": "thread_1", "source_location": "Biblioteca", "reveals": "Una pagina è stata strappata."},
        {"id": "clue_2", "label": "Impronta di stivale", "type": "physical_evidence", "thread_id": "thread_1", "source_location": "Biblioteca", "reveals": "Impronta insolita vicino alla teca."},
        {"id": "clue_3", "label": "Ricevuta di vendita", "type": "document", "thread_id": "thread_1", "source_location": "Ufficio bibliotecario", "reveals": "Una ricevuta per un oggetto antico."},
    ],
    "threads": [
        {"id": "thread_1", "question": "Chi ha rubato il codice?", "required_clues": ["clue_1", "clue_2", "clue_3"], "minimum_clues_to_deduce": 2, "payoff": "Il bibliotecario è smascherato."},
    ],
}


class TestWizardSteps(unittest.TestCase):
    def test_get_steps_returns_all_steps(self):
        result = wizard_get_steps()
        self.assertEqual(result["steps"], _WIZARD_STEPS)
        self.assertIn("title", result["schema"])
        self.assertIn("clues", result["schema"])

    def test_unknown_step_raises(self):
        with self.assertRaises(HTTPException):
            _step("", "unknown_step", {})

    def test_title_step_creates_draft(self):
        result = _step("", "title", _TITLE_DATA)
        self.assertEqual(result["validation_errors"], [])
        self.assertIsNotNone(result["draft_id"])
        self.assertEqual(result["next_step"], "premise")
        self.assertFalse(result["completed"])
        _wizard_drafts.pop(result["draft_id"], None)

    def test_title_step_missing_genre_returns_error(self):
        result = _step("", "title", {"title": "Solo titolo"})
        self.assertIn("genre", str(result["validation_errors"]))

    def test_premise_step_missing_hidden_truth(self):
        result = _step("", "premise", {"premise": "Una storia.", "win_condition": "Vinci."})
        self.assertTrue(len(result["validation_errors"]) > 0)

    def test_npcs_step_requires_two_npcs(self):
        result = _step("", "npcs", {"npcs": [{"id": "n1", "name": "Solo"}]})
        self.assertTrue(any("almeno 2" in e for e in result["validation_errors"]))

    def test_npcs_step_npc_missing_id(self):
        result = _step("", "npcs", {"npcs": [
            {"name": "Senza ID", "role": "witness"},
            {"id": "n2", "name": "Con ID", "role": "ally"},
        ]})
        self.assertTrue(len(result["validation_errors"]) > 0)

    def test_clocks_step_requires_one_clock(self):
        result = _step("", "clocks", {"clocks": []})
        self.assertTrue(len(result["validation_errors"]) > 0)

    def test_clues_step_requires_three_clues(self):
        result = _step("", "clues", {
            "clues": [{"id": "c1", "label": "Solo uno"}],
            "threads": [{"id": "t1", "question": "?", "required_clues": ["c1"], "minimum_clues_to_deduce": 1}],
        })
        self.assertTrue(any("almeno 3" in e for e in result["validation_errors"]))

    def test_clues_step_requires_thread(self):
        clues = [{"id": f"c{i}", "label": f"Clue {i}"} for i in range(3)]
        result = _step("", "clues", {"clues": clues, "threads": []})
        self.assertTrue(any("thread" in e.lower() for e in result["validation_errors"]))


class TestWizardDraftPersistence(unittest.TestCase):
    def setUp(self):
        self._draft_id = None

    def tearDown(self):
        if self._draft_id:
            _wizard_drafts.pop(self._draft_id, None)

    def test_draft_accumulates_steps(self):
        r1 = _step("", "title", _TITLE_DATA)
        did = r1["draft_id"]
        self._draft_id = did
        r2 = _step(did, "premise", _PREMISE_DATA)
        self.assertEqual(r2["draft_id"], did)
        draft = wizard_get_draft(did)
        self.assertIn("title", draft["completed_steps"])
        self.assertIn("premise", draft["completed_steps"])
        self.assertIn("npcs", draft["missing_steps"])

    def test_draft_not_ready_without_all_steps(self):
        r1 = _step("", "title", _TITLE_DATA)
        did = r1["draft_id"]
        self._draft_id = did
        draft = wizard_get_draft(did)
        self.assertFalse(draft["ready_to_compile"])

    def test_full_wizard_flow_marks_completed(self):
        r = _step("", "title", _TITLE_DATA)
        did = r["draft_id"]
        self._draft_id = did
        _step(did, "premise", _PREMISE_DATA)
        _step(did, "npcs", _NPCS_DATA)
        _step(did, "clocks", _CLOCKS_DATA)
        r_final = _step(did, "clues", _CLUES_DATA)
        self.assertTrue(r_final["completed"])
        draft = wizard_get_draft(did)
        self.assertTrue(draft["ready_to_compile"])

    def test_get_draft_not_found_raises(self):
        with self.assertRaises(HTTPException):
            wizard_get_draft("non_esiste_draft_id")

    def test_draft_preview_excludes_internal_fields(self):
        r = _step("", "title", _TITLE_DATA)
        did = r["draft_id"]
        self._draft_id = did
        preview = r["draft_preview"]
        self.assertNotIn("_updated", preview)
        self.assertNotIn("_completed_steps", preview)
        self.assertIn("title", preview)


if __name__ == "__main__":
    unittest.main()
