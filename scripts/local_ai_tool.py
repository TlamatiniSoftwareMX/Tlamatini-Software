#!/usr/bin/env python3
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_AI_ROOT = PROJECT_ROOT / "local_ai"
CONFIG_DIR = LOCAL_AI_ROOT / "config"
DOWNLOADS_DIR = LOCAL_AI_ROOT / "downloads"
RUNTIME_DIR = LOCAL_AI_ROOT / "runtime"
RUNTIME_BIN_DIR = RUNTIME_DIR / "bin"
DIST_DIR = PROJECT_ROOT / "dist"
FULL_DIST_DIR = DIST_DIR / "tlamatini_full"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.model_router import canonical_model_id
from core.ollama_local import ensure_local_ollama


def _ensure_data_dir_env() -> None:
    if os.environ.get("TLAMATINI_DATA_DIR", "").strip():
        return
    candidata_hermana = PROJECT_ROOT.parent / "TLAMATINI_DATA"
    if candidata_hermana.exists():
        os.environ["TLAMATINI_DATA_DIR"] = str(candidata_hermana)
    else:
        os.environ["TLAMATINI_DATA_DIR"] = str(PROJECT_ROOT / "TLAMATINI_DATA")


_ensure_data_dir_env()


def _backend_mode() -> str:
    return os.environ.get("TLAMATINI_AI_BACKEND", "").strip().lower() or "ollama"


def _default_ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "").strip() or "http://127.0.0.1:11436"


def _ollama_list() -> list[str]:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = _default_ollama_host()
    result = subprocess.run(
        ["ollama", "list"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "No se pudo consultar Ollama.").strip())
    modelos = []
    for linea in (result.stdout or "").splitlines()[1:]:
        if not linea.strip():
            continue
        modelos.append(linea.split()[0].strip())
    return modelos

RUNTIME_BIN_NAME = "llama-server.exe" if os.name == "nt" else "llama-server"
RUNTIME_BIN = PROJECT_ROOT / os.environ.get("TLAMATINI_AI_RUNTIME_BIN", f"local_ai/runtime/bin/{RUNTIME_BIN_NAME}")

DEFAULT_LLAMA3_URL = (
    "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/"
    "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf?download=true"
)
DEFAULT_GEMMA3_URL = os.environ.get("TLAMATINI_GEMMA3_URL", "").strip()
DEFAULT_MISTRAL_URL = (
    "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/"
    "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf?download=true"
)
LLAMA_CPP_RELEASE_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"


def _default_boot_model() -> str:
    raw = os.environ.get("TLAMATINI_AI_BOOT_MODEL", "").strip().lower()
    return canonical_model_id(raw or os.environ.get("TLAMATINI_LOCAL_LLM_MODEL", "").strip().lower() or "gemma3:4b")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _models_config() -> Dict:
    return _load_json(CONFIG_DIR / "models.json").get("models", {})


def _save_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _runtime_relative() -> str:
    try:
        return str(RUNTIME_BIN.relative_to(PROJECT_ROOT))
    except Exception:
        return str(RUNTIME_BIN)


def _host_platform_tag() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _model_path(model_id: str) -> Path:
    data = _models_config().get(model_id, {})
    raw = str(data.get("path", "")).strip()
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else (PROJECT_ROOT / path)
    return LOCAL_AI_ROOT / "models" / model_id / "model.gguf"


def _default_full_models_config() -> Dict:
    return {
        "models": {
            "gemma3": {
                "alias": "gemma3:4b",
                "role": "primary",
                "port": 18437,
                "path": "local_ai/models/gemma3/model.gguf",
                "context_window": 4096,
            }
        }
    }


def _default_full_runtime_config() -> Dict:
    return {
        "profile": "fast",
        "host": "127.0.0.1",
        "timeout": 12,
        "context_window": 4096,
        "autostart": True,
        "warmup_retries": 3,
        "warmup_sleep": 0.5,
        "threads": max(4, (os.cpu_count() or 8) - 2),
        "threads_batch": max(4, (os.cpu_count() or 8) - 2),
        "batch_size": 1024,
        "ubatch_size": 512,
        "parallel": 1,
        "cache_ram": 1024,
        "poll": 10,
        "webui": False,
        "accelerator": "auto",
        "gpu_layers": "auto",
    }


