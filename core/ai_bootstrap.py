import os
from typing import Iterable, Optional

from core.model_router import canonical_model_id, ollama_model_name
from core.ollama_local import ensure_local_ollama, list_ollama_models, pull_ollama_model


KNOWN_OLLAMA_MODELS = [
    "gemma3:4b",
    "gemma3:latest",
    "llama3:latest",
    "mistral:latest",
]


def preferred_ollama_model() -> str:
    local_model = os.environ.get("TLAMATINI_LOCAL_LLM_MODEL", "").strip()
    if local_model:
        return local_model
    primary = os.environ.get("TLAMATINI_PRIMARY_MODEL", "").strip()
    return ollama_model_name(primary or "gemma3:4b")


def choose_ollama_model(preferred_model: str, available_models: Iterable[str]) -> Optional[str]:
    available = [str(item or "").strip() for item in available_models if str(item or "").strip()]
    if not available:
        return None

    preferred = str(preferred_model or "").strip() or "gemma3:4b"
    if preferred in available:
        return preferred

    preferred_canonical = canonical_model_id(preferred)
    for candidate in available:
        if canonical_model_id(candidate) == preferred_canonical:
            return candidate

    for known in KNOWN_OLLAMA_MODELS:
        if known in available:
            return known
        known_canonical = canonical_model_id(known)
        for candidate in available:
            if canonical_model_id(candidate) == known_canonical:
                return candidate

    return available[0]


def apply_ollama_model_selection(selected_model: str) -> str:
    selected = str(selected_model or "").strip() or "gemma3:4b"
    os.environ["TLAMATINI_LOCAL_LLM_MODEL"] = selected
    canonical = canonical_model_id(selected)
    if canonical in {"gemma3", "llama3", "mistral"}:
        os.environ["TLAMATINI_PRIMARY_MODEL"] = canonical
    if canonical == "mistral":
        os.environ["TLAMATINI_ENABLE_MISTRAL"] = "1"
    return selected


def bootstrap_ollama_model(host: str, auto_pull: bool = True) -> tuple[bool, str, Optional[str]]:
    preferred = preferred_ollama_model()

    ok, mensaje = ensure_local_ollama(host)
    if not ok:
        return False, mensaje, None

    available = list_ollama_models(host)
    selected = choose_ollama_model(preferred, available)
    if selected:
        selected = apply_ollama_model_selection(selected)
        if selected == preferred:
            return True, f"Ollama listo con el modelo principal {selected}.", selected
        return True, f"Ollama listo con fallback {selected} (faltaba {preferred}).", selected

    if auto_pull:
        ok, mensaje = pull_ollama_model(preferred, host)
        if not ok:
            return False, mensaje, None
        available = list_ollama_models(host)
        selected = choose_ollama_model(preferred, available)
        if selected:
            selected = apply_ollama_model_selection(selected)
            return True, f"Ollama listo tras descargar {selected}.", selected

    return False, "Ollama arrancó, pero no hay modelos disponibles para TLAMATINI.", None
