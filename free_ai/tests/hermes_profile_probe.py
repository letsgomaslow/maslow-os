"""Local installed-Hermes compatibility probe; never submits inference."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if sys.argv[1:] not in ([], ["--accounts"]):
    raise SystemExit("Choose the default profile or --accounts profile.")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "voice"))
from maslow_voice.assistant_runtime import configuration


with tempfile.TemporaryDirectory(prefix="maslow-assistant-probe-") as temporary:
    profile = Path(temporary)
    plugin = profile / "plugins/maslow-assistant"
    plugin.mkdir(parents=True)
    for name in ("plugin.yaml", "__init__.py"):
        shutil.copyfile(ROOT / "voice/assistant_plugin" / name, plugin / name)
    (profile / "skills").mkdir()
    (profile / "empty-plugins").mkdir()
    (profile / "config.yaml").write_text(json.dumps(configuration({"model": "openai/gpt-oss-120b", "endpoint": "http://127.0.0.1:18573/v1"}, 18574)))
    env = {"PATH": "/usr/bin:/bin", "HOME": str(profile), "HERMES_HOME": str(profile), "HERMES_ENABLE_PROJECT_PLUGINS": "false",
        "HERMES_BUNDLED_PLUGINS": str(profile / "empty-plugins"), "HERMES_BUNDLED_SKILLS": str(profile / "skills"),
        "HERMES_DISABLE_LAZY_INSTALLS": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "DO_NOT_TRACK": "1",
        "MASLOW_ASSISTANT_ACCOUNTS": "1" if sys.argv[1:] == ["--accounts"] else "0",
        "OPENAI_API_KEY": "local-probe-only", "MASLOW_ASSISTANT_PARENT": str(os.getpid()), "PYTHONDONTWRITEBYTECODE": "1"}
    interpreter = next((str(path) for path in (Path("/opt/hermes-agent/python/bin/python3"), Path("/opt/hermes-agent/venv/bin/python")) if path.is_file()), None)
    if interpreter is None:
        raise SystemExit("Install the reviewed Hermes package before this compatibility probe.")
    result = subprocess.run([interpreter, str(ROOT / "voice/assistant_worker.py"), "--probe"], cwd=profile, env=env,
        text=True, capture_output=True, timeout=90)
    print(result.stdout[-4000:])
    if result.returncode:
        print(result.stderr[-4000:], file=sys.stderr)
        raise SystemExit(result.returncode)