def _write_full_local_ai_config() -> None:
    _save_json(CONFIG_DIR / "models.json", _default_full_models_config())
    _save_json(CONFIG_DIR / "runtime.json", _default_full_runtime_config())


def _ensure_full_model_present() -> None:
    gemma = _model_path("gemma3")
    if not gemma.exists() or not gemma.is_file():
        raise RuntimeError(
            "Falta Gemma 3 para la edición Full. "
            "Coloca el modelo en local_ai/models/gemma3/model.gguf antes de empaquetar."
        )
    if gemma.stat().st_size < 1024 * 1024:
        raise RuntimeError("El archivo de Gemma 3 parece incompleto.")


def _pyinstaller_command() -> list[str]:
    venv_python = PROJECT_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv_python.exists():
        return [str(venv_python), "-m", "PyInstaller"]
    venv = PROJECT_ROOT / ".venv" / ("Scripts/pyinstaller.exe" if os.name == "nt" else "bin/pyinstaller")
    if venv.exists():
        return [str(venv)]
    found = shutil.which("pyinstaller")
    if found:
        return [found]
    try:
        import PyInstaller  # noqa: F401

        return [sys.executable, "-m", "PyInstaller"]
    except Exception:
        pass
    raise RuntimeError("No se encontró pyinstaller. Instálalo en el entorno del proyecto antes de generar la edición Full.")


def _build_pyinstaller_bundle() -> None:
    pyinstaller_cmd = _pyinstaller_command()
    result = subprocess.run(
        [*pyinstaller_cmd, "--clean", "--noconfirm", "pyinstaller.spec"],
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("PyInstaller no pudo generar el bundle Full.")


def _copy_full_bundle_target() -> Path:
    source_candidates = [
        DIST_DIR / "TLAMATINI",
        DIST_DIR / "TLAMATINI.exe",
        DIST_DIR / "TLAMATINI.app",
    ]
    source = next((item for item in source_candidates if item.exists()), None)
    if source is None:
        raise RuntimeError("No se encontró salida de PyInstaller en dist/.")

    if FULL_DIST_DIR.exists():
        if FULL_DIST_DIR.is_dir():
            shutil.rmtree(FULL_DIST_DIR)
        else:
            FULL_DIST_DIR.unlink()

    if source.is_dir():
        shutil.copytree(source, FULL_DIST_DIR)
    else:
        FULL_DIST_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, FULL_DIST_DIR / source.name)
    return FULL_DIST_DIR


def _copy_if_exists(source: Path, target: Path) -> None:
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _write_release_manifest(target: Path) -> None:
    manifest = {
        "app": "TLAMATINI",
        "edition": "full",
        "platform": _host_platform_tag(),
        "version": os.environ.get("TLAMATINI_APP_VERSION", "5.2.3"),
        "ai_backend": "local",
        "primary_model": "gemma3:4b",
        "model_path": "embedded",
        "runtime_path": "embedded",
        "bundle": target.name,
    }
    _save_json(target / "release_manifest.json", manifest)


def _copy_platform_installers(target: Path) -> None:
    installer_map = {
        "linux": [("scripts/install_full_linux.sh", "install.sh")],
        "windows": [
            ("scripts/install_full_windows.ps1", "install.ps1"),
            ("scripts/install_full_windows.cmd", "install.cmd"),
        ],
        "macos": [("scripts/install_full_macos.sh", "install.command")],
    }
    for source_rel, target_name in installer_map.get(_host_platform_tag(), []):
        _copy_if_exists(PROJECT_ROOT / source_rel, target / target_name)
    if _host_platform_tag() == "linux":
        _copy_if_exists(PROJECT_ROOT / "assets" / "app_icon.png", target / "tlamatini.png")
    elif _host_platform_tag() == "windows":
        _copy_if_exists(PROJECT_ROOT / "assets" / "app_icon.ico", target / "tlamatini.ico")
    elif _host_platform_tag() == "macos":
        _copy_if_exists(PROJECT_ROOT / "assets" / "app_icon.icns", target / "tlamatini.icns")


