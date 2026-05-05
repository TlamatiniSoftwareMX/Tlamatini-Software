import os
import unittest
from unittest import mock

from core import ai_bootstrap, local_llm, model_router


class AIBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)

    def test_primary_model_reads_env_dynamically(self):
        os.environ["TLAMATINI_PRIMARY_MODEL"] = "mistral:latest"
        self.assertEqual(model_router.primary_model(), "mistral")
        os.environ["TLAMATINI_PRIMARY_MODEL"] = "llama3:latest"
        self.assertEqual(model_router.primary_model(), "llama3")

    def test_choose_ollama_model_prefers_canonical_match(self):
        selected = ai_bootstrap.choose_ollama_model(
            "gemma3:4b",
            ["gemma3:latest", "llama3:latest"],
        )
        self.assertEqual(selected, "gemma3:latest")

    def test_choose_ollama_model_falls_back_to_first_supported(self):
        selected = ai_bootstrap.choose_ollama_model(
            "gemma3:4b",
            ["mistral:latest", "otro-modelo:latest"],
        )
        self.assertEqual(selected, "mistral:latest")

    def test_apply_ollama_model_selection_updates_runtime_env(self):
        ai_bootstrap.apply_ollama_model_selection("mistral:latest")
        self.assertEqual(os.environ["TLAMATINI_LOCAL_LLM_MODEL"], "mistral:latest")
        self.assertEqual(os.environ["TLAMATINI_PRIMARY_MODEL"], "mistral")
        self.assertEqual(os.environ["TLAMATINI_ENABLE_MISTRAL"], "1")

    def test_bootstrap_ollama_pulls_missing_preferred_model(self):
        os.environ["TLAMATINI_LOCAL_LLM_MODEL"] = "gemma3:4b"

        with (
            mock.patch("core.ai_bootstrap.ensure_local_ollama", return_value=(True, "ok")),
            mock.patch("core.ai_bootstrap.list_ollama_models", side_effect=[[], ["gemma3:4b"]]),
            mock.patch("core.ai_bootstrap.pull_ollama_model", return_value=(True, "pulled")) as pull_mock,
        ):
            ok, _mensaje, selected = ai_bootstrap.bootstrap_ollama_model("http://127.0.0.1:11436", auto_pull=True)

        self.assertTrue(ok)
        self.assertEqual(selected, "gemma3:4b")
        pull_mock.assert_called_once()

    def test_local_llm_provider_reads_backend_dynamically(self):
        os.environ["TLAMATINI_AI_BACKEND"] = "local"
        provider = local_llm.obtener_local_llm_provider()
        self.assertIsInstance(provider, local_llm.TlamatiniLocalProvider)
        os.environ["TLAMATINI_AI_BACKEND"] = "ollama"
        provider = local_llm.obtener_local_llm_provider()
        self.assertIsInstance(provider, local_llm.OllamaProvider)


if __name__ == "__main__":
    unittest.main()
