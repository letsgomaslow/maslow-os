"""Bounded local session measurements; never audio, transcripts or credentials."""

import json
import math
import os
import time
from pathlib import Path

from .config import private_directory

FIELDS = {"session_id", "provider", "model", "state", "code", "task_id", "selected_agent", "elapsed_ms",
          "input_tokens", "output_tokens", "total_tokens", "input_audio_tokens", "output_audio_tokens", "usage_seconds"}


class SessionAudit:
    def __init__(self, directory):
        self.path = private_directory(Path(directory)) / "voice-audit.jsonl"

    def record(self, event, **fields):
        record = {"event": event, "time": time.time()}
        for key, value in fields.items():
            if key not in FIELDS:
                continue
            if isinstance(value, str):
                record[key] = value[:200]
            elif type(value) in {int, float} and math.isfinite(value):
                record[key] = value
        # Failure to record diagnostics must not hold the microphone open or
        # prevent shutdown. Two private 2 MiB files bound storage use.
        try:
            if self.path.is_symlink():
                return
            if self.path.exists() and self.path.stat().st_size > 2 * 1024 * 1024:
                os.replace(self.path, self.path.with_suffix(".previous.jsonl"))
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "a") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(json.dumps(record) + "\n")
        except OSError:
            pass