def _copy_full_local_ai_assets(target: Path) -> None:
    local_ai_target = target / "local_ai"
    local_ai_target.mkdir(parents=True, exist_ok=True)
    for item in ("config", "runtime", "models"):
        source = LOCAL_AI_ROOT / item
        if not source.exists():
            continue
        destination = local_ai_target / item
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def _copy_full_support_assets(target: Path) -> None:
    for item in ("assets", "map_ui"):
        source = PROJECT_ROOT / item
        if not source.exists():
            continue
        destination = target / item
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    _copy_if_exists(PROJECT_ROOT / "public_license_key.pem", target / "public_license_key.pem")


def _archive_directory(source_dir: Path, archive_base: Path, fmt: str) -> Path:
    archive_path = shutil.make_archive(str(archive_base), fmt, root_dir=source_dir.parent, base_dir=source_dir.name)
    return Path(archive_path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_artifact_checksums(artifacts: list[Path]) -> Path:
    lines = []
    records = []
    for artifact in artifacts:
        if not artifact.exists() or not artifact.is_file():
            continue
        checksum = _sha256_file(artifact)
        rel = artifact.relative_to(PROJECT_ROOT)
        lines.append(f"{checksum}  {rel}")
        records.append({"path": str(rel), "sha256": checksum, "size": artifact.stat().st_size})
    checksums_txt = DIST_DIR / "SHA256SUMS.txt"
    checksums_json = DIST_DIR / "SHA256SUMS.json"
    checksums_txt.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    checksums_json.write_text(json.dumps({"artifacts": records}, indent=2, ensure_ascii=False), encoding="utf-8")
    return checksums_txt


def _write_release_metadata() -> Path:
    metadata = {
        "app": "TLAMATINI",
        "edition": "full",
        "platform": _host_platform_tag(),
        "version": os.environ.get("TLAMATINI_APP_VERSION", "5.2.3"),
    }
    checksums_json = DIST_DIR / "SHA256SUMS.json"
    if checksums_json.exists():
        try:
            metadata["artifacts"] = json.loads(checksums_json.read_text(encoding="utf-8")).get("artifacts", [])
        except Exception:
            metadata["artifacts"] = []
    else:
        metadata["artifacts"] = []
    output = DIST_DIR / "release_metadata.json"
    output.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def _package_linux_release(target: Path) -> list[Path]:
    artifacts = []
    archive = _archive_directory(target, DIST_DIR / "TLAMATINI-full-linux-x86_64", "gztar")
    artifacts.append(archive)
    return artifacts


def _package_windows_release(target: Path) -> list[Path]:
    artifacts = []
    archive = _archive_directory(target, DIST_DIR / "TLAMATINI-full-windows-x86_64", "zip")
    artifacts.append(archive)
    return artifacts


def _package_macos_release(target: Path) -> list[Path]:
    artifacts = []
    archive = _archive_directory(target, DIST_DIR / "TLAMATINI-full-macos", "zip")
    artifacts.append(archive)
    app_bundle = target / "TLAMATINI.app"
    if shutil.which("hdiutil") and app_bundle.exists():
        dmg_path = DIST_DIR / "TLAMATINI-full-macos.dmg"
        if dmg_path.exists():
            dmg_path.unlink()
        result = subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                "TLAMATINI",
                "-srcfolder",
                str(app_bundle),
                "-ov",
                "-format",
                "UDZO",
                str(dmg_path),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
        )
        if result.returncode == 0 and dmg_path.exists():
            artifacts.append(dmg_path)
    return artifacts


def package_full_release() -> int:
    bundle = FULL_DIST_DIR
    if not bundle.exists():
        print("No existe dist/tlamatini_full. Ejecuta primero build_full_release.")
        return 1
    platform_tag = _host_platform_tag()
    if platform_tag == "linux":
        artifacts = _package_linux_release(bundle)
    elif platform_tag == "windows":
        artifacts = _package_windows_release(bundle)
    else:
        artifacts = _package_macos_release(bundle)
    checksum_file = _write_artifact_checksums(artifacts + [item for item in bundle.iterdir() if item.is_file()])
    metadata_file = _write_release_metadata()
    shutil.copy2(metadata_file, bundle / metadata_file.name)
    print("Paquetes generados:")
    for artifact in artifacts:
        print(f"- {artifact.relative_to(PROJECT_ROOT)}")
    print(f"- {checksum_file.relative_to(PROJECT_ROOT)}")
    print(f"- {metadata_file.relative_to(PROJECT_ROOT)}")
    return 0


