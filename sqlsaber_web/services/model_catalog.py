"""Helpers for exposing supported AI providers/models to the frontend.

The Settings page uses this to populate provider/model dropdowns.

Important: this module must not make network requests at runtime.
"""

from __future__ import annotations

from collections.abc import Iterable

ALLOWED_MODEL_PROVIDERS: tuple[str, ...] = ("anthropic", "openai", "google")
PROVIDER_LABELS: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
}


# Snapshot of `sqlsaber models list` filtered to chat-capable models only.
# Excludes embeddings and specialized TTS/image/audio variants.
AVAILABLE_MODELS_BY_PROVIDER: dict[str, list[dict]] = {
    "anthropic": [
        {
            "id": "anthropic:claude-opus-4-5",
            "name": "Claude Opus 4.5 (latest)",
            "description": "$5/25 per 1M tokens",
            "context_length": 200000,
        },
        {
            "id": "anthropic:claude-sonnet-4-5",
            "name": "Claude Sonnet 4.5 (latest)",
            "description": "$3/15 per 1M tokens",
            "context_length": 200000,
        },
        {
            "id": "anthropic:claude-haiku-4-5",
            "name": "Claude Haiku 4.5 (latest)",
            "description": "$1/5 per 1M tokens",
            "context_length": 200000,
        },
    ],
    "openai": [
        {
            "id": "openai:gpt-5.2",
            "name": "GPT-5.2",
            "description": "$1.75/14 per 1M tokens",
            "context_length": 400000,
        },
        {
            "id": "openai:gpt-5.1",
            "name": "GPT-5.1",
            "description": "$1.25/10 per 1M tokens",
            "context_length": 400000,
        },
        {
            "id": "openai:gpt-5.1-codex",
            "name": "GPT-5.1 Codex",
            "description": "$1.25/10 per 1M tokens",
            "context_length": 400000,
        },
        {
            "id": "openai:gpt-5.1-codex-max",
            "name": "GPT-5.1 Codex Max",
            "description": "$1.25/10 per 1M tokens",
            "context_length": 400000,
        },
        {
            "id": "openai:gpt-5.1-codex-mini",
            "name": "GPT-5.1 Codex mini",
            "description": "$0.25/2 per 1M tokens",
            "context_length": 400000,
        },
        {
            "id": "openai:gpt-5.2-pro",
            "name": "GPT-5.2 Pro",
            "description": "$21/168 per 1M tokens",
            "context_length": 400000,
        },
    ],
    "google": [
        {
            "id": "google:gemini-3-flash-preview",
            "name": "Gemini 3 Flash Preview",
            "description": "$0.5/3 per 1M tokens",
            "context_length": 1048576,
        },
        {
            "id": "google:gemini-3-pro-preview",
            "name": "Gemini 3 Pro Preview",
            "description": "$2/12 per 1M tokens",
            "context_length": 1000000,
        },
        {
            "id": "google:gemini-2.5-flash",
            "name": "Gemini 2.5 Flash",
            "description": "$0.3/2.5 per 1M tokens",
            "context_length": 1048576,
        },
        {
            "id": "google:gemini-2.5-pro",
            "name": "Gemini 2.5 Pro",
            "description": "$1.25/10 per 1M tokens",
            "context_length": 1048576,
        },
        {
            "id": "google:gemini-2.0-flash",
            "name": "Gemini 2.0 Flash",
            "description": "$0.1/0.4 per 1M tokens",
            "context_length": 1048576,
        },
    ],
}


def normalize_provider(provider: str | None) -> str:
    return (provider or "").strip().lower()


def is_allowed_provider(provider: str | None) -> bool:
    return normalize_provider(provider) in ALLOWED_MODEL_PROVIDERS


def get_provider_options() -> list[dict[str, str]]:
    return [
        {"key": key, "label": PROVIDER_LABELS.get(key, key)}
        for key in ALLOWED_MODEL_PROVIDERS
    ]


def get_available_models_catalog(
    *, providers: Iterable[str] = ALLOWED_MODEL_PROVIDERS
) -> dict:
    """Return catalog of available models for the UI.

    Shape:
      {
        "providers": [{"key": "openai", "label": "OpenAI"}, ...],
        "models_by_provider": {
          "openai": [{"id": "openai:gpt-5", "name": "GPT-5", ...}, ...],
          ...
        },
      }
    """

    requested = {normalize_provider(p) for p in providers}

    models_by_provider: dict[str, list[dict]] = {}
    for provider in ALLOWED_MODEL_PROVIDERS:
        if provider in requested:
            models_by_provider[provider] = [*AVAILABLE_MODELS_BY_PROVIDER[provider]]
        else:
            models_by_provider[provider] = []

    return {
        "providers": get_provider_options(),
        "models_by_provider": models_by_provider,
    }
