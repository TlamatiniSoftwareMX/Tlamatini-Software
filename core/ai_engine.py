from typing import Iterator, Optional, Tuple

from core.local_inference_service import get_local_inference_service
from core.model_router import (
    MODEL_ROUTE_CLASSIFICATION,
    MODEL_ROUTE_DOCUMENTS,
    MODEL_ROUTE_GENERAL,
    MODEL_ROUTE_SUMMARY,
    resolve_model,
)


class AIEngine:
    def __init__(self):
        self.service = get_local_inference_service()

    def is_available(self, route: str = MODEL_ROUTE_GENERAL, model: Optional[str] = None) -> Tuple[bool, str]:
        model_id = resolve_model(model=model, route=route)
        return self.service.is_available(model_id)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        route: str = MODEL_ROUTE_GENERAL,
        model: Optional[str] = None,
        temperature: float = 0.0,
        top_p: float = 0.9,
        max_tokens: int = 256,
        context_window: int = 4096,
        timeout: float | None = None,
    ) -> str:
        model_id = resolve_model(model=model, route=route)
        options = {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "context_window": context_window,
        }
        if timeout is not None:
            options["timeout"] = timeout
        return self.service.generate(model_id=model_id, prompt=prompt, system_prompt=system_prompt, options=options)

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        route: str = MODEL_ROUTE_GENERAL,
        model: Optional[str] = None,
        temperature: float = 0.0,
        top_p: float = 0.9,
        max_tokens: int = 256,
        context_window: int = 4096,
        timeout: float | None = None,
    ) -> Iterator[str]:
        model_id = resolve_model(model=model, route=route)
        options = {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "context_window": context_window,
        }
        if timeout is not None:
            options["timeout"] = timeout
        yield from self.service.generate_stream(model_id=model_id, prompt=prompt, system_prompt=system_prompt, options=options)


def get_ai_engine() -> AIEngine:
    return AIEngine()


__all__ = [
    "AIEngine",
    "MODEL_ROUTE_GENERAL",
    "MODEL_ROUTE_DOCUMENTS",
    "MODEL_ROUTE_CLASSIFICATION",
    "MODEL_ROUTE_SUMMARY",
    "get_ai_engine",
]
