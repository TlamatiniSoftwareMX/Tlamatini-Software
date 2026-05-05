import argparse
import atexit
import os
import signal
import sys
import traceback
from pathlib import Path

from core.ai_bootstrap import bootstrap_ollama_model
from core.model_router import canonical_model_id
from core.ollama_local import configured_ollama_host, stop_local_ollama
from core.path_manager import PROJECT_ROOT, get_paths, local_ai_root, storage_fallback_reason, using_temporary_app_root


def _asegurar_rutas_portables(base_dir: Path):
    os.environ.setdefault("TLAMATINI_APP_DIR", str(base_dir))
    os.environ.setdefault("TLAMATINI_HOME", str(get_paths().root_dir))


def _asegurar_python_integrado():
    if getattr(sys, "frozen", False):
        return
    base_dir = Path(__file__).resolve().parent
    _asegurar_rutas_portables(base_dir)
    venv_python = base_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    if not venv_python.exists():
        return

    actual = Path(sys.executable).resolve()
    esperado = venv_python.resolve()

    if actual == esperado:
        return

    os.execv(str(esperado), [str(esperado), __file__, *sys.argv[1:]])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arranque principal de TLAMATINI.")
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--safe", action="store_true", help="Usa perfil seguro para laptop.")
    profile.add_argument("--fast", action="store_true", help="Usa perfil rapido si el equipo aguanta.")
    parser.add_argument("--with-mistral", action="store_true", help="Habilita y arranca Mistral ademas de Gemma 3.")
    parser.add_argument("--no-ai", action="store_true", help="No inicia IA local; solo abre TLAMATINI.")
    return parser.parse_args()


def _bundled_local_ai_available() -> bool:
    ai_root = PROJECT_ROOT / "local_ai"
    if not ai_root.exists():
        ai_root = local_ai_root()
    runtime_name = "llama-server.exe" if os.name == "nt" else "llama-server"
    runtime_bin = ai_root / "runtime" / "bin" / runtime_name
    config_models = ai_root / "config" / "models.json"
    gemma_model = ai_root / "models" / "gemma3" / "model.gguf"
    return runtime_bin.exists() and config_models.exists() and gemma_model.exists()


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    if args.safe:
        os.environ["TLAMATINI_AI_PROFILE"] = "safe"
    elif args.fast:
        os.environ["TLAMATINI_AI_PROFILE"] = "fast"
    else:
        os.environ.setdefault("TLAMATINI_AI_PROFILE", "safe")

    os.environ.setdefault("TLAMATINI_AI_BOOT_MODEL", "gemma3:4b")
    os.environ.setdefault("TLAMATINI_PRIMARY_MODEL", "gemma3:4b")
    os.environ.setdefault("TLAMATINI_LOCAL_LLM_MODEL", "gemma3:4b")
    default_backend = "local" if _bundled_local_ai_available() else "ollama"
    os.environ.setdefault("TLAMATINI_AI_BACKEND", default_backend)
    os.environ.setdefault("TLAMATINI_AI_AUTO_PULL", "1")
    os.environ.setdefault("TLAMATINI_AI_WARMUP_ON_START", "0")
    os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:11436")

    if args.with_mistral:
        os.environ["TLAMATINI_ENABLE_MISTRAL"] = "1"
    else:
        os.environ.setdefault("TLAMATINI_ENABLE_MISTRAL", "0")


