import atexit
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from core.path_manager import default_ollama_models_dir, local_ai_logs_dir


_LOCAL_PROCESS: Optional[subprocess.Popen] = None


def configured_ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11436").strip() or "http://127.0.0.1:11436"


def configured_ollama_models_dir() -> Path:
    return Path(os.environ.get("OLLAMA_MODELS", "").strip() or str(default_ollama_models_dir())).expanduser().resolve()


def configured_ollama_bin() -> str:
    return os.environ.get("TLAMATINI_OLLAMA_BIN", "").strip() or (shutil.which("ollama") or "ollama")


def configured_ollama_log() -> Path:
    return Path(os.environ.get("TLAMATINI_OLLAMA_LOG", "").strip() or str(local_ai_logs_dir() / "ollama_local.log"))


def _host_for_server(host: str) -> str:
    limpio = (host or configured_ollama_host()).strip()
    return limpio.replace("http://", "").replace("https://", "")


def _request(host: str, path: str, timeout: float = 2.0) -> dict:
    req = urllib.request.Request(f"{host.rstrip('/')}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_reachable(host: Optional[str] = None) -> bool:
    try:
        _request(host or configured_ollama_host(), "/api/version", timeout=1.5)
        return True
    except Exception:
        return False


def list_ollama_models(host: Optional[str] = None) -> list[str]:
    data = _request(host or configured_ollama_host(), "/api/tags", timeout=5.0)
    return [str(item.get("name", "")).strip() for item in data.get("models", []) if str(item.get("name", "")).strip()]


def pull_ollama_model(model_name: str, host: Optional[str] = None, timeout_seconds: int = 1800) -> Tuple[bool, str]:
    model = str(model_name or "").strip()
    if not model:
        return False, "No se definió un modelo de Ollama para descargar."

    env = os.environ.copy()
    env["OLLAMA_HOST"] = _host_for_server(host or configured_ollama_host())
    models_dir = configured_ollama_models_dir()
    models_dir.mkdir(parents=True, exist_ok=True)
    env["OLLAMA_MODELS"] = str(models_dir)

    ollama_bin = configured_ollama_bin()
    if shutil.which(ollama_bin) is None and not Path(ollama_bin).exists():
        return False, f"No se encontró el binario de Ollama: {ollama_bin}"

    try:
        result = subprocess.run(
            [ollama_bin, "pull", model],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        return False, f"No se pudo descargar el modelo {model}: {exc}"

    if result.returncode != 0:
        detalle = (result.stderr or result.stdout or "").strip()
        return False, f"Falló la descarga del modelo {model}: {detalle or 'sin detalle'}"
    return True, f"Modelo descargado en Ollama: {model}"


def ensure_local_ollama(host: Optional[str] = None) -> Tuple[bool, str]:
    global _LOCAL_PROCESS

    host = host or configured_ollama_host()
    if ollama_reachable(host):
        return True, f"Ollama disponible en {host}."

    if _LOCAL_PROCESS and _LOCAL_PROCESS.poll() is None:
        for _ in range(10):
            if ollama_reachable(host):
                return True, f"Ollama disponible en {host}."
            time.sleep(0.5)
        return False, f"Ollama sigue iniciando en {host}, pero aún no responde."
    _LOCAL_PROCESS = None

    models_dir = configured_ollama_models_dir()
    models_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["OLLAMA_HOST"] = _host_for_server(host)
    env["OLLAMA_VULKAN"] = env.get("OLLAMA_VULKAN", "1")
    env["OLLAMA_MODELS"] = str(models_dir)
    env.setdefault("OLLAMA_KEEP_ALIVE", "30m")
    ollama_log = configured_ollama_log()
    ollama_log.parent.mkdir(parents=True, exist_ok=True)
    ollama_bin = configured_ollama_bin()
    if shutil.which(ollama_bin) is None and not Path(ollama_bin).exists():
        return False, f"No se encontró el binario de Ollama: {ollama_bin}"

    try:
        log_handle = open(ollama_log, "ab")
        _LOCAL_PROCESS = subprocess.Popen(
            [ollama_bin, "serve"],
            env=env,
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
        )
    except Exception as exc:
        return False, f"No se pudo iniciar Ollama local: {exc}"

    for _ in range(30):
        if ollama_reachable(host):
            return True, f"Ollama local iniciado en {host} con Vulkan."
        time.sleep(0.5)

    return False, f"Ollama no respondió en {host} tras iniciar el backend local. Revisa {ollama_log}."


def stop_local_ollama() -> None:
    global _LOCAL_PROCESS
    process = _LOCAL_PROCESS
    _LOCAL_PROCESS = None
    if not process:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            pass


atexit.register(stop_local_ollama)
