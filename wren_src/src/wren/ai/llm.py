"""
Low-level LLM routing for Wren.

This module is responsible for talking to the underlying AI provider
and should be kept separate from the higher-level type inference logic.
"""

import logging
from typing import Any

from ..core.config import get_config
from ..errors.base import AIProviderError, ConfigurationError

logger = logging.getLogger(__name__)


class LLMRouter:
    """Thin wrapper around OpenAI client."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Instantiate the OpenAI client lazily."""
        if self._client is None:
            config = get_config()

            if not config.openai_api_key:
                raise ConfigurationError.missing_api_key("OpenAI")

            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=config.openai_api_key)
            except ImportError:
                raise ConfigurationError(
                    message="OpenAI package not installed",
                    fix="Install OpenAI package",
                    example="pip install openai",
                )

        return self._client

    def complete(
        self,
        prompt: str | None = None,
        *,
        messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Send a completion request to the LLM provider."""
        config = get_config()
        client = self._get_client()

        # Normalize into chat messages
        if messages is None:
            if prompt is None:
                raise ValueError("Either prompt or messages must be provided")
            messages = [{"role": "user", "content": prompt}]
        elif prompt:
            messages = [*messages, {"role": "user", "content": prompt}]

        if config.show_prompts:
            rendered = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
            )
            logger.info(f"LLM prompt:\n{rendered}")

        params = dict(kwargs)
        model = params.pop("model", config.default_model)
        temperature = params.pop("temperature", config.ai_temperature)
        max_tokens = params.pop("max_tokens", config.ai_max_tokens)

        request_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **params,
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        # Remove Portkey-specific model routing
        # OpenAI models are used directly

        try:
            response = client.chat.completions.create(**request_params)
            return response.choices[0].message.content
        except Exception as exc:
            raise AIProviderError.api_error("OpenAI", exc)


# Shared router instance
llm_router = LLMRouter()


class LLMInterface:
    """Public API for issuing low-level LLM calls from the SDK."""

    def __init__(self, router: LLMRouter):
        self._router = router

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        return self.complete(prompt, **kwargs)

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Request a completion using a simple prompt."""
        return self._router.complete(prompt, **kwargs)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Allow callers to provide fully formed chat messages."""
        return self._router.complete(messages=messages, **kwargs)


# Exported public interface
llm = LLMInterface(llm_router)


def call_llm(prompt: str, **kwargs: Any) -> str:
    """Convenience helper used internally when a raw LLM call is needed."""
    return llm(prompt, **kwargs)
