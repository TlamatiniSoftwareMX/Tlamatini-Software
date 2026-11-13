#!/usr/bin/env python3
"""Inspect an installed release in an ephemeral native runner. No build is performed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import psutil
from PyInstaller.archive.readers import CArchiveReader


def stop_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            try: child.terminate()
            except psutil.Error: pass
        try: parent.terminate()
        except psutil.Error: pass
        _, alive = psutil.wait_procs(children + [parent], timeout=8)
        for child in alive:
            try: child.kill()
            except psutil.Error: pass
        process.wait(timeout=10)
    except (psutil.Error, subprocess.TimeoutExpired):
        pass


def windows_text(pids):
    import ctypes
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    results = []
    def get_text(handle):
        buffer = ctypes.create_unicode_buffer(4096)
        user32.GetWindowTextW(handle, buffer, len(buffer))
        return buffer.value
    def visit(handle, _):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(handle):
            texts = [get_text(handle)]
            def child_visit(child, _):
                text = get_text(child)
                if text: texts.append(text)
                return True
            user32.EnumChildWindows(handle, callback_type(child_visit), 0)
            results.append(' | '.join(texts))
        return True
    user32.EnumWindows(callback_type(visit), 0)
    return results


def gui_smoke(executable, folder, env):
    logfile = folder / 'gui.log'
    result = {}
    with logfile.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([str(executable), '--no-ai'], stdout=log, stderr=subprocess.STDOUT, env=env, cwd=executable.parent)
        try:
            time.sleep(18)
            result['alive_after_18_seconds'] = process.poll() is None
            if sys.platform == 'win32':
                pids = {process.pid}
                try: pids.update(c.pid for c in psutil.Process(process.pid).children(recursive=True))
                except psutil.Error: pass
                result['windows'] = windows_text(pids)
                try:
                    from PIL import ImageGrab
                    ImageGrab.grab().save(folder / 'gui.png')
                except Exception as error: result['screenshot_error'] = str(error)
            else:
                scan = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', 'TLAMATINI'], text=True, capture_output=True)
                names = []
                for handle in scan.stdout.split():
                    value = subprocess.run(['xdotool', 'getwindowname', handle], text=True, capture_output=True).stdout.strip()
                    if value: names.append(value)
                result['windows'] = names
                subprocess.run(['import', '-window', 'root', str(folder / 'gui.png')], timeout=15, check=False)
        finally:
            stop_tree(process)
    text = logfile.read_text(encoding='utf-8', errors='replace')
    result['fatal_output'] = any(value in text.lower() for value in ['traceback (most recent call last)', 'error fatal de arranque', 'failed to execute script'])
    result['success'] = result['alive_after_18_seconds'] and bool(result.get('windows')) and not result['fatal_output']
    if any('no se pudo iniciar' in title.lower() or 'error fatal' in title.lower() for title in result.get('windows', [])):
        result['success'] = False
    return result


def runtime_smoke(root, folder, expected):
    runtime = root / 'local_ai/runtime/bin' / ('llama-server.exe' if sys.platform == 'win32' else 'llama-server')
    model = root / 'local_ai/models/gemma3/model.gguf'
    result = {'runtime_present': runtime.is_file(), 'model_present': model.is_file()}
    if not runtime.is_file() or not model.is_file():
        return dict(result, success=False)
    result['model_size_bytes'] = model.stat().st_size
    with model.open('rb') as stream: result['gguf_magic_valid'] = stream.read(4) == b'GGUF'
    if expected['ram_recommended_gib'] == 4:
        with model.open('rb') as stream: result['model_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        result['expected_model_valid'] = result['model_sha256'] == '8ccc5cd1f1b3602548715ae25a66ed73fd5dc68a210412eea643eb20eb75a135'
    else:
        result['expected_model_valid'] = 2_000_000_000 < model.stat().st_size < 4_000_000_000
    if not result['gguf_magic_valid'] or not result['expected_model_valid']:
        return dict(result, success=False)
    config = json.loads((root / 'local_ai/config/runtime.json').read_text(encoding='utf-8'))
    models = json.loads((root / 'local_ai/config/models.json').read_text(encoding='utf-8'))
    result['configuration'] = config
    context = models.get('models', {}).get('gemma3', {}).get('context_window', config.get('context_window', 2048))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    args = [str(runtime), '-m', str(model), '--host', '127.0.0.1', '--port', str(port), '-c', str(context),
            '-t', str(config.get('threads', 2)), '-tb', str(config.get('threads_batch', 2)),
            '-b', str(config.get('batch_size', 256)), '-ub', str(config.get('ubatch_size', 128)),
            '-np', str(config.get('parallel', 1)), '--cache-ram', str(config.get('cache_ram', 256)),
            '--poll', str(config.get('poll', 0)), '--poll-batch', str(config.get('poll', 0)), '--no-webui', '-ngl', '0']
    env = os.environ.copy()
    if sys.platform != 'win32': env['LD_LIBRARY_PATH'] = str(runtime.parent) + ':' + env.get('LD_LIBRARY_PATH', '')
    peak = [0]; done = threading.Event()
    with (folder / 'runtime.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, cwd=root, env=env)
        def sample():
            while not done.wait(0.2):
                try:
                    rss = psutil.Process(process.pid).memory_info().rss
                    peak[0] = max(peak[0], rss)
                    if rss > (3 if expected['ram_recommended_gib'] == 4 else 5) * 1024**3:
                        result['memory_limit_exceeded'] = True
                        process.terminate()
                except psutil.Error: return
        monitor = threading.Thread(target=sample, daemon=True); monitor.start()
        try:
            start = time.monotonic(); deadline = start + 180
            while time.monotonic() < deadline:
                if process.poll() is not None: raise RuntimeError(f'Runtime exited: {process.returncode}')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as response:
                        if response.status == 200: break
                except Exception: time.sleep(0.5)
            else: raise RuntimeError('Runtime not ready after 180 seconds')
            result['startup_seconds'] = round(time.monotonic() - start, 2)
            request = urllib.request.Request(f'http://127.0.0.1:{port}/completion', data=json.dumps({'prompt':'<start_of_turn>user\nResponde en español: ¿cuánto es dos más dos?<end_of_turn>\n<start_of_turn>model\n','n_predict':32,'temperature':0}).encode(), headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request, timeout=90) as response: data = json.load(response)
            result['response'] = data.get('content', '').strip()
            result['success'] = bool(result['response'])
        except Exception as error:
            result.update(success=False, error=str(error))
        finally:
            done.set(); monitor.join(timeout=2); stop_tree(process)
    result['peak_runtime_rss_bytes'] = peak[0]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--edition', required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--install-code', type=int, default=0)
    args = parser.parse_args()
    platform = 'windows' if sys.platform == 'win32' else 'linux'
    expected = json.loads(Path('installer/ediciones.json').read_text(encoding='utf-8'))['editions'][platform+'-'+args.edition]
    folder = args.output / (platform+'-'+args.edition); folder.mkdir(parents=True, exist_ok=True)
    report = {'platform': platform, 'edition': args.edition, 'install_exit_code': args.install_code, 'expected': expected, 'checks': {}, 'warnings': []}
    executable = args.root / ('TLAMATINI.exe' if platform == 'windows' else 'TLAMATINI')
    try:
        if args.install_code: raise RuntimeError('Published installation command failed')
        if not executable.is_file(): raise RuntimeError('Installed executable missing')
        archive = CArchiveReader(str(executable))
        names = [name for name in archive.toc if name.lower().endswith('.pyz')]
        modules = archive.open_embedded_archive(names[0]).toc
        report['feature_modules'] = {name: name in modules for name in ['tkinter','PIL','numpy','cv2','cryptography','requests','pmtiles','tkinterdnd2','fitz','pymupdf','pytesseract']}
        for name, feature in [('fitz','PDF'),('pytesseract','OCR'),('cv2','camera')]:
            if name not in modules and (name != 'fitz' or 'pymupdf' not in modules): report['warnings'].append(feature+' module missing from executable')
        if 'edition.json' in archive.toc:
            marker = json.loads(archive.extract('edition.json'))
            report['embedded_edition'] = marker
            report['checks']['edition_marker'] = marker['edition'] == {'sin-ia':'no-ai','ia-4gb':'ai-4gb','ia-8gb':'full'}[args.edition]
        else:
            report['checks']['edition_marker'] = args.edition == 'ia-8gb'
        if args.edition == 'sin-ia':
            report['checks']['no_ai_payload'] = not (args.root / 'local_ai').exists()
        if platform == 'linux':
            control = subprocess.check_output(['dpkg-query','-W','-f=${Version}','tlamatini'],text=True).strip()
            report['installed_package_version'] = control
            report['checks']['package_version'] = control == expected['package_version']
            report['package_dependencies'] = subprocess.check_output(['dpkg-query','-W','-f=${Depends}','tlamatini'],text=True)
            if not report['package_dependencies']: report['warnings'].append('DEB declares no runtime system dependencies')
        help_run = subprocess.run([str(executable),'--help'],capture_output=True,text=True,timeout=45,cwd=args.root)
        report['help_exit_code'] = help_run.returncode
        report['checks']['help'] = help_run.returncode == 0
        env = os.environ.copy(); env['TLAMATINI_HOME'] = str(folder / 'user-data')
        report['gui'] = gui_smoke(executable, folder, env)
        report['checks']['gui'] = report['gui']['success']
        if args.edition != 'sin-ia':
            report['runtime'] = runtime_smoke(args.root, folder, expected)
            report['checks']['runtime'] = report['runtime']['success']
        report['success'] = all(report['checks'].values())
    except Exception as error:
        report.update(success=False,error=str(error))
    (folder / 'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['expected']},ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__': main()
