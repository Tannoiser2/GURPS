import unittest
from unittest import mock

from App import claude_service as cs


class SDWorkflowTests(unittest.TestCase):
    def test_build_sdxl_workflow_structure(self):
        wf = cs._build_sdxl_workflow("un prompt", "brutto", 1344, 768, 12345)
        # checkpoint dal setting
        self.assertEqual(wf["4"]["class_type"], "CheckpointLoaderSimple")
        self.assertEqual(wf["4"]["inputs"]["ckpt_name"], cs.SD_COMFY_CHECKPOINT)
        # dimensioni nel latent
        self.assertEqual(wf["5"]["inputs"]["width"], 1344)
        self.assertEqual(wf["5"]["inputs"]["height"], 768)
        # prompt positivo/negativo
        self.assertEqual(wf["6"]["inputs"]["text"], "un prompt")
        self.assertEqual(wf["7"]["inputs"]["text"], "brutto")
        # seed nel sampler
        self.assertEqual(wf["3"]["inputs"]["seed"], 12345)
        # il grafo termina con SaveImage
        self.assertEqual(wf["9"]["class_type"], "SaveImage")


class SDProviderGatingTests(unittest.TestCase):
    def setUp(self):
        self._prev = cs._ACTIVE_IMAGE_PROVIDER

    def tearDown(self):
        cs.set_active_image_provider(self._prev)

    def test_set_active_image_provider(self):
        cs.set_active_image_provider("stablediffusion")
        self.assertEqual(cs._ACTIVE_IMAGE_PROVIDER, "stablediffusion")
        cs.set_active_image_provider(None)
        self.assertEqual(cs._ACTIVE_IMAGE_PROVIDER, "")

    def test_sd_active_requires_enabled_and_provider(self):
        with mock.patch.object(cs, "SD_ENABLED", True):
            cs.set_active_image_provider("stablediffusion")
            self.assertTrue(cs._sd_active())
            cs.set_active_image_provider("openai")
            self.assertFalse(cs._sd_active())
        with mock.patch.object(cs, "SD_ENABLED", False):
            cs.set_active_image_provider("stablediffusion")
            self.assertFalse(cs._sd_active())


class SDRoutingTests(unittest.TestCase):
    """Verifica che le funzioni immagine instradino su ComfyUI quando SD è attivo."""

    def setUp(self):
        self._prev = cs._ACTIVE_IMAGE_PROVIDER

    def tearDown(self):
        cs.set_active_image_provider(self._prev)

    def test_scene_image_routes_to_comfyui(self):
        with mock.patch.object(cs, "SD_ENABLED", True), \
             mock.patch.object(cs, "_build_image_prompt", return_value="english scene prompt"), \
             mock.patch.object(cs, "_call_comfyui_image", return_value="BASE64IMG") as m:
            cs.set_active_image_provider("stablediffusion")
            out = cs.generate_scene_image("scena italiana", "fantasy", "dungeon")
        self.assertEqual(out, "BASE64IMG")
        m.assert_called_once()
        self.assertEqual(m.call_args.kwargs.get("kind"), "scene")

    def test_npc_avatar_routes_to_comfyui(self):
        with mock.patch.object(cs, "SD_ENABLED", True), \
             mock.patch.object(cs, "_call_comfyui_image", return_value="IMG") as m:
            cs.set_active_image_provider("stablediffusion")
            out = cs.generate_npc_avatar("Grok", "orco brutale", "enemy", "fantasy")
        self.assertEqual(out, "IMG")
        self.assertEqual(m.call_args.kwargs.get("kind"), "portrait")

    def test_not_routed_when_sd_inactive(self):
        with mock.patch.object(cs, "SD_ENABLED", True), \
             mock.patch.object(cs, "_call_comfyui_image", return_value="IMG") as m:
            cs.set_active_image_provider("openai")  # non SD
            # provider testuale non-openai → prende il ramo Gemini, che senza key torna None
            cs.set_active_provider("claude")
            out = cs.generate_npc_avatar("Grok", "orco", "enemy", "fantasy")
        m.assert_not_called()
        # senza provider immagini reale, non deve comunque usare ComfyUI
        self.assertIsNone(out)


class SDComfyHttpFlowTests(unittest.TestCase):
    """Collauda il flusso HTTP reale di _call_comfyui_image: submit → poll → view,
    mockando urllib.request.urlopen (nessuna rete reale)."""

    def test_full_submit_poll_fetch(self):
        import json as _json
        import base64 as _b64
        import urllib.request
        png = _b64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )

        class _FakeResp:
            def __init__(self, data):
                self._data = data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return self._data

        history = {"test123": {
            "outputs": {"9": {"images": [{"filename": "gurps_0001.png", "subfolder": "", "type": "output"}]}},
            "status": {"completed": True},
        }}

        def _fake_urlopen(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req
            if url.endswith("/prompt"):
                return _FakeResp(_json.dumps({"prompt_id": "test123"}).encode())
            if "/history/" in url:
                return _FakeResp(_json.dumps(history).encode())
            if "/view" in url:
                return _FakeResp(png)
            raise AssertionError(f"URL inatteso: {url}")

        with mock.patch.object(urllib.request, "urlopen", side_effect=_fake_urlopen), \
             mock.patch("time.sleep", return_value=None):
            out = cs._call_comfyui_image("un prompt di scena", kind="scene")
        # deve restituire il PNG in base64
        self.assertEqual(_b64.b64decode(out), png)

    def test_submit_failure_returns_none(self):
        import urllib.request

        def _boom(req, timeout=None):
            raise OSError("connessione rifiutata")

        with mock.patch.object(urllib.request, "urlopen", side_effect=_boom), \
             mock.patch("time.sleep", return_value=None):
            out = cs._call_comfyui_image("prompt", kind="scene")
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
