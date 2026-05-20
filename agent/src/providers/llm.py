"""LLM factory and JSON extraction helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore


if ChatOpenAI is not None:
    class ChatOpenAIWithReasoning(ChatOpenAI):  # type: ignore[misc,valid-type]
        """ChatOpenAI that preserves provider reasoning across invoke + stream.

        langchain-openai 0.3.x drops non-standard fields in three paths:
          * _convert_dict_to_message — invoke / ainvoke (inbound)
          * _convert_delta_to_message_chunk — stream / astream (inbound)
          * _convert_message_to_dict — request serialization (outbound)
        Moonshot/DeepSeek emit `reasoning_content`; OpenRouter relays as
        `reasoning`. Inbound paths normalize to additional_kwargs["reasoning_content"];
        outbound path re-injects it so strict providers (kimi-k2.5) accept
        multi-turn continuations.
        """

        @staticmethod
        def _capture(src: Any, msg: Any) -> None:
            if value := src.get("reasoning_content") or src.get("reasoning"):
                msg.additional_kwargs["reasoning_content"] = value

        def _create_chat_result(self, response, generation_info=None):  # type: ignore[override]
            result = super()._create_chat_result(response, generation_info)
            raw = response if isinstance(response, dict) else response.model_dump()
            for gen, choice in zip(result.generations, raw["choices"]):
                self._capture(choice["message"], gen.message)
            return result

        def _convert_chunk_to_generation_chunk(  # type: ignore[override]
            self,
            chunk: dict,
            default_chunk_class: type,
            base_generation_info: Optional[dict],
        ):
            gen = super()._convert_chunk_to_generation_chunk(
                chunk, default_chunk_class, base_generation_info
            )
            if gen is None:
                return None
            choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices")
            if choices:
                self._capture(choices[0]["delta"], gen.message)
            return gen

        def _get_request_payload(  # type: ignore[override]
            self,
            input_: Any,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
        ) -> dict:
            """Re-inject reasoning_content and normalize assistant content.

            LangChain strips ``reasoning_content`` when serializing AIMessages
            back to OpenAI wire format. Moonshot kimi-k2.5 also rejects
            assistant turns where ``content`` is null or ``reasoning_content``
            is absent, breaking ReAct continuations after a tool call (#39).
            """
            payload = super()._get_request_payload(input_, stop=stop, **kwargs)
            messages = super()._convert_input(input_).to_messages()
            for i, m in enumerate(payload["messages"]):
                if m.get("role") != "assistant":
                    continue
                if m.get("content") is None:
                    m["content"] = ""
                m["reasoning_content"] = messages[i].additional_kwargs.get("reasoning_content", "")
            return payload
else:
    ChatOpenAIWithReasoning = None  # type: ignore

AGENT_DIR = Path(__file__).resolve().parents[2]

# .env search order: ~/.vibe-trading/.env → agent/.env → $CWD/.env
_ENV_CANDIDATES = [
    Path.home() / ".vibe-trading" / ".env",
    AGENT_DIR / ".env",
    Path.cwd() / ".env",
]

_dotenv_loaded: bool = False


def _load_env_file(path: Path) -> None:
    """Load a single .env file into os.environ (setdefault, no override)."""
    if load_dotenv is not None:
        load_dotenv(dotenv_path=path, override=False)
    else:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _ensure_dotenv() -> None:
    """Load `.env` from the first found candidate path."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    for candidate in _ENV_CANDIDATES:
        if candidate.exists():
            _load_env_file(candidate)
            break
    _dotenv_loaded = True


def _sync_provider_env() -> None:
    """Map provider-specific env vars to OPENAI_* for ChatOpenAI.

    Each entry: provider_name -> (api_key_env, base_url_env).
    All base URLs must be set explicitly in .env — no hardcoded defaults.
    api_key_env=None means no key required (e.g. Ollama local).
    """
    _ensure_dotenv()
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").lower()

    if provider in {"openai-codex", "openai_codex"}:
        codex_url = os.getenv("OPENAI_CODEX_BASE_URL", "https://chatgpt.com/backend-api/codex/responses")
        os.environ["OPENAI_API_BASE"] = codex_url
        os.environ["OPENAI_BASE_URL"] = codex_url
        os.environ.pop("OPENAI_API_KEY", None)
        return

    # (api_key_env, base_url_env)
    _PROVIDER_MAP: dict[str, tuple[str | None, str]] = {
        "openai":     ("OPENAI_API_KEY",     "OPENAI_BASE_URL"),
        "openrouter": ("OPENROUTER_API_KEY",  "OPENROUTER_BASE_URL"),
        "deepseek":   ("DEEPSEEK_API_KEY",    "DEEPSEEK_BASE_URL"),
        "gemini":     ("GEMINI_API_KEY",      "GEMINI_BASE_URL"),
        "groq":       ("GROQ_API_KEY",        "GROQ_BASE_URL"),
        "dashscope":  ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
        "qwen":       ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
        "zhipu":      ("ZHIPU_API_KEY",       "ZHIPU_BASE_URL"),
        "moonshot":   ("MOONSHOT_API_KEY",    "MOONSHOT_BASE_URL"),
        "minimax":    ("MINIMAX_API_KEY",     "MINIMAX_BASE_URL"),
        "mimo":       ("MIMO_API_KEY",        "MIMO_BASE_URL"),
        "zai":        ("ZAI_API_KEY",         "ZAI_BASE_URL"),
        "ollama":     (None,                  "OLLAMA_BASE_URL"),
    }

    spec = _PROVIDER_MAP.get(provider, _PROVIDER_MAP["openai"])
    key_env, base_env = spec

    # Resolve API key: provider-specific env → OPENAI_API_KEY fallback
    if key_env is not None:
        api_key = os.getenv(key_env, "") or os.getenv("OPENAI_API_KEY", "")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "") or "ollama"

    # Resolve base URL: provider-specific env → OPENAI_BASE_URL fallback
    base_url = os.getenv(base_env, "") or os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "")

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ.setdefault("OPENAI_BASE_URL", base_url)


