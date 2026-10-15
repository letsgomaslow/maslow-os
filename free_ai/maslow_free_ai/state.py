"""Private settings; this file never contains account or encryption secrets."""

import json
import os
import tempfile
from pathlib import Path

from .errors import FreeAIError


def private_directory(path):
    path = Path(path)
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise FreeAIError("UNSAFE_STATE", "Free cloud AI storage cannot use symbolic links.")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid():
        raise FreeAIError("UNSAFE_STATE", "Free cloud AI storage belongs to another user.")
    path.chmod(0o700)
    return path


def atomic_json(path, value):
    private_directory(path.parent)
    if path.is_symlink():
        raise FreeAIError("UNSAFE_STATE", "Free cloud AI settings cannot use symbolic links.")
    fd, temporary = tempfile.mkstemp(prefix=".free-ai-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class State:
    def __init__(self, directory=None):
        root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        self.directory = private_directory(directory or root / "maslow-free-ai")
        self.path = self.directory / "settings.json"
        self.value = {"schema": 1, "enabled": False, "configured": False, "free_plan": "unconfirmed", "verified_routes": []}
        if self.path.is_symlink():
            raise FreeAIError("UNSAFE_STATE", "Free cloud AI settings cannot use symbolic links.")
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                if set(data) != set(self.value) or data["schema"] != 1 or any(type(data[k]) is not bool for k in ("enabled", "configured")):
                    raise ValueError()
                if data["free_plan"] not in {"unconfirmed", "user-confirmed"} or not isinstance(data["verified_routes"], list):
                    raise ValueError()
                if any(route not in {"openai/gpt-oss-120b", "openai/gpt-oss-20b"} for route in data["verified_routes"]):
                    raise ValueError()
                self.value = data
            except (ValueError, TypeError, OSError):
                raise FreeAIError("STATE_UNREADABLE", "Free cloud AI settings need recovery. They were left unchanged.") from None

    def update(self, **changes):
        value = {**self.value, **changes}
        atomic_json(self.path, value)
        self.value = value