def doctor_full_release() -> int:
    bundle = FULL_DIST_DIR
    issues = []
    if not bundle.exists():
        issues.append("Falta dist/tlamatini_full")
    if not (bundle / "release_manifest.json").exists():
        issues.append("Falta release_manifest.json en dist/tlamatini_full")
    if not (bundle / "release_metadata.json").exists():
        issues.append("Falta release_metadata.json en dist/tlamatini_full")
    if _host_platform_tag() == "linux" and not (bundle / "install.sh").exists():
        issues.append("Falta install.sh para Linux")
    if _host_platform_tag() == "windows" and not ((bundle / "install.ps1").exists() and (bundle / "install.cmd").exists()):
        issues.append("Faltan instaladores Windows")
    if _host_platform_tag() == "macos" and not (bundle / "install.command").exists():
        issues.append("Falta install.command para macOS")
    if not _ensure_dist_checksums_present():
        issues.append("Faltan SHA256SUMS en dist/")
    if not (DIST_DIR / "release_metadata.json").exists():
        issues.append("Falta release_metadata.json en dist/")
    if issues:
        print("Doctor Full: problemas detectados")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Doctor Full: OK")
    return 0


def _ensure_dist_checksums_present() -> bool:
    return (DIST_DIR / "SHA256SUMS.txt").exists() and (DIST_DIR / "SHA256SUMS.json").exists()


def _safe_request(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TLAMATINI-Local-AI/1.0",
            "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.8",
        },
    )
    return urllib.request.urlopen(request, timeout=60)


def _open_request(url: str, extra_headers: Optional[Dict[str, str]] = None):
    headers = {
        "User-Agent": "TLAMATINI-Local-AI/1.0",
        "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.8",
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=60)