def _build_single_llm(
    *,
    provider: str,
    model_name: str,
    api_key: str,
    base_url: str,
    callbacks: Any = None,
) -> Any:
    """Build one ChatOpenAI instance from explicit params."""
    if ChatOpenAI is None:
        raise RuntimeError("langchain-openai is not installed")
    temperature = float(os.getenv("LANGCHAIN_TEMPERATURE", "0.0"))
    if provider == "minimax" and temperature <= 0.0:
        temperature = 0.01
    effort = os.getenv("LANGCHAIN_REASONING_EFFORT", "").strip().lower()
    return ChatOpenAIWithReasoning(
        model=model_name,
        openai_api_key=api_key or "none",
        openai_api_base=base_url,
        temperature=temperature,
        timeout=int(os.getenv("TIMEOUT_SECONDS", "120")),
        max_retries=0,  # fallback wrapper handles retries across providers
        callbacks=callbacks,
        extra_body={"reasoning": {"effort": effort}} if effort else None,
    )


def _load_fallback_chain(callbacks: Any = None) -> list:
    """Read FALLBACK_N_* env vars and return a list of LLM instances.

    Format in .env:
        FALLBACK_1_PROVIDER=deepseek
        FALLBACK_1_MODEL=deepseek-chat
        FALLBACK_1_API_KEY=sk-xxx
        FALLBACK_1_BASE_URL=https://api.deepseek.com/v1
    """
    _ensure_dotenv()
    chain = []
    for i in range(1, 10):
        provider = os.getenv(f"FALLBACK_{i}_PROVIDER", "").strip()
        model = os.getenv(f"FALLBACK_{i}_MODEL", "").strip()
        key = os.getenv(f"FALLBACK_{i}_API_KEY", "").strip()
        url = os.getenv(f"FALLBACK_{i}_BASE_URL", "").strip()
        if not provider or not model:
            break
        try:
            llm = _build_single_llm(
                provider=provider, model_name=model,
                api_key=key, base_url=url, callbacks=callbacks,
            )
            chain.append((f"{provider}/{model}", llm))
        except Exception:
            pass
    return chain


