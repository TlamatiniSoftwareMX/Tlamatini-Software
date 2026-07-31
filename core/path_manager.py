from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.platform_utils import current_platform


APP_NAME = "TLAMATINI"
FALLBACK_REASON_ENV = "TLAMATINI_STORAGE_FALLBACK_REASON"
FALLBACK_ROOT_ENV = "TLAMATINI_STORAGE_FALLBACK_ROOT"
if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", ""):
    executable_root = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(sys._MEIPASS).resolve()
    PROJECT_ROOT = executable_root if (executable_root / "local_ai").exists() else Path(sys._MEIPASS).resolve()
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    RESOURCE_ROOT = PROJECT_ROOT
APP_ASSETS_DIR = RESOURCE_ROOT / "assets"


def _set_secure_permissions(path: Path, *, is_dir: bool) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, 0o700 if is_dir else 0o600)
    except Exception:
        pass


@dataclass(frozen=True)
class AppPaths:
    root_dir: Path
    data_dir: Path
    license_dir: Path
    updates_dir: Path
    models_dir: Path
    library_dir: Path
    config_dir: Path
    memory_json: Path
    memory_aux_dir: Path
    logs_file: Path
    books_cache_dir: Path
    license_file: Path
    offline_license_code_file: Path
    installation_id_file: Path
    user_profile_file: Path
    bundled_public_key_file: Path
    local_updates_dir: Path
    local_ai_root: Path
    local_ai_config_dir: Path
    local_ai_runtime_dir: Path
    local_ai_models_dir: Path
    local_ai_logs_dir: Path
    local_ai_temp_dir: Path
    offline_library_dir: Path
    offline_learning_dir: Path
    local_maps_dir: Path


def _candidate_platform_root() -> Path:
    env_home = os.environ.get("TLAMATINI_HOME", "").strip()
    if env_home:
        return Path(env_home).expanduser().resolve()

    legacy_override = os.environ.get("TLAMATINI_DATA_DIR", "").strip()
    if legacy_override:
        return Path(legacy_override).expanduser().resolve()

    info = current_platform()
    home = Path.home()
    if info.os_name == "windows":
        base = Path(os.environ.get("APPDATA", "").strip() or (home / "AppData" / "Roaming"))
        return (base / APP_NAME).expanduser().resolve()
    if info.os_name == "macos":
        return (home / "Library" / "Application Support" / APP_NAME).expanduser().resolve()
    return (home / ".tlamatini").expanduser().resolve()


def _fallback_root() -> Path:
    return (Path(tempfile.gettempdir()) / APP_NAME).resolve()


def _record_storage_fallback(fallback: Path, reason: str) -> None:
    os.environ[FALLBACK_REASON_ENV] = str(reason or "").strip() or "unknown"
    os.environ[FALLBACK_ROOT_ENV] = str(fallback)
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        _set_secure_permissions(fallback, is_dir=True)
        marker = fallback / ".storage_fallback_warning"
        marker.write_text(
            (
                "TLAMATINI está usando almacenamiento temporal.\n"
                f"reason={os.environ[FALLBACK_REASON_ENV]}\n"
                f"root={fallback}\n"
            ),
            encoding="utf-8",
        )
        _set_secure_permissions(marker, is_dir=False)
    except Exception:
        pass


