"""Live package-preparation requires the isolated fixed Voice entry."""
from pathlib import Path
import sys

from .errors import VoiceError


def canonical_startup():
    root = Path("/usr/lib/maslow-voice")
    if (not sys.flags.isolated or not sys.flags.no_site or not sys.flags.dont_write_bytecode
            or sys.pycache_prefix != "/dev/null" or sys.executable != str(root / "venv/bin/python")
            or Path(__file__) != root / "maslow_voice/startup.py"
            or sys.argv[0] != str(root / "maslow_voice/daemon.py")):
        raise VoiceError("FREE_AI_CANONICAL_STARTUP_REQUIRED", "Package preparation needs the fixed isolated Voice service. Review or stop the older service before continuing.")
