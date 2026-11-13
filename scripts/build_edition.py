#!/usr/bin/env python3
"""Build one edition at a time, without loading an AI model."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import local_ai_tool as release

MODEL_URL = 'https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf'
MODEL_SHA256 = '8ccc5cd1f1b3602548715ae25a66ed73fd5dc68a210412eea643eb20eb75a135'
MODEL_SIZE = 806058240


def verified_model(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size != MODEL_SIZE:
        return False
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest() == MODEL_SHA256


def prepare_ai(bundle: Path, model: Path) -> None:
    if not verified_model(model):
        raise RuntimeError(f'Modelo 1B ausente o SHA-256 incorrecto: {model}')
    target = bundle / 'local_ai'
    (target / 'config').mkdir(parents=True, exist_ok=True)
    (target / 'models/gemma3').mkdir(parents=True, exist_ok=True)
    shutil.copy2(model, target / 'models/gemma3/model.gguf')
    runtime = ROOT / 'local_ai/runtime'
    if not (runtime / 'bin' / ('llama-server.exe' if os.name == 'nt' else 'llama-server')).is_file():
        os.environ['TLAMATINI_AI_BACKEND'] = 'local'
        if release.setup_local_ai() != 0:
            raise RuntimeError('No se pudo preparar el runtime nativo.')
    shutil.copytree(runtime, target / 'runtime', dirs_exist_ok=True)
    config = {'profile': 'safe', 'host': '127.0.0.1', 'timeout': 60,
              'context_window': 1024, 'autostart': True, 'warmup_retries': 120,
              'warmup_sleep': 0.5, 'threads': 2, 'threads_batch': 2,
              'batch_size': 64, 'ubatch_size': 32, 'parallel': 1,
              'cache_ram': 0, 'poll': 0, 'webui': False,
              'accelerator': 'cpu', 'gpu_layers': '0'}
    (target / 'config/runtime.json').write_text(json.dumps(config, indent=2))
    models = {'models': {'gemma3': {'alias': 'gemma3:1b', 'role': 'primary',
              'port': 18437, 'path': 'local_ai/models/gemma3/model.gguf', 'context_window': 1024}}}
    (target / 'config/models.json').write_text(json.dumps(models, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edition', choices=['no-ai', 'ai-4gb'])
    parser.add_argument('--model', type=Path, default=ROOT / 'local_ai/downloads/editions/gemma-3-1b-it-Q4_K_M.gguf')
    parser.add_argument('--reuse-executable', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update(TLAMATINI_EDITION=args.edition, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    bundle = ROOT / 'dist' / args.edition
    bundle.mkdir(parents=True, exist_ok=True)
    if args.edition == 'no-ai' and (bundle / 'local_ai').exists():
        raise RuntimeError('La carpeta sin IA contiene local_ai; use una carpeta limpia.')
    if not args.reuse_executable:
        command = [*release._pyinstaller_command(), '--noconfirm', '--distpath', str(bundle), 'pyinstaller.spec']
        if sys.platform.startswith('linux'):
            command = ['prlimit', '--as=1610612736', '--', *command]
        subprocess.run(command, check=True)
    from PyInstaller.archive.readers import CArchiveReader
    entry = bundle / ('TLAMATINI.exe' if os.name == 'nt' else 'TLAMATINI')
    marker = json.loads(CArchiveReader(str(entry)).extract('edition.json'))
    if marker['edition'] != args.edition:
        raise RuntimeError('El ejecutable pertenece a otra edición.')
    if args.edition == 'ai-4gb':
        prepare_ai(bundle, args.model)
    manifest = {'app': 'TLAMATINI', 'version': '5.2.6', 'edition': args.edition,
                'platform': release._host_platform_tag(), 'model': 'gemma3:1b-Q4_K_M' if args.edition == 'ai-4gb' else None,
                'target_ram_gb': 4 if args.edition == 'ai-4gb' else None}
    (bundle / 'edition.json').write_text(json.dumps(manifest, indent=2))
    print(f'Edición preparada sin ejecutar IA: {bundle}')


if __name__ == '__main__':
    main()
