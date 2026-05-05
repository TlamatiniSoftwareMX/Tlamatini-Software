import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from core.logs import registrar_log
from core.model_router import primary_model
from core.path_manager import PROJECT_ROOT as APP_PROJECT_ROOT, local_ai_logs_dir, local_ai_models_dir, local_ai_root, local_ai_runtime_dir


PROJECT_ROOT = APP_PROJECT_ROOT
BUNDLED_LOCAL_AI_ROOT = PROJECT_ROOT / "local_ai"
BUNDLED_LOCAL_AI_READY = (BUNDLED_LOCAL_AI_ROOT / "config").exists() and (BUNDLED_LOCAL_AI_ROOT / "runtime").exists() and (BUNDLED_LOCAL_AI_ROOT / "models").exists()
USER_LOCAL_AI_ROOT = local_ai_root()
LOCAL_AI_ROOT = BUNDLED_LOCAL_AI_ROOT if BUNDLED_LOCAL_AI_READY else local_ai_root()
CONFIG_DIR = LOCAL_AI_ROOT / "config"
RUNTIME_DIR = LOCAL_AI_ROOT / "runtime"
RUNTIME_BIN_DIR = RUNTIME_DIR / "bin"
MODELS_DIR = LOCAL_AI_ROOT / "models"
LOGS_DIR = local_ai_logs_dir()
TEMP_DIR = USER_LOCAL_AI_ROOT / "temp"

DEFAULT_HOST = os.environ.get("TLAMATINI_AI_HOST", "127.0.0.1").strip() or "127.0.0.1"
DEFAULT_TIMEOUT = int(os.environ.get("TLAMATINI_AI_TIMEOUT", "12"))
DEFAULT_CONTEXT = int(os.environ.get("TLAMATINI_AI_CONTEXT", "2048"))
DEFAULT_AUTOSTART = os.environ.get("TLAMATINI_AI_AUTOSTART", "1").strip().lower() not in {"0", "false", "no"}
DEFAULT_WARMUP_RETRIES = int(os.environ.get("TLAMATINI_AI_WARMUP_RETRIES", "2"))
DEFAULT_WARMUP_SLEEP = float(os.environ.get("TLAMATINI_AI_WARMUP_SLEEP", "0.25"))
DEFAULT_BOOT_MODEL = os.environ.get("TLAMATINI_AI_BOOT_MODEL", "").strip().lower() or primary_model()
DEFAULT_PROFILE = os.environ.get("TLAMATINI_AI_PROFILE", "").strip().lower() or "fast"
DEFAULT_ACCELERATOR = os.environ.get("TLAMATINI_AI_ACCELERATOR", "").strip().lower() or "auto"


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _normalizar_n_predict(value, default: int = 512) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    if parsed <= 0:
        return default
    return parsed


def _cpu_count() -> int:
    return max(2, int(os.cpu_count() or 4))


