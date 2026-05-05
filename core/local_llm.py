import os
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterator, Optional, Tuple

from core.ai_engine import (
    MODEL_ROUTE_CLASSIFICATION,
    MODEL_ROUTE_DOCUMENTS,
    MODEL_ROUTE_GENERAL,
    MODEL_ROUTE_SUMMARY,
    get_ai_engine,
)
from core.model_router import ollama_model_name, primary_model, resolve_model


DEFAULT_TEMPERATURE = float(os.environ.get("TLAMATINI_LOCAL_LLM_TEMPERATURE", "0.3"))
DEFAULT_TOP_P = float(os.environ.get("TLAMATINI_LOCAL_LLM_TOP_P", "0.9"))
DEFAULT_MAX_TOKENS = int(os.environ.get("TLAMATINI_LOCAL_LLM_MAX_TOKENS", "640"))
DEFAULT_TIMEOUT = int(os.environ.get("TLAMATINI_LOCAL_LLM_TIMEOUT", "12"))
DEFAULT_CONTEXT_WINDOW = int(os.environ.get("TLAMATINI_LOCAL_LLM_CONTEXT", "2048"))


def _default_local_model() -> str:
    return os.environ.get("TLAMATINI_LOCAL_LLM_MODEL", "").strip() or primary_model()


def _default_backend() -> str:
    return os.environ.get("TLAMATINI_AI_BACKEND", "").strip().lower() or "ollama"


def _default_ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11436").strip() or "http://127.0.0.1:11436"


@dataclass
class LocalLLMConfig:
    model: str = field(default_factory=_default_local_model)
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: int = DEFAULT_TIMEOUT
    context_window: int = DEFAULT_CONTEXT_WINDOW
    route: str = MODEL_ROUTE_GENERAL


class LocalLLMProvider:
    provider_name = "tlamatini_local_ai"

    def is_available(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def generate(self, prompt: str, system_prompt: str = "", config: Optional[LocalLLMConfig] = None) -> str:
        raise NotImplementedError

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[LocalLLMConfig] = None,
    ) -> Iterator[str]:
        respuesta = self.generate(prompt=prompt, system_prompt=system_prompt, config=config)
        if respuesta:
            yield respuesta


class TlamatiniLocalProvider(LocalLLMProvider):
    provider_name = "local_ai_internal"

    def __init__(self):
        self.engine = get_ai_engine()

    def _route_from_config(self, config: Optional[LocalLLMConfig]) -> str:
        cfg = config or LocalLLMConfig()
        model_id = resolve_model(cfg.model, route=cfg.route)
        if model_id == "mistral" and cfg.route not in {MODEL_ROUTE_CLASSIFICATION, MODEL_ROUTE_SUMMARY, MODEL_ROUTE_DOCUMENTS}:
            return MODEL_ROUTE_DOCUMENTS
        return cfg.route or MODEL_ROUTE_GENERAL

    def is_available(self) -> Tuple[bool, str]:
        return self.engine.is_available(route=MODEL_ROUTE_GENERAL, model=primary_model())

    def generate(self, prompt: str, system_prompt: str = "", config: Optional[LocalLLMConfig] = None) -> str:
        cfg = config or LocalLLMConfig()
        route = self._route_from_config(cfg)
        return self.engine.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            route=route,
            model=cfg.model,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_tokens,
            context_window=cfg.context_window,
            timeout=cfg.timeout,
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[LocalLLMConfig] = None,
    ) -> Iterator[str]:
        cfg = config or LocalLLMConfig()
        route = self._route_from_config(cfg)
        yield from self.engine.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            route=route,
            model=cfg.model,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_tokens,
            context_window=cfg.context_window,
            timeout=cfg.timeout,
        )


class OllamaProvider(LocalLLMProvider):
    provider_name = "ollama"

    def __init__(self):
        self.host = _default_ollama_host().rstrip("/")

    def _payload(self, prompt: str, system_prompt: str, cfg: LocalLLMConfig, stream: bool) -> dict:
        payload = {
            "model": ollama_model_name(cfg.model),
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": stream,
            "keep_alive": "30m",
            "options": {
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "num_ctx": cfg.context_window,
            },
        }
        if int(cfg.max_tokens or 0) > 0:
            payload["options"]["num_predict"] = int(cfg.max_tokens)
        return payload

    def _request(self, path: str, payload: Optional[dict] = None, timeout: float = 15.0) -> dict:
        data = None
        headers = {}
        method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
            method = "POST"
        req = urllib.request.Request(f"{self.host}{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def is_available(self) -> Tuple[bool, str]:
        try:
            data = self._request("/api/tags")
            modelos = [str(item.get("name", "")).strip() for item in data.get("models", [])]
            esperado = ollama_model_name(_default_local_model())
            if esperado in modelos:
                return True, f"Ollama disponible con {esperado}."
            return False, f"Ollama activo pero falta el modelo {esperado}."
        except Exception as exc:
            return False, f"No se pudo conectar con Ollama en {self.host}: {exc}"

    def generate(self, prompt: str, system_prompt: str = "", config: Optional[LocalLLMConfig] = None) -> str:
        cfg = config or LocalLLMConfig()
        payload = self._payload(prompt=prompt, system_prompt=system_prompt, cfg=cfg, stream=False)
        try:
            data = self._request("/api/generate", payload, timeout=max(60.0, float(cfg.timeout or 0)))
        except urllib.error.HTTPError as exc:
            detalle = exc.read().decode("utf-8", errors="ignore").strip()
            raise RuntimeError(detalle or f"Ollama devolvió HTTP {exc.code}.") from exc
        except Exception as exc:
            raise RuntimeError(f"No se pudo generar respuesta con Ollama: {exc}") from exc
        return str(data.get("response", "")).strip()

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        config: Optional[LocalLLMConfig] = None,
    ) -> Iterator[str]:
        cfg = config or LocalLLMConfig()
        payload = self._payload(prompt=prompt, system_prompt=system_prompt, cfg=cfg, stream=True)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=max(60.0, float(cfg.timeout or 0))) as response:
                for raw_line in response:
                    linea = raw_line.decode("utf-8", errors="ignore").strip()
                    if not linea:
                        continue
                    try:
                        chunk = json.loads(linea)
                    except json.JSONDecodeError:
                        continue
                    texto = str(chunk.get("response", "") or "")
                    if texto:
                        yield texto
        except urllib.error.HTTPError as exc:
            detalle = exc.read().decode("utf-8", errors="ignore").strip()
            raise RuntimeError(detalle or f"Ollama devolvió HTTP {exc.code}.") from exc
        except Exception as exc:
            raise RuntimeError(f"No se pudo generar respuesta con Ollama: {exc}") from exc


def obtener_local_llm_provider() -> LocalLLMProvider:
    if _default_backend() == "ollama":
        return OllamaProvider()
    return TlamatiniLocalProvider()