def _ruta_relativa(base_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except Exception:
        return str(path)


def _validar_archivos_ai(base_dir: Path, with_mistral: bool = False) -> tuple[bool, list[str]]:
    backend = os.environ.get("TLAMATINI_AI_BACKEND", "").strip().lower() or "ollama"
    if backend == "ollama":
        return True, []

    errores = []
    primary_id = canonical_model_id(os.environ.get("TLAMATINI_PRIMARY_MODEL", "").strip().lower() or "gemma3:4b")
    ai_root = PROJECT_ROOT / "local_ai"
    if not ai_root.exists():
        ai_root = local_ai_root()
    runtime_name = "llama-server.exe" if os.name == "nt" else "llama-server"
    runtime = ai_root / "runtime" / "bin" / runtime_name
    principal = ai_root / "models" / primary_id / "model.gguf"
    mistral = ai_root / "models" / "mistral" / "model.gguf"
    if not runtime.exists():
        errores.append(
            f"Falta runtime local: {_ruta_relativa(base_dir, runtime)}\n"
            "Ejecuta: sh scripts/setup_local_ai.sh"
        )
    elif not runtime.is_file():
        errores.append(f"Runtime invalido: {_ruta_relativa(base_dir, runtime)}")
    if not principal.exists():
        errores.append(
            f"Falta modelo principal: {_ruta_relativa(base_dir, principal)}\n"
            "Ejecuta: sh scripts/download_models.sh"
        )
    elif not principal.is_file():
        errores.append(f"Modelo principal invalido: {_ruta_relativa(base_dir, principal)}")
    if with_mistral:
        if not mistral.exists():
            errores.append(
                f"Falta modelo opcional Mistral: {_ruta_relativa(base_dir, mistral)}\n"
                "Ejecuta: sh scripts/download_models.sh"
            )
        elif not mistral.is_file():
            errores.append(f"Modelo Mistral invalido: {_ruta_relativa(base_dir, mistral)}")
    return not errores, errores


def _validar_runtime_local(base_dir: Path, with_mistral: bool = False) -> tuple[bool, list[str]]:
    original_backend = os.environ.get("TLAMATINI_AI_BACKEND")
    os.environ["TLAMATINI_AI_BACKEND"] = "local"
    try:
        return _validar_archivos_ai(base_dir, with_mistral=with_mistral)
    finally:
        if original_backend is None:
            os.environ.pop("TLAMATINI_AI_BACKEND", None)
        else:
            os.environ["TLAMATINI_AI_BACKEND"] = original_backend


def _boot_local_ai(base_dir: Path, with_mistral: bool) -> tuple[object, list[str]]:
    from core.local_inference_service import LocalInferenceService

    service = LocalInferenceService()
    started_by_main: list[str] = []
    primary_id = canonical_model_id(os.environ.get("TLAMATINI_PRIMARY_MODEL", "").strip().lower() or "gemma3:4b")
    targets = [primary_id] + (["mistral"] if with_mistral and primary_id != "mistral" else [])

    print(
        "[TLAMATINI] Configuracion IA: "
        f"perfil={service.profile} aceleracion={'gpu-auto' if service.using_gpu else 'cpu'} "
        f"ctx={service.context_window} threads={service.threads}/{service.threads_batch}"
    )

    for model_id in targets:
        managed = service.managed_model(model_id)
        ok, mensaje = service.healthcheck_model(model_id)
        if ok:
            print(f"[TLAMATINI] {model_id} ya esta corriendo en http://{managed.host}:{managed.port} ({mensaje})")
            continue
        print(f"[TLAMATINI] Iniciando {model_id} en http://{managed.host}:{managed.port}...")
        pid_before = service.read_pid(model_id)
        ok, mensaje = service.ensure_model_ready(model_id)
        if not ok:
            raise RuntimeError(f"No se pudo iniciar {model_id}: {mensaje}")
        pid_after = service.read_pid(model_id)
        if pid_after and pid_after != pid_before:
            started_by_main.append(model_id)
        ok, mensaje = service.wait_until_ready(model_id, retries=max(5, service.warmup_retries), sleep_seconds=max(0.5, service.warmup_sleep))
        if not ok:
            raise RuntimeError(f"{model_id} no quedo listo: {mensaje}")
        print(f"[TLAMATINI] {model_id} listo ({mensaje})")
    return service, started_by_main


def _registrar_cleanup_ai(service, started_models: list[str]) -> None:
    stop_on_exit = os.environ.get("TLAMATINI_AI_STOP_ON_EXIT", "0").strip().lower() in {"1", "true", "yes", "on"}
    cleaned = {"done": False}

    def _cleanup(*_args):
        if cleaned["done"]:
            return
        cleaned["done"] = True
        if not stop_on_exit:
            return
        for model_id in reversed(started_models):
            try:
                if service.stop_model_process(model_id):
                    print(f"[TLAMATINI] Runtime detenido: {model_id}")
            except Exception:
                pass

    atexit.register(_cleanup)

    def _handle_signal(signum, _frame):
        print(f"\n[TLAMATINI] Senal {signum} recibida. Cerrando...")
        _cleanup()
        raise SystemExit(130)

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(signum, _handle_signal)
        except Exception:
            pass

    return _cleanup


def _launch_gui(cleanup=None) -> None:
    import tkinter as tk
    try:
        from tkinterdnd2 import TkinterDnD
    except Exception:
        TkinterDnD = None

    from interfaz.dashboard import DashboardTLAMATINI
    from sistema.arranque import iniciar_sistema

    try:
        iniciar_sistema()
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo completar el arranque inicial: {e}")

    root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
    root.withdraw()
    dashboard = tk.Toplevel(root)

    def _close_app():
        if cleanup is not None:
            try:
                cleanup()
            except Exception:
                pass
        try:
            if dashboard.winfo_exists():
                dashboard.destroy()
        except Exception:
            pass
        try:
            root.quit()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

    dashboard.protocol("WM_DELETE_WINDOW", _close_app)
    root.protocol("WM_DELETE_WINDOW", _close_app)
    DashboardTLAMATINI(dashboard, app_root=root)
    root.mainloop()


def _report_startup_failure(exc: Exception) -> None:
    detail = traceback.format_exc()
    log_path = None

    try:
        paths = get_paths()
        log_path = paths.logs_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write("\n[TLAMATINI] Error fatal de arranque\n")
            handle.write(detail)
            if not detail.endswith("\n"):
                handle.write("\n")
    except Exception:
        log_path = None

    print("[TLAMATINI] Error fatal de arranque:", file=sys.stderr)
    print(detail, file=sys.stderr)

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        extra = f"\n\nLog: {log_path}" if log_path else ""
        messagebox.showerror(
            "TLAMATINI",
            f"No se pudo iniciar TLAMATINI.\n\n{exc}{extra}",
            parent=root,
        )
        root.destroy()
    except Exception:
        pass


def main():
    _asegurar_rutas_portables(Path.cwd())
    _asegurar_python_integrado()
    args = _parse_args()
    _apply_cli_overrides(args)
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if using_temporary_app_root():
        reason = storage_fallback_reason() or "ruta principal no escribible"
        print(f"[TLAMATINI] Advertencia: usando almacenamiento temporal en {get_paths().root_dir} ({reason})")

    cleanup = None
    if args.no_ai:
        print("[TLAMATINI] Arranque sin IA local (--no-ai).")
    else:
        backend = os.environ.get("TLAMATINI_AI_BACKEND", "").strip().lower() or "ollama"
        if backend == "ollama":
            host = configured_ollama_host()
            auto_pull = os.environ.get("TLAMATINI_AI_AUTO_PULL", "1").strip().lower() not in {"0", "false", "no"}
            print(f"[TLAMATINI] Backend IA activo: Ollama ({host})")
            ok, mensaje, selected_model = bootstrap_ollama_model(host, auto_pull=auto_pull)
            if not ok:
                fallback_ok, _ = _validar_runtime_local(base_dir, with_mistral=args.with_mistral)
                if not fallback_ok:
                    raise RuntimeError(mensaje)
                print(f"[TLAMATINI] {mensaje}")
                print("[TLAMATINI] Fallback automatico a runtime local empaquetado.")
                os.environ["TLAMATINI_AI_BACKEND"] = "local"
                backend = "local"
            else:
                if selected_model:
                    print(f"[TLAMATINI] Modelo IA activo: {selected_model}")
                print(f"[TLAMATINI] {mensaje}")
                cleanup = stop_local_ollama
        if backend != "ollama":
            ok, errores = _validar_archivos_ai(base_dir, with_mistral=args.with_mistral)
            if not ok:
                print("[TLAMATINI] No se puede iniciar IA local:")
                for error in errores:
                    print(f"- {error}")
                raise SystemExit(1)
            service, started_models = _boot_local_ai(base_dir, with_mistral=args.with_mistral)
            cleanup = _registrar_cleanup_ai(service, started_models)

    _launch_gui(cleanup=cleanup)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _report_startup_failure(exc)
        raise SystemExit(1)
