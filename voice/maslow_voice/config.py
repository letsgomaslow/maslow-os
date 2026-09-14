"""Non-secret preferences. Credentials live exclusively in Secret Service."""

import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .errors import VoiceError
from .voices import LIVEKIT_VOICES, LIVE_VOICES, OPENAI_VOICES

DEFAULTS = {
    "mode": "openai", "server_kind": "ollama", "server_url": "http://127.0.0.1:11434",
    "model": "", "execution_model": "", "default_coder": "codex",
    "realtime_model": "gpt-realtime-2.1", "realtime_voice": "cedar", "live_voice": "marin",
    "livekit_url": "", "livekit_voice": "Ashley",
    "reduced_motion": False, "fixed_position": False, "display": "",
    "idle_seconds": 60, "retention_days": 30, "microphone_device": "",
    "speaker_device": "", "ollama_models": "", "speech_directory": "",
}


def private_directory(path: Path) -> Path:
    if path.is_symlink():
        raise VoiceError("UNSAFE_STATE", "The Voice storage folder must not be a symbolic link.")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid():
        raise VoiceError("UNSAFE_STATE", "Voice storage belongs to another user.")
    path.chmod(0o700)
    return path


def state_directory() -> Path:
    return private_directory(Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "maslow-voice")


def runtime_directory() -> Path:
    root = os.environ.get("XDG_RUNTIME_DIR")
    if not root:
        raise VoiceError("NO_USER_SESSION", "Start Voice from your desktop session.")
    return private_directory(Path(root) / "maslow-voice")


def validate_endpoint(value: str, *, livekit=False) -> str:
    try:
        p = urlsplit(value)
        valid_schemes = {"wss", "https"} if livekit else {"https", "http"}
        if p.scheme not in valid_schemes or not p.hostname or p.username or p.password or p.query or p.fragment:
            raise ValueError()
        p.port
        if any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError()
    except (ValueError, TypeError):
        raise VoiceError("INVALID_ENDPOINT", "Enter a server address without credentials, query parameters, or fragments.") from None
    return value.rstrip("/")


def validate_settings(settings: dict) -> dict:
    if not isinstance(settings, dict) or set(settings) - set(DEFAULTS):
        raise VoiceError("INVALID_SETTINGS", "Voice settings contain an unsupported field.")
    result = dict(DEFAULTS, **settings)
    for key, choices in {"mode": {"offline", "server", "livekit", "openai", "gpt_live"}, "server_kind": {"ollama", "lmstudio"}, "default_coder": {"codex", "claude", "hermes"}, "realtime_voice": set(OPENAI_VOICES), "live_voice": set(LIVE_VOICES), "livekit_voice": set(LIVEKIT_VOICES)}.items():
        if not isinstance(result[key], str) or result[key] not in choices:
            raise VoiceError("INVALID_SETTINGS", "Choose one of the supported Voice options.")
    for key in ("reduced_motion", "fixed_position"):
        if type(result[key]) is not bool:
            raise VoiceError("INVALID_SETTINGS", "The motion preferences must be on or off.")
    for key, bounds in {"idle_seconds": (15, 300), "retention_days": (1, 365)}.items():
        if type(result[key]) is not int or not bounds[0] <= result[key] <= bounds[1]:
            raise VoiceError("INVALID_SETTINGS", "The timeout or history duration is outside the supported range.")
    for key, default in DEFAULTS.items():
        if isinstance(default, str) and (not isinstance(result[key], str) or len(result[key]) > 4096 or "\x00" in result[key]):
            raise VoiceError("INVALID_SETTINGS", "A Voice setting has an invalid value.")
    result["server_url"] = validate_endpoint(result["server_url"])
    if result["livekit_url"]:
        result["livekit_url"] = validate_endpoint(result["livekit_url"], livekit=True)
    return result


def atomic_json(path: Path, value):
    private_directory(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=".voice-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Settings:
    def __init__(self, directory=None):
        self.directory = private_directory(Path(directory)) if directory else state_directory()
        self.path = self.directory / "settings.json"
        try:
            self.value = validate_settings(json.loads(self.path.read_text())) if self.path.exists() else dict(DEFAULTS)
        except (OSError, json.JSONDecodeError):
            raise VoiceError("SETTINGS_UNREADABLE", "Voice settings could not be read. Restore the saved settings before continuing.") from None

    def update(self, changes):
        if not isinstance(changes, dict):
            raise VoiceError("INVALID_SETTINGS", "Settings must be an object.")
        value = validate_settings(dict(self.value, **changes))
        atomic_json(self.path, value)
        self.value = value
        return dict(value)
