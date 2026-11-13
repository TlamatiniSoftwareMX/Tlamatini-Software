import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
from core import edition, local_llm


class EditionTests(unittest.TestCase):
    def test_embedded_no_ai_cannot_enable_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'edition.json').write_text(json.dumps({'edition': 'no-ai'}))
            with mock.patch.object(edition.sys, '_MEIPASS', tmp, create=True), mock.patch.dict(os.environ, {'TLAMATINI_AI_BACKEND': 'ollama'}):
                args = argparse.Namespace(no_ai=False, safe=False, fast=False, with_mistral=False)
                main._apply_cli_overrides(args)
                self.assertTrue(args.no_ai)
                self.assertEqual(os.environ['TLAMATINI_AI_AUTO_PULL'], '0')
                with mock.patch.object(local_llm, 'OllamaProvider') as ollama, mock.patch.object(local_llm, 'TlamatiniLocalProvider') as local:
                    provider = local_llm.obtener_local_llm_provider()
                    self.assertFalse(provider.is_available()[0])
                    with self.assertRaises(RuntimeError):
                        provider.generate('hola')
                    ollama.assert_not_called()
                    local.assert_not_called()

    def test_full_edition_retains_ai(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'edition.json').write_text('{"edition": "full"}')
            with mock.patch.object(edition.sys, '_MEIPASS', tmp, create=True):
                self.assertFalse(edition.ai_disabled())

    def test_low_ram_edition_forces_conservative_settings(self):
        with mock.patch.object(main, 'edition_name', return_value='ai-4gb'), mock.patch.dict(os.environ, {}, clear=True):
            args = argparse.Namespace(no_ai=False, safe=False, fast=True, with_mistral=True)
            main._apply_cli_overrides(args)
            self.assertTrue(args.safe)
            self.assertFalse(args.fast)
            self.assertFalse(args.with_mistral)
            self.assertEqual(os.environ['TLAMATINI_AI_THREADS'], '2')
            self.assertEqual(os.environ['TLAMATINI_AI_STOP_ON_EXIT'], '1')
            self.assertEqual(os.environ['TLAMATINI_LOCAL_LLM_MODEL'], 'gemma3:1b')
