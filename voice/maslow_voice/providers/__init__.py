"""Provider selection for Maslow Voice.

This package deliberately does not import optional cloud or model SDKs at import
time. A provider reports a clear, sanitized configuration error when its selected
runtime dependency is absent; it never falls back to a different provider.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from maslow_voice.errors import VoiceError

from .base import VoiceProvider
from .livekit_expressive import LiveKitExpressiveProvider
from .local import LocalProvider
from .openai_realtime import OpenAIRealtimeProvider

Emit = Callable[[dict[str, Any]], Awaitable[None]]
Submit = Callable[[dict[str, Any], str], Awaitable[dict[str, Any]]]


def create_provider(
    config: dict[str, Any],
    secrets: dict[str, str],
    emit: Emit,
    submit: Submit,
    audio_transport: Any = None,
) -> VoiceProvider:
    """Create exactly the configured provider.

    ``mode`` is a user-owned choice. It is intentionally strict: an unknown
    mode, a missing credential, or a failed connection is surfaced to the UI
    rather than redirecting speech to another service.
    """

    mode = str(config.get("mode", "")).strip().lower()
    common = {
        "config": config,
        "secrets": secrets,
        "emit": emit,
        "submit": submit,
        "audio_transport": audio_transport,
    }
    if mode == "livekit":
        return LiveKitExpressiveProvider(**common)
    if mode == "openai":
        return OpenAIRealtimeProvider(**common)
    if mode in {"offline", "server"}:
        return LocalProvider(**common)
    raise VoiceError("INVALID_SETTINGS", "Choose one of the supported Voice options.")


__all__ = ["VoiceProvider", "create_provider"]