def _profile_defaults(profile: str) -> Dict[str, int]:
    logical = _cpu_count()
    if profile == "safe":
        return {
            "threads": _clamp(logical // 3, 2, 4),
            "threads_batch": _clamp(logical // 3, 2, 4),
            "context_window": 2048,
            "batch_size": 256,
            "ubatch_size": 128,
            "parallel": 1,
            "cache_ram": 256,
            "poll": 0,
        }
    if profile == "fast":
        return {
            "threads": _clamp(logical - 2, 4, 8),
            "threads_batch": _clamp(logical - 2, 4, 8),
            "context_window": 4096,
            "batch_size": 1024,
            "ubatch_size": 512,
            "parallel": 1,
            "cache_ram": 1024,
            "poll": 10,
        }
    return {
        "threads": _clamp(logical // 2, 4, 6),
        "threads_batch": _clamp(logical // 2, 4, 6),
        "context_window": 3072,
        "batch_size": 512,
        "ubatch_size": 256,
        "parallel": 1,
        "cache_ram": 512,
        "poll": 0,
    }


@dataclass
class ManagedModel:
    model_id: str
    alias: str
    role: str
    port: int
    model_path: Path
    log_path: Path
    pid_path: Path
    host: str = DEFAULT_HOST
    context_window: int = DEFAULT_CONTEXT
    threads: int = 0
    threads_batch: int = 0
    batch_size: int = 0
    ubatch_size: int = 0
    parallel: int = 1
    cache_ram: int = 0
    poll: int = 0
    accelerator: str = "cpu"
    gpu_layers: str = "0"
    webui: bool = False
    using_gpu: bool = False


def _runtime_binary_name() -> str:
    if os.name == "nt":
        return "llama-server.exe"
    return "llama-server"


def _runtime_binary_path() -> Path:
    env = os.environ.get("TLAMATINI_AI_RUNTIME_BIN", "").strip()
    if env:
        return (PROJECT_ROOT / env).resolve() if not Path(env).is_absolute() else Path(env).resolve()
    return (RUNTIME_BIN_DIR / _runtime_binary_name()).resolve()


def _load_models_config() -> Dict:
    path = CONFIG_DIR / "models.json"
    if not path.exists():
        return {"models": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_runtime_config() -> Dict:
    path = CONFIG_DIR / "runtime.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_int(value: object, fallback: int) -> int:
    try:
        parsed = int(str(value).strip())
        return parsed if parsed > 0 else fallback
    except Exception:
        return fallback


def _resolve_bool(value: object, fallback: bool) -> bool:
    raw = str(value).strip().lower()
    if not raw:
        return fallback
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return fallback


def _resolve_relative_path(raw: str, default: Path) -> Path:
    valor = (raw or "").strip()
    if not valor:
        return default.resolve()
    ruta = Path(valor)
    if ruta.is_absolute():
        return ruta.resolve()
    return (PROJECT_ROOT / ruta).resolve()


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.3)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def _reserve_free_port(host: str) -> Optional[int]:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])
    except OSError:
        return None


class LocalInferenceService:
    def __init__(self):
        self.runtime_config = _load_runtime_config()
        self.models_config = _load_models_config()
        self.runtime_binary = _runtime_binary_path()
        self.profile = str(self.runtime_config.get("profile", DEFAULT_PROFILE) or DEFAULT_PROFILE).strip().lower() or "balanced"
        if self.profile not in {"safe", "balanced", "fast"}:
            self.profile = "balanced"
        self.profile_defaults = _profile_defaults(self.profile)
        self.host = str(self.runtime_config.get("host", DEFAULT_HOST) or DEFAULT_HOST)
        self.timeout = int(self.runtime_config.get("timeout", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
        self.context_window = int(
            self.runtime_config.get("context_window", self.profile_defaults["context_window"])
            or self.profile_defaults["context_window"]
        )
        self.autostart = bool(self.runtime_config.get("autostart", DEFAULT_AUTOSTART))
        self.warmup_retries = int(self.runtime_config.get("warmup_retries", DEFAULT_WARMUP_RETRIES) or DEFAULT_WARMUP_RETRIES)
        self.warmup_sleep = float(self.runtime_config.get("warmup_sleep", DEFAULT_WARMUP_SLEEP) or DEFAULT_WARMUP_SLEEP)
        self.threads = _resolve_int(
            os.environ.get("TLAMATINI_AI_THREADS", self.runtime_config.get("threads", "")),
            self.profile_defaults["threads"],
        )
        self.threads_batch = _resolve_int(
            os.environ.get("TLAMATINI_AI_THREADS_BATCH", self.runtime_config.get("threads_batch", "")),
            self.profile_defaults["threads_batch"],
        )
        self.batch_size = _resolve_int(
            os.environ.get("TLAMATINI_AI_BATCH_SIZE", self.runtime_config.get("batch_size", "")),
            self.profile_defaults["batch_size"],
        )
        self.ubatch_size = _resolve_int(
            os.environ.get("TLAMATINI_AI_UBATCH_SIZE", self.runtime_config.get("ubatch_size", "")),
            self.profile_defaults["ubatch_size"],
        )
        self.parallel = _resolve_int(
            os.environ.get("TLAMATINI_AI_PARALLEL", self.runtime_config.get("parallel", "")),
            self.profile_defaults["parallel"],
        )
        self.cache_ram = _resolve_int(
            os.environ.get("TLAMATINI_AI_CACHE_RAM", self.runtime_config.get("cache_ram", "")),
            self.profile_defaults["cache_ram"],
        )
        self.poll = max(0, int(str(os.environ.get("TLAMATINI_AI_POLL", self.runtime_config.get("poll", self.profile_defaults["poll"]))).strip() or self.profile_defaults["poll"]))
        self.webui = _resolve_bool(
            os.environ.get("TLAMATINI_AI_WEBUI", self.runtime_config.get("webui", "")),
            False,
        )
        self.accelerator = str(
            os.environ.get("TLAMATINI_AI_ACCELERATOR", self.runtime_config.get("accelerator", DEFAULT_ACCELERATOR))
            or DEFAULT_ACCELERATOR
        ).strip().lower() or "auto"
        self.gpu_layers = str(
            os.environ.get("TLAMATINI_AI_GPU_LAYERS", self.runtime_config.get("gpu_layers", "auto"))
            or "auto"
        ).strip().lower()
        self.available_devices = self._list_runtime_devices()
        self.using_gpu = self.accelerator in {"auto", "gpu"} and bool(self.available_devices)
        self.port_overrides: Dict[str, int] = {}

    def _list_runtime_devices(self) -> List[str]:
        if not self.runtime_binary.exists():
            return []
        try:
            env = os.environ.copy()
            runtime_dir = str(self.runtime_binary.parent)
            if os.name != "nt":
                ld_path = env.get("LD_LIBRARY_PATH", "").strip()
                env["LD_LIBRARY_PATH"] = runtime_dir if not ld_path else f"{runtime_dir}:{ld_path}"
            result = subprocess.run(
                [str(self.runtime_binary), "--list-devices"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
                env=env,
            )
            devices = []
            for line in (result.stdout or "").splitlines():
                item = line.strip()
                if not item or item.lower().startswith("available devices"):
                    continue
                devices.append(item)
            return devices
        except Exception:
            return []

    def _managed_model(self, model_id: str) -> ManagedModel:
        model_data = dict((self.models_config.get("models", {}) or {}).get(model_id, {}))
        alias = str(model_data.get("alias", model_id) or model_id)
        role = str(model_data.get("role", model_id) or model_id)
        port = self._resolve_model_port(model_id, int(model_data.get("port", 0) or 0))
        default_model_path = MODELS_DIR / model_id / "model.gguf"
        model_path = _resolve_relative_path(str(model_data.get("path", "")), default_model_path)
        log_path = LOGS_DIR / f"{model_id}.log"
        pid_path = TEMP_DIR / f"{model_id}.pid"
        context_window = int(model_data.get("context_window", self.context_window) or self.context_window)
        return ManagedModel(
            model_id=model_id,
            alias=alias,
            role=role,
            port=port,
            model_path=model_path,
            log_path=log_path,
            pid_path=pid_path,
            host=self.host,
            context_window=context_window,
            threads=self.threads,
            threads_batch=self.threads_batch,
            batch_size=self.batch_size,
            ubatch_size=self.ubatch_size,
            parallel=self.parallel,
            cache_ram=self.cache_ram,
            poll=self.poll,
            accelerator=self.accelerator,
            gpu_layers=self.gpu_layers,
            webui=self.webui,
            using_gpu=self.using_gpu,
        )

    def _resolve_model_port(self, model_id: str, configured_port: int) -> int:
        if model_id in self.port_overrides:
            return self.port_overrides[model_id]

        preferred = configured_port if configured_port > 0 else 11437
        pid = self.read_pid(model_id)
        if pid and self.pid_is_running(pid):
            self.port_overrides[model_id] = preferred
            return preferred

        port = _reserve_free_port(self.host) or preferred
        self.port_overrides[model_id] = port
        return port

    def available_models(self) -> Dict[str, ManagedModel]:
        modelos = {}
        for model_id in (self.models_config.get("models", {}) or {}).keys():
            modelos[model_id] = self._managed_model(model_id)
        return modelos

    def startup_models(self) -> Dict[str, ManagedModel]:
        modelos = self.available_models()
        if DEFAULT_BOOT_MODEL in modelos:
            return {DEFAULT_BOOT_MODEL: modelos[DEFAULT_BOOT_MODEL]}
        principal = primary_model()
        if principal in modelos:
            return {principal: modelos[principal]}
        return modelos

    def managed_model(self, model_id: str) -> ManagedModel:
        return self._managed_model(model_id)

    def healthcheck_model(self, model_id: str) -> Tuple[bool, str]:
        return self._healthcheck(self._managed_model(model_id))

    def wait_until_ready(self, model_id: str, retries: Optional[int] = None, sleep_seconds: Optional[float] = None) -> Tuple[bool, str]:
        managed = self._managed_model(model_id)
        total_retries = retries if retries is not None else self.warmup_retries
        wait_time = sleep_seconds if sleep_seconds is not None else self.warmup_sleep
        for _ in range(max(1, total_retries)):
            ok, mensaje = self._healthcheck(managed)
            if ok:
                return True, mensaje
            time.sleep(max(0.1, wait_time))
        return False, f"Runtime de {model_id} no respondió a tiempo."

    def read_pid(self, model_id: str) -> Optional[int]:
        try:
            raw = (TEMP_DIR / f"{model_id}.pid").read_text(encoding="utf-8").strip()
            return int(raw) if raw else None
        except Exception:
            return None

    def pid_is_running(self, pid: Optional[int]) -> bool:
        if not pid or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def stop_model_process(self, model_id: str, timeout: float = 5.0) -> bool:
        managed = self._managed_model(model_id)
        pid = self.read_pid(model_id)
        if not self.pid_is_running(pid):
            managed.pid_path.unlink(missing_ok=True)
            return False
        try:
            os.kill(pid, 15)
        except OSError:
            managed.pid_path.unlink(missing_ok=True)
            return False
        deadline = time.time() + max(0.5, timeout)
        while time.time() < deadline:
            if not self.pid_is_running(pid):
                managed.pid_path.unlink(missing_ok=True)
                return True
            time.sleep(0.2)
        try:
            os.kill(pid, 9)
        except OSError:
            pass
        managed.pid_path.unlink(missing_ok=True)
        return True

    def _leer_error_modelo_desde_log(self, managed: ManagedModel) -> str:
        try:
            if not managed.log_path.exists():
                return ""
            lineas = managed.log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-120:]
        except Exception:
            return ""

        patrones = (
            "error loading model hyperparameters:",
            "failed to load model",
            "failed to load model '",
            "main: exiting due to model loading error",
            "error while loading shared libraries:",
        )
        encontrados = [linea.strip() for linea in lineas if any(p in linea.lower() for p in patrones)]
        if not encontrados:
            return ""

        detalle = next(
            (linea for linea in encontrados if "error loading model hyperparameters:" in linea.lower()),
            encontrados[-1],
        )
        detalle_l = detalle.lower()
        if "gemma3.attention.layer_norm_rms_epsilon" in detalle_l:
            return (
                "El runtime llama-server actual no soporta este GGUF de Gemma 3. "
                "Se necesita un runtime llama.cpp más reciente o un GGUF compatible con el runtime empaquetado."
            )
        if "error while loading shared libraries:" in detalle_l:
            return f"Fallo de bibliotecas del runtime: {detalle}"
        return detalle

    def _healthcheck(self, managed: ManagedModel) -> Tuple[bool, str]:
        if not _is_port_open(managed.host, managed.port):
            return False, f"Puerto {managed.port} no disponible para {managed.model_id}."
        for endpoint in (f"http://{managed.host}:{managed.port}/health", f"http://{managed.host}:{managed.port}/v1/models"):
            try:
                req = urllib.request.Request(endpoint, method="GET")
                with urllib.request.urlopen(req, timeout=2) as response:
                    if 200 <= response.status < 500:
                        return True, "Runtime activo."
            except Exception:
                continue
        return True, "Puerto activo."

    def _spawn_server(self, managed: ManagedModel) -> Tuple[bool, str]:
        if not self.runtime_binary.exists():
            return False, f"No se encontró runtime local en {self.runtime_binary.relative_to(PROJECT_ROOT)}."
        if not managed.model_path.exists():
            return False, f"No se encontró modelo local en {managed.model_path.relative_to(PROJECT_ROOT)}."
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        managed.pid_path.unlink(missing_ok=True)
        cmd = [
            str(self.runtime_binary),
            "-m",
            str(managed.model_path),
            "--host",
            managed.host,
            "--port",
            str(managed.port),
            "-c",
            str(managed.context_window),
            "-t",
            str(managed.threads),
            "-tb",
            str(managed.threads_batch),
            "-b",
            str(managed.batch_size),
            "-ub",
            str(managed.ubatch_size),
            "-np",
            str(managed.parallel),
            "--cache-ram",
            str(managed.cache_ram),
            "--poll",
            str(managed.poll),
            "--poll-batch",
            str(managed.poll),
        ]
        if not managed.webui:
            cmd.append("--no-webui")
        if managed.using_gpu:
            cmd.extend(["-ngl", managed.gpu_layers or "auto"])
        registrar_log(
            "info",
            (
                f"Activando runtime local para modelo={managed.model_id} perfil={self.profile} "
                f"host={managed.host} puerto={managed.port} ctx={managed.context_window} "
                f"threads={managed.threads}/{managed.threads_batch} batch={managed.batch_size}/{managed.ubatch_size} "
                f"parallel={managed.parallel} cache_ram={managed.cache_ram}MiB "
                f"aceleracion={'gpu-auto' if managed.using_gpu else 'cpu'} webui={'on' if managed.webui else 'off'}"
            ),
            "local_ai",
        )
        with managed.log_path.open("a", encoding="utf-8") as log_file:
            env = os.environ.copy()
            runtime_dir = str(self.runtime_binary.parent)
            if os.name != "nt":
                ld_path = env.get("LD_LIBRARY_PATH", "").strip()
                env["LD_LIBRARY_PATH"] = runtime_dir if not ld_path else f"{runtime_dir}:{ld_path}"
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_ROOT,
                env=env,
            )
        managed.pid_path.write_text(str(process.pid), encoding="utf-8")
        for _ in range(40):
            ok, mensaje = self._healthcheck(managed)
            if ok:
                return True, mensaje
            time.sleep(0.5)
        detalle_log = self._leer_error_modelo_desde_log(managed)
        if detalle_log:
            return False, detalle_log
        return False, f"Runtime de {managed.model_id} no respondió tras iniciar."

    def ensure_model_ready(self, model_id: str) -> Tuple[bool, str]:
        managed = self._managed_model(model_id)
        if managed.port <= 0:
            return False, f"Modelo {model_id} sin puerto configurado."
        ok, mensaje = self._healthcheck(managed)
        if ok:
            registrar_log(
                "info",
                (
                    f"Modelo local activo: modelo={managed.model_id} perfil={self.profile} "
                    f"host={managed.host} puerto={managed.port} ctx={managed.context_window} "
                    f"threads={managed.threads}/{managed.threads_batch} "
                    f"aceleracion={'gpu-auto' if managed.using_gpu else 'cpu'}"
                ),
                "local_ai",
            )
            return True, mensaje
        if not self.autostart:
            return False, "Autostart desactivado y runtime no activo."
        return self._spawn_server(managed)

    def is_available(self, model_id: Optional[str] = None) -> Tuple[bool, str]:
        modelos = [model_id] if model_id else list(self.available_models().keys())
        if not modelos:
            return False, "No hay modelos configurados."
        faltantes = []
        for item in modelos:
            managed = self._managed_model(item)
            if not managed.model_path.exists():
                faltantes.append(item)
        if faltantes:
            return False, f"Faltan modelos locales: {', '.join(faltantes)}."
        if not self.runtime_binary.exists():
            return False, f"Falta runtime local: {self.runtime_binary.relative_to(PROJECT_ROOT)}."
        if model_id:
            return self.ensure_model_ready(model_id)
        return True, "Runtime y modelos configurados."

    def generate(self, model_id: str, prompt: str, system_prompt: str = "", options: Optional[Dict] = None) -> str:
        managed = self._managed_model(model_id)
        ok, mensaje = self.ensure_model_ready(model_id)
        if not ok:
            raise RuntimeError(mensaje)
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "stream": False,
            "temperature": float((options or {}).get("temperature", 0.0)),
            "top_p": float((options or {}).get("top_p", 0.9)),
            "n_predict": _normalizar_n_predict((options or {}).get("max_tokens", 256)),
            "n_ctx": int((options or {}).get("context_window", managed.context_window)),
        }
        request_timeout = max(1.0, float((options or {}).get("timeout", self.timeout) or self.timeout))
        last_error = ""
        for endpoint in (f"http://{managed.host}:{managed.port}/completion", f"http://{managed.host}:{managed.port}/v1/completions"):
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            for intento in range(self.warmup_retries):
                try:
                    registrar_log(
                        "info",
                        f"Solicitud IA -> modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}",
                        "local_ai",
                    )
                    with urllib.request.urlopen(req, timeout=request_timeout) as response:
                        data = json.loads(response.read().decode("utf-8"))
                    if "content" in data:
                        text = str(data.get("content", "")).strip()
                        if not text:
                            last_error = "respuesta vacía"
                            time.sleep(min(1.0, self.warmup_sleep))
                            continue
                        registrar_log(
                            "info",
                            f"Respuesta IA <- modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}",
                            "local_ai",
                        )
                        return text
                    if "choices" in data and data["choices"]:
                        choice = data["choices"][0]
                        text = str(choice.get("text") or choice.get("message", {}).get("content", "")).strip()
                        if not text:
                            last_error = "respuesta vacía"
                            time.sleep(min(1.0, self.warmup_sleep))
                            continue
                        registrar_log(
                            "info",
                            f"Respuesta IA <- modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}",
                            "local_ai",
                        )
                        return text
                    last_error = "formato de respuesta no reconocido"
                except urllib.error.HTTPError as exc:
                    detalle = exc.read().decode("utf-8", errors="ignore").strip()
                    detalle_l = detalle.lower()
                    if exc.code == 503 and ("loading model" in detalle_l or "unavailable_error" in detalle_l) and intento < (self.warmup_retries - 1):
                        time.sleep(self.warmup_sleep)
                        continue
                    registrar_log(
                        "error",
                        f"Error IA modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}: {detalle or f'HTTP {exc.code}'}",
                        "local_ai",
                    )
                    raise RuntimeError(detalle or f"Runtime local devolvió HTTP {exc.code}.") from exc
                except Exception:
                    last_error = "timeout o conexión interrumpida"
                    if intento < (self.warmup_retries - 1):
                        time.sleep(min(1.0, self.warmup_sleep))
                        continue
                    break
        detalle = f" Último detalle: {last_error}." if last_error else ""
        raise RuntimeError(f"No se pudo generar respuesta con el modelo {model_id}.{detalle}")

    def generate_stream(self, model_id: str, prompt: str, system_prompt: str = "", options: Optional[Dict] = None) -> Iterator[str]:
        managed = self._managed_model(model_id)
        ok, mensaje = self.ensure_model_ready(model_id)
        if not ok:
            raise RuntimeError(mensaje)
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "stream": True,
            "temperature": float((options or {}).get("temperature", 0.0)),
            "top_p": float((options or {}).get("top_p", 0.9)),
            "n_predict": _normalizar_n_predict((options or {}).get("max_tokens", 256)),
            "n_ctx": int((options or {}).get("context_window", managed.context_window)),
        }
        request_timeout = max(1.0, float((options or {}).get("timeout", self.timeout) or self.timeout))
        last_error = ""
        for endpoint in (f"http://{managed.host}:{managed.port}/completion", f"http://{managed.host}:{managed.port}/v1/completions"):
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            for intento in range(self.warmup_retries):
                emitted = 0
                try:
                    registrar_log(
                        "info",
                        f"Stream IA -> modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}",
                        "local_ai",
                    )
                    with urllib.request.urlopen(req, timeout=request_timeout) as response:
                        for raw_line in response:
                            line = raw_line.decode("utf-8", errors="ignore").strip()
                            if not line:
                                continue
                            if line.startswith("data:"):
                                line = line[5:].strip()
                            if line == "[DONE]":
                                break
                            try:
                                data = json.loads(line)
                            except json.JSONDecodeError:
                                continue

                            text = str(data.get("content") or data.get("response") or "")
                            if not text and "choices" in data and data["choices"]:
                                choice = data["choices"][0]
                                text = str(
                                    choice.get("text")
                                    or choice.get("delta", {}).get("content", "")
                                    or choice.get("message", {}).get("content", "")
                                )
                            if text:
                                emitted += 1
                                yield text
                            if data.get("stop") or data.get("done"):
                                break
                    if emitted:
                        registrar_log(
                            "info",
                            f"Stream IA <- modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}",
                            "local_ai",
                        )
                        return
                    last_error = "stream sin contenido"
                    time.sleep(min(1.0, self.warmup_sleep))
                except urllib.error.HTTPError as exc:
                    detalle = exc.read().decode("utf-8", errors="ignore").strip()
                    detalle_l = detalle.lower()
                    if exc.code == 503 and ("loading model" in detalle_l or "unavailable_error" in detalle_l) and intento < (self.warmup_retries - 1):
                        time.sleep(self.warmup_sleep)
                        continue
                    registrar_log(
                        "error",
                        f"Error stream IA modelo={managed.model_id} ruta={managed.role} endpoint={endpoint}: {detalle or f'HTTP {exc.code}'}",
                        "local_ai",
                    )
                    raise RuntimeError(detalle or f"Runtime local devolvió HTTP {exc.code}.") from exc
                except Exception:
                    last_error = "timeout o conexión interrumpida"
                    if intento < (self.warmup_retries - 1):
                        time.sleep(min(1.0, self.warmup_sleep))
                        continue
                    break
        detalle = f" Último detalle: {last_error}." if last_error else ""
        raise RuntimeError(f"No se pudo generar respuesta streaming con el modelo {model_id}.{detalle}")


_SERVICE: Optional[LocalInferenceService] = None


def get_local_inference_service() -> LocalInferenceService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = LocalInferenceService()
    return _SERVICE
