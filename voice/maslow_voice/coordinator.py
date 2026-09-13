"""Dedicated Hermes profiles, with explicit inference and a bounded tool plugin."""

import asyncio
import hashlib
import json
import os
import secrets
import shutil
import socket
from pathlib import Path

from .config import atomic_json, private_directory
from .errors import VoiceError
from .hermes import HermesClient

PROVIDER_KEYS = {
    "openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
    "nous-api": "NOUS_API_KEY", "lmstudio": "LM_API_KEY", "custom": "OPENAI_API_KEY",
}


def clean_environment():
    allowed = ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TZ", "XDG_RUNTIME_DIR", "WAYLAND_DISPLAY",
               "XDG_SESSION_TYPE", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "TERM")
    result = {key: os.environ[key] for key in allowed if key in os.environ}
    result.update(PATH="/usr/local/bin:/usr/bin:/bin", PYTHONUNBUFFERED="1", HERMES_ENABLE_PROJECT_PLUGINS="false",
                  HERMES_NO_AUTO_INSTALL="1", DO_NOT_TRACK="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    return result


def read_existing_model(home: Path):
    """Read only the selected native inference configuration, never whole profiles."""
    try:
        import yaml
        config = yaml.safe_load((home / "config.yaml").read_text()) or {}
        model = config.get("model", {})
        if not isinstance(model, dict):
            raise ValueError()
        provider = model.get("provider", "auto")
        if provider not in PROVIDER_KEYS:
            raise VoiceError("EXECUTOR_SETUP_REQUIRED", "Select an explicit API-key or local-server model in Hermes setup before enabling Voice tasks.")
        safe = {key: model[key] for key in ("default", "model", "provider", "base_url", "context_length", "max_tokens") if key in model}
        if not safe.get("default", safe.get("model")):
            raise ValueError()
        credential_name = PROVIDER_KEYS[provider]
        credential = model.get("api_key", "")
        # dotenv values are data only; no interpolation, sourcing, or arbitrary shell evaluation.
        env_file = home / ".env"
        if not credential and env_file.is_file():
            for line in env_file.read_text().splitlines():
                key, separator, value = line.strip().removeprefix("export ").partition("=")
                if separator and key.strip() == credential_name:
                    credential = value.strip().strip("\"'")
        return safe, {credential_name: credential} if credential else {}
    except VoiceError:
        raise
    except (ImportError, OSError, ValueError, TypeError):
        raise VoiceError("EXECUTOR_SETUP_REQUIRED", "Configure a Hermes execution model in Hub before handing off tasks.") from None


def process_identity(pid):
    try:
        data = Path(f"/proc/{int(pid)}/stat").read_text()
        # comm may contain spaces and parentheses; starttime is field22 after final ')'.
        return data.rsplit(")", 1)[1].split()[19]
    except (OSError, ValueError, IndexError):
        return None


def hermes_configuration(model, api_token, port, project):
    auxiliary = {kind: {"provider": "main", "model": model.get("default", model.get("model", ""))}
                 for kind in ("compression", "title_generation", "vision", "web_extract", "curator")}
    return {
        "model": model, "platforms": {"api_server": {"enabled": True, "extra": {"host": "127.0.0.1", "port": port}}},
        "platform_toolsets": {"api_server": ["terminal", "file", "maslow_voice"]},
        "agent": {"max_turns": 60}, "terminal": {"backend": "local", "cwd": project},
        "fallback_model": None, "fallback_models": [], "auxiliary": auxiliary,
        "memory": {"enabled": False}, "compression": {"enabled": False},
        "skills": {"creation_nudge_interval": 0, "external_dirs": []},
        "plugins": {"enabled": ["maslow-voice"], "entries": {"maslow-voice": {"enabled": True}}},
        "telemetry": {"enabled": False}, "display": {"show_reasoning": False},
    }


class HermesRuntime:
    def __init__(self, directory, settings, credentials, tool_socket, tool_token):
        self.directory = private_directory(Path(directory) / "coordinators")
        self.settings, self.credentials = settings, credentials
        self.tool_socket, self.tool_token = str(tool_socket), tool_token
        self.clients, self.processes = {}, {}
        self.lock = asyncio.Lock()

    async def model_config(self, mode):
        config = self.settings.value
        if mode in {"offline", "server"}:
            model = config["execution_model"] or config["model"]
            if not model:
                raise VoiceError("MODEL_REQUIRED", "Choose a downloaded execution model before handing off work.")
            endpoint = "http://127.0.0.1:11434" if mode == "offline" else config["server_url"]
            if not endpoint.endswith("/v1"):
                endpoint += "/v1"
            token = "local-only" if mode == "offline" else await self.credentials.get("server_token")
            return {"default": model, "provider": "custom", "base_url": endpoint}, {"OPENAI_API_KEY": token or "local-server", "OPENAI_BASE_URL": endpoint}
        original = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
        return read_existing_model(original)

    async def ensure(self, task):
        async with self.lock:
            model, provider_env = await self.model_config(task["mode"])
            key = hashlib.sha256(json.dumps([task["mode"], task["project"], model], sort_keys=True).encode()).hexdigest()[:24]
            if key in self.clients:
                return self.clients[key]
            profile = private_directory(self.directory / key)
            locator = profile / "voice-runtime.json"
            if locator.is_file():
                try:
                    data = json.loads(locator.read_text())
                    if data["start"] and process_identity(data["pid"]) == data["start"]:
                        client = HermesClient(data["endpoint"], data["token"])
                        await client.capabilities()
                        self.clients[key] = client
                        return client
                except (OSError, ValueError, KeyError, VoiceError):
                    pass
            binary = shutil.which("hermes")
            if not binary:
                raise VoiceError("HERMES_MISSING", "Install Hermes through Hub to enable task execution.")
            with socket.socket() as candidate:
                candidate.bind(("127.0.0.1", 0))
                port = candidate.getsockname()[1]
            token = secrets.token_urlsafe(32)
            configuration = hermes_configuration(model, token, port, task["project"])
            atomic_json(profile / "config.yaml", configuration)  # JSON is a YAML subset.
            plugin = private_directory(profile / "plugins" / "maslow-voice")
            source = Path(__file__).resolve().parent.parent / "hermes_plugin"
            for name in ("plugin.yaml", "__init__.py"):
                shutil.copyfile(source / name, plugin / name)
            private_directory(profile / "skills")
            environment = clean_environment()
            environment.update(provider_env)
            environment.update(HERMES_HOME=str(profile), API_SERVER_HOST="127.0.0.1", API_SERVER_PORT=str(port), API_SERVER_KEY=token,
                               MASLOW_VOICE_TOOL_SOCKET=self.tool_socket, MASLOW_VOICE_TOOL_TOKEN=self.tool_token,
                               MASLOW_VOICE_MODE=task["mode"], TERMINAL_CWD=task["project"])
            process = await asyncio.create_subprocess_exec(binary, "gateway", "run", cwd=task["project"], env=environment,
                                                           stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL,
                                                           stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
            endpoint = f"http://127.0.0.1:{port}"
            atomic_json(locator, {"pid": process.pid, "start": process_identity(process.pid), "endpoint": endpoint, "token": token})
            client = HermesClient(endpoint, token)
            self.processes[key] = process
            for _ in range(60):
                if process.returncode is not None:
                    raise VoiceError("HERMES_START_FAILED", "The Hermes coordinator did not start. Check the packaged API dependencies and execution model.")
                try:
                    await client.capabilities()
                    self.clients[key] = client
                    return client
                except VoiceError:
                    await asyncio.sleep(0.5)
            process.terminate()
            await process.wait()
            raise VoiceError("HERMES_START_TIMEOUT", "Hermes did not become ready in time. Check its setup and retry.")
