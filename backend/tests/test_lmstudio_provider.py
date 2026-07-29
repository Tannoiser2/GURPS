import unittest
from unittest import mock

from App import claude_service as cs


def _fake_openai_module(capture: dict):
    """Costruisce un finto modulo openai il cui OpenAI(...) registra base_url/api_key
    e le chiamate a chat.completions.create, restituendo una risposta fissa.
    """
    class _Msg:
        content = '{"narrative":"ok","options":[],"state_updates":{}}'

    class _Choice:
        message = _Msg()

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 5

    class _Resp:
        choices = [_Choice()]
        usage = _Usage()

    class _Completions:
        def create(self, **kwargs):
            capture.setdefault("calls", []).append(kwargs)
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, **kwargs):
            capture["client_kwargs"] = kwargs
            self.chat = _Chat()

    fake = mock.Mock()
    fake.OpenAI = _Client
    return fake


class LMStudioProviderTests(unittest.TestCase):
    def setUp(self):
        self._prev_provider = cs._ACTIVE_PROVIDER

    def tearDown(self):
        cs.set_active_provider(self._prev_provider)

    def test_set_active_provider_accepts_lmstudio(self):
        cs.set_active_provider("lmstudio")
        self.assertEqual(cs._ACTIVE_PROVIDER, "lmstudio")

    def test_unknown_provider_falls_back_to_claude(self):
        cs.set_active_provider("nonexistent")
        self.assertEqual(cs._ACTIVE_PROVIDER, "claude")

    def test_availability_requires_enabled_flag(self):
        with mock.patch.object(cs, "_OPENAI_AVAILABLE", True):
            with mock.patch.object(cs, "LMSTUDIO_ENABLED", False):
                self.assertFalse(cs._text_provider_available("lmstudio"))
            with mock.patch.object(cs, "LMSTUDIO_ENABLED", True):
                self.assertTrue(cs._text_provider_available("lmstudio"))

    def test_call_lmstudio_uses_local_base_url_and_model(self):
        capture: dict = {}
        fake = _fake_openai_module(capture)
        with mock.patch.object(cs, "_openai_module", fake), \
             mock.patch.object(cs, "_OPENAI_AVAILABLE", True), \
             mock.patch.object(cs, "LMSTUDIO_BASE_URL", "http://localhost:1234/v1"), \
             mock.patch.object(cs, "LMSTUDIO_MODEL", "test-local-model"), \
             mock.patch.object(cs, "LMSTUDIO_API_KEY", "lm-studio"):
            out = cs._call_lmstudio("ciao", max_tokens=32, json_mode=True)
        self.assertIn("narrative", out)
        # Il client punta al server locale, non alle API cloud.
        self.assertEqual(capture["client_kwargs"]["base_url"], "http://localhost:1234/v1")
        self.assertEqual(capture["client_kwargs"]["api_key"], "lm-studio")
        # La chiamata usa il modello locale e forza json mode.
        call = capture["calls"][0]
        self.assertEqual(call["model"], "test-local-model")
        self.assertEqual(call["response_format"], {"type": "json_object"})

    def test_json_mode_off_when_flag_disabled(self):
        capture: dict = {}
        fake = _fake_openai_module(capture)
        with mock.patch.object(cs, "_openai_module", fake), \
             mock.patch.object(cs, "_OPENAI_AVAILABLE", True), \
             mock.patch.object(cs, "LMSTUDIO_JSON_MODE", False):
            cs._call_lmstudio("ciao", json_mode=True)
        self.assertNotIn("response_format", capture["calls"][0])

    def test_dispatcher_routes_to_lmstudio(self):
        capture: dict = {}
        fake = _fake_openai_module(capture)
        with mock.patch.object(cs, "_openai_module", fake), \
             mock.patch.object(cs, "_OPENAI_AVAILABLE", True):
            cs.set_active_provider("lmstudio")
            cs._call_text_model("prompt di test", max_tokens=16, json_mode=True)
        self.assertEqual(len(capture["calls"]), 1)

    def test_call_with_provider_targets_lmstudio_explicitly(self):
        capture: dict = {}
        fake = _fake_openai_module(capture)
        with mock.patch.object(cs, "_openai_module", fake), \
             mock.patch.object(cs, "_OPENAI_AVAILABLE", True):
            cs.set_active_provider("claude")  # attivo diverso
            cs._call_text_model_with_provider("lmstudio", "prompt", max_tokens=16)
        self.assertEqual(len(capture["calls"]), 1)


if __name__ == "__main__":
    unittest.main()