class FallbackLLM:
    """Wraps a primary LLM with an ordered fallback chain.

    Transparently proxies invoke/stream/ainvoke/astream.
    Falls back to the next provider on 5xx / connection errors.
    """

    _FALLBACK_CODES = {500, 502, 503, 504}

    def __init__(self, primary_name: str, primary: Any, fallbacks: list) -> None:
        self._primary_name = primary_name
        self._chain = [(primary_name, primary)] + fallbacks
        # Expose attributes expected by LangChain / agent loop
        self.model_name = getattr(primary, "model_name", primary_name)
        self.callbacks = getattr(primary, "callbacks", None)

    def _should_fallback(self, exc: Exception) -> bool:
        code = getattr(getattr(exc, "response", None), "status_code", None) \
               or getattr(exc, "status_code", None)
        if code in self._FALLBACK_CODES:
            return True
        msg = str(exc).lower()
        return any(k in msg for k in ("upstream", "connection", "timeout", "502", "503", "504"))

    def _try_chain(self, method: str, *args: Any, **kwargs: Any) -> Any:
        import logging
        log = logging.getLogger(__name__)
        last_exc: Exception = RuntimeError("no providers configured")
        for name, llm in self._chain:
            try:
                return getattr(llm, method)(*args, **kwargs)
            except Exception as exc:
                if self._should_fallback(exc):
                    log.warning("Provider %s failed (%s), trying next…", name, exc)
                    last_exc = exc
                else:
                    raise
        raise last_exc

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._try_chain("invoke", *args, **kwargs)

    def stream(self, *args: Any, **kwargs: Any) -> Any:
        return self._try_chain("stream", *args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        import logging
        log = logging.getLogger(__name__)
        last_exc: Exception = RuntimeError("no providers configured")
        for name, llm in self._chain:
            try:
                return await llm.ainvoke(*args, **kwargs)
            except Exception as exc:
                if self._should_fallback(exc):
                    log.warning("Provider %s failed (%s), trying next…", name, exc)
                    last_exc = exc
                else:
                    raise
        raise last_exc

    async def astream(self, *args: Any, **kwargs: Any):
        import logging
        log = logging.getLogger(__name__)
        last_exc: Exception = RuntimeError("no providers configured")
        for name, llm in self._chain:
            try:
                async for chunk in llm.astream(*args, **kwargs):
                    yield chunk
                return
            except Exception as exc:
                if self._should_fallback(exc):
                    log.warning("Provider %s failed (%s), trying next…", name, exc)
                    last_exc = exc
                else:
                    raise
        raise last_exc

    def bind_tools(self, *args: Any, **kwargs: Any) -> "FallbackLLM":
        bound_chain = [(n, llm.bind_tools(*args, **kwargs)) for n, llm in self._chain]
        obj = FallbackLLM.__new__(FallbackLLM)
        obj._primary_name = self._primary_name
        obj._chain = bound_chain
        obj.model_name = self.model_name
        obj.callbacks = self.callbacks
        return obj

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chain[0][1], name)


def build_llm(*, model_name: Optional[str] = None, callbacks: Any = None) -> Any:
    """Construct an LLM instance with optional fallback chain.

    Primary provider is read from LANGCHAIN_PROVIDER / LANGCHAIN_MODEL_NAME.
    Additional fallbacks are read from FALLBACK_N_PROVIDER / FALLBACK_N_MODEL /
    FALLBACK_N_API_KEY / FALLBACK_N_BASE_URL (N = 1, 2, 3, …).

    Args:
        model_name: Model name override; defaults to LANGCHAIN_MODEL_NAME.
        callbacks: Optional LangChain callbacks.

    Returns:
        FallbackLLM wrapping one or more ChatOpenAI instances.

    Raises:
        RuntimeError: If langchain-openai is missing or LANGCHAIN_MODEL_NAME is unset.
    """
    _sync_provider_env()
    name = model_name or os.getenv("LANGCHAIN_MODEL_NAME", "").strip()
    if not name:
        raise RuntimeError("LANGCHAIN_MODEL_NAME is not set")
    temperature = float(os.getenv("LANGCHAIN_TEMPERATURE", "0.0"))
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").lower()
    if provider in {"openai-codex", "openai_codex"}:
        from src.providers.openai_codex import OpenAICodexLLM

        effort = os.getenv("LANGCHAIN_REASONING_EFFORT", "").strip().lower()
        return OpenAICodexLLM(
            model=name,
            temperature=temperature,
            timeout=int(os.getenv("TIMEOUT_SECONDS", "120")),
            reasoning_effort=effort or None,
        )

    if ChatOpenAI is None:
        raise RuntimeError("langchain-openai is not installed")
    if provider == "minimax" and temperature <= 0.0:
        temperature = 0.01
    effort = os.getenv("LANGCHAIN_REASONING_EFFORT", "").strip().lower()
    # Qwen3 thinking models: disable by default for speed unless explicitly enabled
    extra: dict = {}
    if effort:
        extra["reasoning"] = {"effort": effort}
    if provider in {"dashscope", "qwen"} and not effort:
        extra["enable_thinking"] = False
    primary = ChatOpenAIWithReasoning(
        model=name,
        temperature=temperature,
        timeout=int(os.getenv("TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("MAX_RETRIES", "2")),
        callbacks=callbacks,
        extra_body=extra if extra else None,
    )
    fallbacks = _load_fallback_chain(callbacks=callbacks)
    if not fallbacks:
        return primary
    return FallbackLLM(f"{provider}/{name}", primary, fallbacks)


def _extract_balanced_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract the outermost JSON object from text using bracket balancing.

    Args:
        text: Text that may embed a JSON object.

    Returns:
        Parsed dict, or None on failure.
    """
    start = -1
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = -1
    return None