def _ensure_writable_root(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
        _set_secure_permissions(path, is_dir=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        _set_secure_permissions(probe, is_dir=False)
        probe.unlink(missing_ok=True)
        os.environ.pop(FALLBACK_REASON_ENV, None)
        os.environ.pop(FALLBACK_ROOT_ENV, None)
        return path
    except Exception as exc:
        strict_mode = os.environ.get("TLAMATINI_STRICT_STORAGE", "0").strip().lower() in {"1", "true", "yes"}
        if strict_mode:
            raise RuntimeError(f"No se pudo usar la ruta de almacenamiento {path}: {exc}") from exc
        fallback = _fallback_root()
        fallback.mkdir(parents=True, exist_ok=True)
        _record_storage_fallback(fallback, f"{path}: {exc}")
        return fallback


def _build_paths(root_dir: Path) -> AppPaths:
    data_dir = Path(os.environ.get("TLAMATINI_DATA_ROOT", "").strip()).expanduser().resolve() if os.environ.get("TLAMATINI_DATA_ROOT", "").strip() else root_dir / "data"
    license_dir = Path(os.environ.get("TLAMATINI_LICENSE_DIR", "").strip()).expanduser().resolve() if os.environ.get("TLAMATINI_LICENSE_DIR", "").strip() else root_dir / "license"
    updates_dir = Path(os.environ.get("TLAMATINI_UPDATES_DIR", "").strip()).expanduser().resolve() if os.environ.get("TLAMATINI_UPDATES_DIR", "").strip() else root_dir / "updates"
    models_dir = Path(os.environ.get("TLAMATINI_MODELS_DIR", "").strip()).expanduser().resolve() if os.environ.get("TLAMATINI_MODELS_DIR", "").strip() else root_dir / "models"
    library_dir = Path(os.environ.get("TLAMATINI_LIBRARY_DIR", "").strip()).expanduser().resolve() if os.environ.get("TLAMATINI_LIBRARY_DIR", "").strip() else root_dir / "library"
    config_dir = Path(os.environ.get("TLAMATINI_CONFIG_DIR", "").strip()).expanduser().resolve() if os.environ.get("TLAMATINI_CONFIG_DIR", "").strip() else root_dir / "config"
    memory_aux_dir = config_dir / "memoria"
    local_ai_root_dir = models_dir / "local_ai"
    return AppPaths(
        root_dir=root_dir,
        data_dir=data_dir,
        license_dir=license_dir,
        updates_dir=updates_dir,
        models_dir=models_dir,
        library_dir=library_dir,
        config_dir=config_dir,
        memory_json=config_dir / "memoria.json",
        memory_aux_dir=memory_aux_dir,
        logs_file=memory_aux_dir / "logs.txt",
        books_cache_dir=memory_aux_dir / "cache_libros",
        license_file=license_dir / "license_state.json",
        offline_license_code_file=license_dir / "license_code.txt",
        installation_id_file=license_dir / "installation_identity.json",
        user_profile_file=root_dir / "user_profile.json",
        bundled_public_key_file=RESOURCE_ROOT / "public_license_key.pem",
        local_updates_dir=updates_dir,
        local_ai_root=local_ai_root_dir,
        local_ai_config_dir=local_ai_root_dir / "config",
        local_ai_runtime_dir=local_ai_root_dir / "runtime",
        local_ai_models_dir=local_ai_root_dir / "models",
        local_ai_logs_dir=local_ai_root_dir / "logs",
        local_ai_temp_dir=local_ai_root_dir / "temp",
        offline_library_dir=library_dir / "offline_library",
        offline_learning_dir=library_dir / "offline_learning",
        local_maps_dir=data_dir / "local_maps",
    )


def _merge_tree(source: Path, target: Path) -> None:
    if not source.exists():
        return
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
            return
        try:
            shutil.move(str(source), str(target))
            return
        except Exception:
            shutil.copy2(source, target)
            return
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            _merge_tree(child, destination)
            try:
                child.rmdir()
            except Exception:
                pass
            continue
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(child), str(destination))
        except Exception:
            shutil.copy2(child, destination)


def _move_file_if_missing(source: Path, target: Path) -> None:
    if not source.exists() or target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(target))
    except Exception:
        shutil.copy2(source, target)


def _legacy_data_candidates(active_root: Path) -> list[Path]:
    candidates = []
    env_dir = os.environ.get("TLAMATINI_DATA_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir).expanduser().resolve())
    for candidate in (
        PROJECT_ROOT.parent / "TLAMATINI_DATA",
        PROJECT_ROOT / "TLAMATINI_DATA",
    ):
        resolved = candidate.resolve()
        if resolved != active_root:
            candidates.append(resolved)
    unique = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _migrate_legacy_data(paths: AppPaths) -> None:
    for legacy_root in _legacy_data_candidates(paths.root_dir):
        if not legacy_root.exists():
            continue
        legacy_base_data = legacy_root / "base_datos"
        mappings = [
            (legacy_root / "memoria", paths.memory_aux_dir),
            (legacy_root / "local_library", paths.offline_library_dir),
            (legacy_root / "local_learning", paths.offline_learning_dir),
            (legacy_root / "local_maps", paths.local_maps_dir),
            (legacy_base_data / "updates", paths.local_updates_dir),
        ]
        legacy_memory = legacy_base_data / "memoria.json"
        if legacy_memory.exists() and not paths.memory_json.exists():
            paths.memory_json.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(legacy_memory), str(paths.memory_json))
            except Exception:
                shutil.copy2(legacy_memory, paths.memory_json)
        for legacy_file, target_file in (
            (legacy_base_data / "license_state.json", paths.license_file),
            (legacy_base_data / "installation_identity.json", paths.installation_id_file),
        ):
            if legacy_file.exists() and not target_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(legacy_file), str(target_file))
                except Exception:
                    shutil.copy2(legacy_file, target_file)
        remaining_base_data = paths.data_dir / "base_datos"
        remaining_base_data.mkdir(parents=True, exist_ok=True)
        for child in legacy_base_data.iterdir() if legacy_base_data.exists() else []:
            if child.name in {"memoria.json", "license_state.json", "installation_identity.json", "updates"}:
                continue
            destination = remaining_base_data / child.name
            if child.is_dir():
                _merge_tree(child, destination)
            else:
                _move_file_if_missing(child, destination)
        for source, target in mappings:
            _merge_tree(source, target)


