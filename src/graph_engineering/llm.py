"""Small DeepSeek/OpenAI-compatible setup kept separate from graph concepts."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


class MissingAPIKeyError(RuntimeError):
    """Raised when an optional provider-backed example is invoked without a key."""


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str | None
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "DeepSeekSettings":
        if env_file is not None:
            load_dotenv(Path(env_file))
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            model=os.getenv("DEEPSEEK_MODEL", cls.model),
            base_url=os.getenv("DEEPSEEK_BASE_URL", cls.base_url),
        )


def create_deepseek_client(
    settings: DeepSeekSettings,
    *,
    required: bool = False,
) -> OpenAI | None:
    """Return no client for optional examples or a clear error when required."""

    if not settings.api_key or settings.api_key == "your_deepseek_api_key_here":
        if required:
            raise MissingAPIKeyError(
                "DeepSeek is not configured. Copy .env.example to .env, set "
                "DEEPSEEK_API_KEY, and restart the notebook kernel."
            )
        return None
    return OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=60.0,
        max_retries=2,
    )


def chat(
    client: OpenAI,
    settings: DeepSeekSettings,
    *,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    max_tokens: int = 500,
) -> str | dict:
    """Call the existing OpenAI-compatible DeepSeek chat endpoint."""

    request: dict = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    if json_mode:
        request["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**request)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek returned an empty response.")
    return json.loads(content) if json_mode else content