def _print_progress(prefix: str, current: int, total: int) -> None:
    if total > 0:
        percent = min(100.0, (current / total) * 100.0)
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        print(f"\r{prefix}: {percent:5.1f}% ({current_mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)
    else:
        current_mb = current / (1024 * 1024)
        print(f"\r{prefix}: {current_mb:.1f} MB", end="", flush=True)


def _response_supports_range(response) -> bool:
    content_range = response.headers.get("Content-Range", "")
    accept_ranges = response.headers.get("Accept-Ranges", "")
    return bool(content_range) or "bytes" in accept_ranges.lower()


def _response_total_size(response) -> int:
    content_range = response.headers.get("Content-Range", "")
    if "/" in content_range:
        total = content_range.rsplit("/", 1)[-1].strip()
        if total.isdigit():
            return int(total)
    content_length = response.headers.get("Content-Length", "").strip()
    if content_length.isdigit():
        return int(content_length)
    return 0


def _remote_size(url: str) -> int:
    try:
        with _open_request(url, {"Range": "bytes=0-0"}) as response:
            if response.status == 206:
                total = _response_total_size(response)
                if total > 0:
                    return total
            content_length = response.headers.get("Content-Length", "").strip()
            if content_length.isdigit():
                return int(content_length)
    except Exception:
        return 0
    return 0


def _download(url: str, target: Path, label: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    existing = tmp.stat().st_size if tmp.exists() else 0
    total_expected = _remote_size(url)
    if target.exists() and target.stat().st_size > 0:
        print(f"{label} ya existe: {target.relative_to(PROJECT_ROOT)}")
        return

    if total_expected > 0 and existing == total_expected:
        tmp.replace(target)
        print(f"Descarga completada: {target.relative_to(PROJECT_ROOT)}")
        return

    if total_expected > 0 and existing > total_expected:
        print(f"Parcial inválido para {label}; reiniciando descarga.")
        tmp.unlink(missing_ok=True)
        existing = 0

    headers = {}
    mode = "wb"
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"

    try:
        with _open_request(url, headers) as response:
            if existing > 0:
                if response.status == 206 and _response_supports_range(response):
                    total = _response_total_size(response) or total_expected or (
                        existing + int(response.headers.get("Content-Length", "0") or 0)
                    )
                    read = existing
                    mode = "ab"
                    print(f"Reanudando {label} desde {existing} bytes.")
                else:
                    print(f"Servidor no soporta Range para {label}, reiniciando descarga.")
                    tmp.unlink(missing_ok=True)
                    existing = 0
                    total = _response_total_size(response) or total_expected or int(
                        response.headers.get("Content-Length", "0") or 0
                    )
                    read = 0
            else:
                total = _response_total_size(response) or total_expected or int(
                    response.headers.get("Content-Length", "0") or 0
                )
                read = 0
                print(f"Iniciando descarga nueva de {label}.")

            with tmp.open(mode) as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    read += len(chunk)
                    _print_progress(label, read, total)
        print()
        final_size = tmp.stat().st_size if tmp.exists() else 0
        if total > 0 and final_size != total:
            raise RuntimeError(
                f"Descarga incompleta de {label}: esperaba {total} bytes y obtuvo {final_size} bytes."
            )
        tmp.replace(target)
        print(f"Descarga completada: {target.relative_to(PROJECT_ROOT)}")
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="ignore").strip()
        raise RuntimeError(f"HTTP {exc.code} al descargar {label}: {detalle or url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Error de red al descargar {label}: {exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"No se pudo descargar {label}: {exc}") from exc


def _platform_asset_matches(name: str) -> bool:
    sistema = platform.system().lower()
    maquina = platform.machine().lower()
    name_l = name.lower()
    if "server" not in name_l and "bin" not in name_l:
        return False
    aceleradores = ("openvino", "rocm", "vulkan", "cuda", "sycl", "opencl", "aclgraph", "kleidiai")
    if any(token in name_l for token in aceleradores):
        return False

    if sistema == "linux":
        if "ubuntu" not in name_l and "linux" not in name_l:
            return False
        if maquina in {"x86_64", "amd64"}:
            return "x64" in name_l or "amd64" in name_l
        if maquina in {"aarch64", "arm64"}:
            return "arm64" in name_l or "aarch64" in name_l
    elif sistema == "darwin":
        if "macos" not in name_l and "mac" not in name_l:
            return False
        if maquina == "arm64":
            return "arm64" in name_l
        return "x64" in name_l or "amd64" in name_l
    elif sistema == "windows":
        if "win" not in name_l:
            return False
        if maquina in {"x86_64", "amd64"}:
            return "x64" in name_l or "amd64" in name_l
        if maquina in {"arm64", "aarch64"}:
            return "arm64" in name_l
    return False


def _runtime_archive_score(name: str) -> int:
    name_l = name.lower()
    score = 0
    if "ubuntu-x64" in name_l or "ubuntu-arm64" in name_l or "macos" in name_l or "win-cpu" in name_l:
        score += 100
    if any(token in name_l for token in ("openvino", "rocm", "vulkan", "cuda", "sycl", "opencl", "aclgraph", "kleidiai")):
        score -= 100
    return score


def _latest_runtime_asset_url() -> Tuple[str, str]:
    try:
        with _safe_request(LLAMA_CPP_RELEASE_API) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"No se pudo consultar releases de llama.cpp: {exc}") from exc

    assets = data.get("assets", []) or []
    candidatos = []
    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if not name or not url:
            continue
        if _platform_asset_matches(name):
            candidatos.append((name, url))
    if candidatos:
        candidatos.sort(key=lambda item: _runtime_archive_score(item[0]), reverse=True)
        name, url = candidatos[0]
        return url, name
    raise RuntimeError("No encontré un binario precompilado compatible de llama.cpp para esta plataforma.")


def _extract_archive(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(destination)
        return
    suffixes = "".join(archive.suffixes[-2:])
    if archive.suffix == ".tar" or suffixes in {".tar.gz", ".tgz"}:
        with tarfile.open(archive) as tf:
            tf.extractall(destination)
        return
    raise RuntimeError(f"Formato de archivo no soportado para runtime: {archive.name}")


def _find_executable(root: Path, names: Iterable[str]) -> Optional[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in names:
            return path
    return None


def _runtime_payload_files(runtime_exec: Path) -> Iterable[Path]:
    parent = runtime_exec.parent
    for path in parent.iterdir():
        if path.is_file():
            yield path


def _runtime_support_ready() -> bool:
    if os.name == "nt":
        return True
    runtime_dir = RUNTIME_BIN.parent
    if not (any(runtime_dir.glob("libllama-common.so*")) and any(runtime_dir.glob("libllama.so*"))):
        return False
    try:
        env = os.environ.copy()
        ld_path = env.get("LD_LIBRARY_PATH", "").strip()
        env["LD_LIBRARY_PATH"] = str(runtime_dir) if not ld_path else f"{runtime_dir}:{ld_path}"
        result = subprocess.run(
            ["ldd", str(RUNTIME_BIN)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        output = f"{result.stdout}\n{result.stderr}".lower()
        if "not found" in output:
            return False
    except Exception:
        return False
    return True


def _existing_runtime_archive() -> Optional[Path]:
    candidates = list(DOWNLOADS_DIR.glob("llama-*.zip")) + list(DOWNLOADS_DIR.glob("llama-*.tar.gz"))
    if candidates:
        candidates.sort(key=lambda item: _runtime_archive_score(item.name), reverse=True)
        return candidates[0]
    return None


def _install_runtime_if_missing() -> None:
    force_refresh = os.environ.get("TLAMATINI_FORCE_RUNTIME_REFRESH", "0").strip().lower() in {"1", "true", "yes"}
    if RUNTIME_BIN.exists() and _runtime_support_ready() and not force_refresh:
        return

    runtime_url = os.environ.get("TLAMATINI_RUNTIME_URL", "").strip()
    archive = _existing_runtime_archive()
    runtime_name = archive.name if archive is not None else ""
    if archive is not None and _runtime_archive_score(archive.name) < 0 and not runtime_url:
        archive = None
        runtime_name = ""
    if archive is None and runtime_url:
        runtime_name = Path(runtime_url.split("?")[0]).name
        archive = DOWNLOADS_DIR / runtime_name
    if archive is None and not runtime_url:
        runtime_url, runtime_name = _latest_runtime_asset_url()
        archive = DOWNLOADS_DIR / runtime_name

    if archive is None:
        raise RuntimeError("No se pudo resolver un archivo de runtime local ni remoto.")

    if archive.exists() and force_refresh and not runtime_url:
        archive.unlink(missing_ok=True)
        runtime_url, runtime_name = _latest_runtime_asset_url()
        archive = DOWNLOADS_DIR / runtime_name

    if not archive.exists():
        print(f"Descargando runtime llama.cpp: {runtime_url}")
        _download(runtime_url, archive, "runtime llama.cpp")
    else:
        print(f"Runtime ya descargado: {archive.relative_to(PROJECT_ROOT)}")

    extract_dir = DOWNLOADS_DIR / "runtime_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    _extract_archive(archive, extract_dir)

    runtime_exec = _find_executable(extract_dir, {RUNTIME_BIN_NAME, "server", "server.exe"})
    if runtime_exec is None:
        raise RuntimeError("No encontré `llama-server` dentro del runtime descargado.")

    RUNTIME_BIN.parent.mkdir(parents=True, exist_ok=True)
    for payload_file in _runtime_payload_files(runtime_exec):
        shutil.copy2(payload_file, RUNTIME_BIN.parent / payload_file.name)
    if os.name != "nt":
        for candidate in RUNTIME_BIN.parent.iterdir():
            if not candidate.is_file():
                continue
            current_mode = candidate.stat().st_mode
            if os.access(candidate, os.X_OK) or candidate == RUNTIME_BIN or not candidate.name.startswith("lib"):
                candidate.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Runtime instalado en {_runtime_relative()}")


def _download_model_if_missing(model_id: str, url: str) -> None:
    target = _model_path(model_id)
    if target.exists() and target.stat().st_size > 0:
        print(f"{model_id} ya existe: {target.relative_to(PROJECT_ROOT)}")
        return
    print(f"Descargando {model_id}: {url}")
    _download(url, target, model_id)


def setup_local_ai() -> int:
    if _backend_mode() == "ollama":
        print("Backend activo: Ollama. No se requiere instalar llama-server para este modo.")
        return 0
    for ruta in [
        LOCAL_AI_ROOT / "runtime" / "bin",
        LOCAL_AI_ROOT / "models" / "gemma3",
        LOCAL_AI_ROOT / "models" / "mistral",
        LOCAL_AI_ROOT / "config",
        LOCAL_AI_ROOT / "cache",
        LOCAL_AI_ROOT / "logs",
        LOCAL_AI_ROOT / "docs_pipeline",
        LOCAL_AI_ROOT / "temp",
        LOCAL_AI_ROOT / "downloads",
    ]:
        ruta.mkdir(parents=True, exist_ok=True)
    try:
        _install_runtime_if_missing()
    except Exception as exc:
        print(f"No se pudo instalar runtime local: {exc}")
        return 1
    print("local_ai preparado.")
    return 0


def download_models() -> int:
    status = setup_local_ai()
    if status != 0:
        return status

    gemma_url = DEFAULT_GEMMA3_URL

    try:
        if gemma_url:
            _download_model_if_missing("gemma3", gemma_url)
    except Exception as exc:
        print(str(exc))
        return 1

    return verify_local_ai()


def verify_local_ai() -> int:
    if _backend_mode() == "ollama":
        esperado = os.environ.get("TLAMATINI_LOCAL_LLM_MODEL", "").strip() or "gemma3:4b"
        ok, mensaje = ensure_local_ollama(_default_ollama_host())
        if not ok:
            print(mensaje)
            return 1
        try:
            modelos = _ollama_list()
        except Exception as exc:
            print(f"No se pudo validar Ollama: {exc}")
            return 1
        if esperado not in modelos:
            print(f"Modelo principal no disponible en Ollama: {esperado}")
            return 1
        print(f"Ollama disponible con el modelo principal {esperado} en {_default_ollama_host()}.")
        return 0

    modelos = _models_config()
    errores = []
    if not RUNTIME_BIN.exists() or not RUNTIME_BIN.is_file():
        errores.append(f"Runtime faltante: {_runtime_relative()}")
    elif os.name != "nt" and not os.access(RUNTIME_BIN, os.X_OK):
        errores.append(f"Runtime no ejecutable: {_runtime_relative()}")
    elif not _runtime_support_ready():
        errores.append(f"Runtime incompleto: faltan bibliotecas locales junto a {_runtime_relative()}")

    for model_id in modelos.keys():
        path = _model_path(model_id)
        if not path.exists() or not path.is_file():
            errores.append(f"Modelo faltante {model_id}: {path.relative_to(PROJECT_ROOT)}")
            continue
        if path.stat().st_size < 1024 * 1024:
            errores.append(f"Modelo inválido {model_id}: {path.relative_to(PROJECT_ROOT)} parece incompleto.")

    if errores:
        if "gemma3" in modelos and not _model_path("gemma3").exists():
            errores.append(
                "TLAMATINI usa runtime local llama.cpp con archivos GGUF; un modelo descargado solo en Ollama no sirve aquí. "
                "Coloca Gemma en local_ai/models/gemma3/model.gguf"
            )
        print("\n".join(errores))
        return 1

    skip_runtime_verify = os.environ.get("TLAMATINI_SKIP_RUNTIME_VERIFY", "0").strip().lower() in {"1", "true", "yes"}
    if skip_runtime_verify:
        print("Verificación operativa del runtime omitida por TLAMATINI_SKIP_RUNTIME_VERIFY.")
        return 0

    # Verificación operativa mínima del modelo principal, no solo existencia de archivos.
    try:
        from core.local_inference_service import LocalInferenceService

        service = LocalInferenceService()
        model_id = _default_boot_model()
        ok, mensaje = service.ensure_model_ready(model_id)
        if not ok:
            print(f"Modelo principal no operativo ({model_id}): {mensaje}")
            return 1
    except Exception as exc:
        print(f"No se pudo validar el modelo principal en runtime: {exc}")
        return 1

    print("Runtime y modelos disponibles.")
    return 0


def run_local_ai() -> int:
    if _backend_mode() == "ollama":
        esperado = os.environ.get("TLAMATINI_LOCAL_LLM_MODEL", "").strip() or "gemma3:4b"
        ok, mensaje = ensure_local_ollama(_default_ollama_host())
        if not ok:
            print(mensaje)
            return 1
        try:
            modelos = _ollama_list()
        except Exception as exc:
            print(f"No se pudo consultar Ollama: {exc}")
            return 1
        print(f"Backend activo: Ollama | host: {_default_ollama_host()} | modelo principal: {esperado}")
        if esperado not in modelos:
            print(f"Falta el modelo en Ollama: {esperado}")
            return 1
        print(f"{esperado}: disponible en Ollama")
        return 0

    from core.local_inference_service import get_local_inference_service

    service = get_local_inference_service()
    modelos = service.startup_models()
    if not modelos:
        print("No hay modelos configurados para arranque local.")
        return 1
    print(f"Modelo local por defecto: {_default_boot_model()}")
    print(
        "Perfil de rendimiento activo: "
        f"{service.profile} | aceleracion: {'gpu-auto' if service.using_gpu else 'cpu'} | "
        f"ctx={service.context_window} | threads={service.threads}/{service.threads_batch} | "
        f"batch={service.batch_size}/{service.ubatch_size}"
    )
    print(f"Modelos seleccionados para arranque: {', '.join(modelos.keys())}")
    for model_id in modelos.keys():
        ok, mensaje = service.ensure_model_ready(model_id)
        print(f"{model_id}: {mensaje}")
        if not ok:
            return 1
    return 0


def run_tlamatini() -> int:
    status = setup_local_ai()
    if status != 0:
        return status
    if verify_local_ai() != 0:
        return 1
    warmup_on_start = os.environ.get("TLAMATINI_AI_WARMUP_ON_START", "0").strip().lower() in {"1", "true", "yes"}
    if warmup_on_start:
        print("Warm-up automático activado. Iniciando solo el modelo por defecto.")
        if run_local_ai() != 0:
            return 1
    else:
        print(f"Warm-up automático desactivado. Modelo por defecto configurado: {_default_boot_model()}")
    return subprocess.call([sys.executable, "main.py"], cwd=PROJECT_ROOT)


def build_portable() -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    target = DIST_DIR / "tlamatini_portable"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        PROJECT_ROOT,
        target,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            ".git",
            "dist",
            "memoria/cache_libros",
            "local_ai/temp",
            "local_ai/logs",
            "local_ai/downloads/runtime_extract",
        ),
    )
    archive = DIST_DIR / "tlamatini_portable.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in target.rglob("*"):
            zf.write(file, file.relative_to(DIST_DIR))
    print(f"Portable generado: {archive.relative_to(PROJECT_ROOT)}")
    return 0


def build_full_release() -> int:
    os.environ["TLAMATINI_AI_BACKEND"] = "local"
    status = setup_local_ai()
    if status != 0:
        return status
    try:
        _ensure_full_model_present()
        _write_full_local_ai_config()
    except Exception as exc:
        print(str(exc))
        return 1

    if verify_local_ai() != 0:
        return 1

    try:
        _build_pyinstaller_bundle()
        target = _copy_full_bundle_target()
        _copy_full_support_assets(target)
        _copy_full_local_ai_assets(target)
        _write_release_manifest(target)
        _copy_platform_installers(target)
    except Exception as exc:
        print(str(exc))
        return 1

    print("Edición Full generada correctamente.")
    print(f"Bundle listo en: {target.relative_to(PROJECT_ROOT)}")
    print("Incluye runtime local y Gemma 3 para que el usuario no descargue IA aparte.")
    return 0


COMMANDS = {
    "setup_local_ai": setup_local_ai,
    "download_models": download_models,
    "verify_local_ai": verify_local_ai,
    "run_local_ai": run_local_ai,
    "run_tlamatini": run_tlamatini,
    "build_portable": build_portable,
    "build_full_release": build_full_release,
    "package_full_release": package_full_release,
    "doctor_full_release": doctor_full_release,
}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify_local_ai"
    raise SystemExit(COMMANDS.get(cmd, verify_local_ai)())
