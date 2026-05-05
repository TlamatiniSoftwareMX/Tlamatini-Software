import os
from typing import Dict, Optional


MODEL_ROUTE_GENERAL = "general"
MODEL_ROUTE_DOCUMENTS = "documents"
MODEL_ROUTE_CLASSIFICATION = "classification"
MODEL_ROUTE_SUMMARY = "summary"


def canonical_model_id(model: Optional[str]) -> str:
    model_id = (model or "").strip().lower()
    aliases: Dict[str, str] = {
        "gemma3": "gemma3",
        "gemma3:4b": "gemma3",
        "gemma3:latest": "gemma3",
        "llama3": "llama3",
        "llama3:latest": "llama3",
        "mistral": "mistral",
        "mistral:latest": "mistral",
    }
    return aliases.get(model_id, model_id)


def ollama_model_name(model: Optional[str]) -> str:
    model_id = canonical_model_id(model)
    aliases: Dict[str, str] = {
        "gemma3": "gemma3:4b",
        "llama3": "llama3:latest",
        "mistral": "mistral:latest",
    }
    return aliases.get(model_id, (model or "").strip() or "gemma3:4b")


def primary_model() -> str:
    configured = os.environ.get("TLAMATINI_PRIMARY_MODEL", "").strip().lower() or "gemma3"
    model_id = canonical_model_id(configured)
    if model_id in {"gemma3", "mistral", "llama3"}:
        return model_id
    return "gemma3"


def mistral_enabled() -> bool:
    return os.environ.get("TLAMATINI_ENABLE_MISTRAL", "0").strip().lower() in {"1", "true", "yes"}


def route_default_model(route: str = MODEL_ROUTE_GENERAL) -> str:
    route_id = (route or MODEL_ROUTE_GENERAL).strip().lower()
    if route_id == MODEL_ROUTE_GENERAL:
        return primary_model()
    if route_id in {MODEL_ROUTE_DOCUMENTS, MODEL_ROUTE_CLASSIFICATION, MODEL_ROUTE_SUMMARY}:
        return "mistral" if mistral_enabled() else primary_model()
    return primary_model()


def resolve_model(model: Optional[str] = None, route: str = MODEL_ROUTE_GENERAL) -> str:
    model_id = canonical_model_id(model)
    if model_id in {"gemma3", "llama3", "mistral"}:
        return model_id

    aliases: Dict[str, str] = {
        "gemma3:latest": "gemma3",
        "gemma3:4b": "gemma3",
        "llama3:latest": "llama3",
        "mistral:latest": "mistral",
        "chat": primary_model(),
        "general": primary_model(),
        "documental": route_default_model(MODEL_ROUTE_DOCUMENTS),
        "documents": route_default_model(MODEL_ROUTE_DOCUMENTS),
        "classification": route_default_model(MODEL_ROUTE_CLASSIFICATION),
        "summary": route_default_model(MODEL_ROUTE_SUMMARY),
    }
    if model_id in aliases:
        return aliases[model_id]

    return route_default_model(route)