def _migrate_legacy_ai(paths: AppPaths) -> None:
    legacy_roots = [
        PROJECT_ROOT / "local_ai",
    ]
    env_ai_root = os.environ.get("TLAMATINI_LOCAL_AI_ROOT", "").strip()
    if env_ai_root:
        legacy_roots.append(Path(env_ai_root).expanduser().resolve())
    for legacy_root in legacy_roots:
        if not legacy_root.exists() or legacy_root.resolve() == paths.local_ai_root.resolve():
            continue
        if legacy_root.resolve() == (PROJECT_ROOT / "local_ai").resolve():
            bundled_ready = all((legacy_root / name).exists() for name in ("config", "runtime", "models"))
            if bundled_ready:
                continue
        _merge_tree(legacy_root, paths.local_ai_root)


def _ensure_core_dirs(paths: AppPaths) -> bool:
    try:
        for path in (
            paths.root_dir,
            paths.data_dir,
            paths.license_dir,
            paths.updates_dir,
            paths.models_dir,
            paths.library_dir,
            paths.config_dir,
            paths.memory_aux_dir,
            paths.books_cache_dir,
            paths.local_ai_root,
            paths.local_ai_config_dir,
            paths.local_ai_runtime_dir,
            paths.local_ai_models_dir,
            paths.local_ai_logs_dir,
            paths.local_ai_temp_dir,
            paths.offline_library_dir,
            paths.offline_learning_dir,
            paths.local_maps_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
            _set_secure_permissions(path, is_dir=True)
        return True
    except Exception:
        return False


def _initialize_paths() -> AppPaths:
    root = _ensure_writable_root(_candidate_platform_root())
    paths = _build_paths(root)
    if not _ensure_core_dirs(paths):
        fallback_root = _ensure_writable_root(_fallback_root())
        paths = _build_paths(fallback_root)
        _ensure_core_dirs(paths)
    _migrate_legacy_data(paths)
    _migrate_legacy_ai(paths)
    if not _ensure_core_dirs(paths):
        fallback_root = _ensure_writable_root(_fallback_root())
        paths = _build_paths(fallback_root)
        _ensure_core_dirs(paths)
    return paths


PATHS = _initialize_paths()


def get_paths() -> AppPaths:
    return PATHS


def app_root_dir() -> Path:
    return PATHS.root_dir


def using_temporary_app_root() -> bool:
    return PATHS.root_dir == _fallback_root() or bool(os.environ.get(FALLBACK_ROOT_ENV, "").strip())


def storage_fallback_reason() -> str:
    return os.environ.get(FALLBACK_REASON_ENV, "").strip()


def data_dir() -> Path:
    return PATHS.data_dir


def config_dir() -> Path:
    return PATHS.config_dir


def license_dir() -> Path:
    return PATHS.license_dir


def updates_dir() -> Path:
    return PATHS.updates_dir


def models_dir() -> Path:
    return PATHS.models_dir


def library_dir() -> Path:
    return PATHS.library_dir


def offline_library_dir() -> Path:
    return PATHS.offline_library_dir


def offline_learning_dir() -> Path:
    return PATHS.offline_learning_dir


def local_ai_root() -> Path:
    return PATHS.local_ai_root


def local_ai_models_dir() -> Path:
    return PATHS.local_ai_models_dir


def local_ai_runtime_dir() -> Path:
    return PATHS.local_ai_runtime_dir


def local_ai_logs_dir() -> Path:
    return PATHS.local_ai_logs_dir


def local_maps_dir() -> Path:
    return PATHS.local_maps_dir


def default_ollama_models_dir() -> Path:
    custom = os.environ.get("OLLAMA_MODELS", "").strip()
    if custom:
        return Path(custom).expanduser().resolve()
    return (Path.home() / ".ollama" / "models").expanduser().resolve()
