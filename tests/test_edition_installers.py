import hashlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
text = (ROOT / 'scripts/INSTALAR-TLAMATINI-EDICIONES.sh').read_text()
code = text.split("<<'PYTHON'\n", 1)[1].rsplit('\nPYTHON', 1)[0]
installer = types.ModuleType('linux_edition_installer')
exec(compile(code, 'linux_edition_installer', 'exec'), installer.__dict__)


def expected(data):
    return {'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class EditionInstallerTests(unittest.TestCase):
    def test_catalog_selects_three_linux_editions(self):
        catalog = json.loads((ROOT / 'installer/ediciones.json').read_text())
        self.assertEqual(len(catalog['editions']), 6)
        for edition, ram, model in [('sin-ia', None, None), ('ia-4gb', 4, 'Gemma 3 1B Q4_K_M'), ('ia-8gb', 8, 'Gemma 3 4B Q4_K_M')]:
            item = installer.select_edition(catalog, edition)
            self.assertEqual(item['ram_recommended_gib'], ram)
            self.assertEqual(item['model'], model)

    def test_verified_file_is_reused_and_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'installer.deb'
            payload = b'complete installer'
            item = dict(expected(payload), url='https://example.invalid/installer')
            path.write_bytes(payload)
            with mock.patch.object(installer.urllib.request, 'urlopen') as network:
                installer.download_file(item, path)
                network.assert_not_called()
            path.write_bytes(b'corrupt installer!')
            self.assertFalse(installer.valid_file(path, item))

    def test_failed_download_never_replaces_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'installer.deb'
            path.write_bytes(b'previous')
            item = dict(expected(b'expected'), url='https://example.invalid/installer')
            with mock.patch.object(installer.urllib.request, 'urlopen', return_value=io.BytesIO(b'tampered')):
                with self.assertRaises(RuntimeError):
                    installer.download_file(item, path)
            self.assertEqual(path.read_bytes(), b'previous')
            self.assertFalse(path.with_name(path.name + '.download').exists())

    def test_valid_download_streams_and_is_verified(self):
        payload = b'x' * (3 * 1024 * 1024)
        class Stream(io.BytesIO):
            def read(self, size=-1):
                if size < 0:
                    raise AssertionError('Installer must not load the complete download into memory')
                return super().read(size)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'installer.deb'
            item = dict(expected(payload), url='https://example.invalid/installer')
            with mock.patch.object(installer.urllib.request, 'urlopen', return_value=Stream(payload)):
                installer.download_file(item, path)
            self.assertTrue(installer.valid_file(path, item))

    def test_parts_are_joined_in_order_and_final_checksum_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            parts = [folder / 'one', folder / 'two']
            parts[0].write_bytes(b'first-')
            parts[1].write_bytes(b'second')
            output = folder / 'installer.deb'
            installer.assemble_files(parts, output, expected(b'first-second'))
            self.assertEqual(output.read_bytes(), b'first-second')
            parts[1].write_bytes(b'tamper')
            with self.assertRaises(RuntimeError):
                installer.assemble_files(parts, output, expected(b'other-valid-installer'))
            self.assertEqual(output.read_bytes(), b'first-second')
            self.assertFalse(output.with_name(output.name + '.assembling').exists())

    def test_catalog_cannot_write_outside_download_folder(self):
        catalog = json.loads((ROOT / 'installer/ediciones.json').read_text())
        catalog['editions']['linux-sin-ia']['downloads'][0]['name'] = '../outside.deb'
        with self.assertRaises(RuntimeError):
            installer.select_edition(catalog, 'sin-ia')
