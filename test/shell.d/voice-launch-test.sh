#!/bin/bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/base-test.sh"
require_command python3
require_command jq

python3 - <<'PY'
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

root = Path(os.environ["ROOT"])
with tempfile.TemporaryDirectory(prefix="voice-launch-test-") as temporary:
    fixture = Path(temporary)
    commands = fixture / "bin"
    commands.mkdir()
    runtime = fixture / "runtime"
    runtime.mkdir()
    state_file = fixture / "state.json"
    mock = commands / "mock"
    mock.write_text('''#!/usr/bin/env python3
import fcntl, json, os, sys, time
from pathlib import Path
name = Path(sys.argv[0]).name
if name == "flock":
    try:
        fcntl.flock(int(sys.argv[-1]), fcntl.LOCK_EX | (fcntl.LOCK_NB if "-n" in sys.argv else 0))
    except BlockingIOError:
        sys.exit(1)
    sys.exit(0)
p = Path(os.environ["VOICE_TEST_STATE"])
s = json.loads(p.read_text())
s.setdefault("calls", []).append([name, *sys.argv[1:]])
def save(): p.write_text(json.dumps(s))
def done(output="", code=0):
    save()
    if output: print(output)
    sys.exit(code)
if name == "omarchy-cmd-missing": done(code=0 if s.get("not_installed") else 1)
if name == "omarchy-hyprland-session-locked":
    checks = s.get("compositor", [1])
    code = checks.pop(0) if len(checks) > 1 else checks[0]
    done(code=code)
if name == "omarchy-shell":
    action = sys.argv[1:3]
    if action == ["lock", "status"]:
        exits = s.get("lock_exits", [s.get("lock_exit", 0)])
        code = exits.pop(0) if len(exits) > 1 else exits[0]
        done(s.get("lock", json.dumps(dict(locked=False, requested=False, pending=False, sessionLocked=False, secure=False))), code)
    if action == ["shell", "listPlugins"]:
        if "registry" in s: done(s["registry"])
        scans = s.get("scans", 0)
        failures = s.get("post_scan_registry_failures", 0)
        if scans and failures:
            s["post_scan_registry_failures"] -= 1
            done(code=1)
        if scans and s.get("post_scan_registry_unavailable"):
            done(code=1)
        pending = s.get("pending", 0)
        if scans and pending:
            s["pending"] -= 1
        enabled = s.get("present", True) or (scans and not pending)
        done(json.dumps([dict(id="maslow.voice", enabled=not s.get("disabled"))] if enabled else []))
    if action == ["shell", "rescanPlugins"]:
        s["scans"] = s.get("scans", 0) + 1
        save()
        if s.get("block_scan"):
            Path(os.environ["VOICE_TEST_STARTED"]).touch()
            deadline = time.monotonic() + 5
            while not Path(os.environ["VOICE_TEST_RELEASE"]).exists():
                if time.monotonic() > deadline: sys.exit(1)
                time.sleep(.01)
        sys.exit(0)
    if action == ["shell", "summon"]: done(s.get("summon", "ok"))
done()
''')
    mock.chmod(0o755)
    for name in ("flock", "omarchy-cmd-missing", "omarchy-hyprland-session-locked", "omarchy-shell", "omarchy-launch-hub", "omarchy-pkg-add", "systemctl"):
        (commands / name).symlink_to(mock)
    (commands / "omarchy-launch-voice").symlink_to(root / "bin/omarchy-launch-voice")
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}",
               XDG_RUNTIME_DIR=str(runtime), VOICE_TEST_STATE=str(state_file),
               VOICE_TEST_STARTED=str(fixture / "started"), VOICE_TEST_RELEASE=str(fixture / "release"))

    marker = runtime / "maslow-voice-refresh-pending"

    def run(state, command="launch", page="settings", pending=False, graphical=True, extra_env=None):
        if pending:
            marker.touch(mode=0o600)
        else:
            marker.unlink(missing_ok=True)
        state_file.write_text(json.dumps(state))
        call_env = env if graphical else dict(env, XDG_RUNTIME_DIR="")
        if extra_env:
            call_env = dict(call_env, **extra_env)
        result = subprocess.run(["bash", str(root / f"bin/omarchy-{command}-voice"), page], env=call_env, text=True, capture_output=True, timeout=8)
        assert result.returncode == 0, result.stderr
        return json.loads(state_file.read_text()), result.stdout

    def actions(state, action):
        return [call for call in state["calls"] if call[:3] == ["omarchy-shell", "shell", action]]

    def no_mutation(state):
        assert not actions(state, "rescanPlugins"), state
        assert not actions(state, "summon"), state

    for scenario in ({"compositor": [0]}, {"compositor": [2]}, {"lock": "invalid"},
                     {"lock": "{}"}, {"lock_exit": 1},
                     {"lock": json.dumps(dict(locked=False, requested=True, pending=True, sessionLocked=False, secure=False))}):
        state, output = run(scenario)
        no_mutation(state)
        assert "open Voice again" in output
    print("ok - locked, pending and unknown lock state defer without shell mutations")

    state, _ = run({"not_installed": True})
    no_mutation(state)
    assert ["omarchy-launch-hub", "voice"] in state["calls"]
    print("ok - missing Voice keeps the Hub installation route")

    state, _ = run({})
    assert not actions(state, "rescanPlugins")
    assert actions(state, "summon") == [["omarchy-shell", "shell", "summon", "maslow.voice", '{"page":"settings"}']]
    print("ok - registered Voice opens the requested page without refreshing plugins")

    state, _ = run({"present": False, "pending": 2})
    assert len(actions(state, "rescanPlugins")) == 1
    assert len(actions(state, "listPlugins")) == 4
    assert len(actions(state, "summon")) == 1
    state["calls"] = []
    state, _ = run(state, page="tasks")
    assert not actions(state, "rescanPlugins")
    assert len(actions(state, "summon")) == 1
    print("ok - new plugin discovery scans once, awaits registration and avoids repeat refresh")

    state, _ = run({"present": False, "post_scan_registry_failures": 2}, pending=True)
    assert len(actions(state, "rescanPlugins")) == 1
    assert len(actions(state, "listPlugins")) == 4
    assert len(actions(state, "summon")) == 1
    assert not marker.exists()
    print("ok - transient post-rescan registry failures retry before opening once")

    state, _ = run({"present": False, "post_scan_registry_failures": 1, "compositor": [1, 1, 1, 0]}, pending=True)
    assert len(actions(state, "rescanPlugins")) == 1
    assert not actions(state, "summon")
    assert marker.exists()
    print("ok - a lock transition after transient registry recovery prevents opening")

    bash_environment = fixture / "fast-retry.bash"
    bash_environment.write_text("sleep() { SECONDS=$((SECONDS + 1)); }\n")
    state, output = run({"present": False, "post_scan_registry_unavailable": True}, pending=True,
                        extra_env={"BASH_ENV": str(bash_environment)})
    assert len(actions(state, "rescanPlugins")) == 1
    assert not actions(state, "summon")
    assert marker.exists()
    assert "open Voice again" in output
    print("ok - permanently unavailable post-rescan registry never opens Voice")

    state, _ = run({"present": False, "compositor": [1, 0]})
    no_mutation(state)
    state, _ = run({"present": False, "compositor": [1, 1, 1, 0]})
    assert len(actions(state, "rescanPlugins")) == 1
    assert not actions(state, "summon")
    print("ok - lock transitions before refresh or summon defer the next mutation")

    for scenario in ({"disabled": True}, {"registry": "{}"}):
        state, output = run(scenario)
        no_mutation(state)
    state, output = run({"summon": "unknown"})
    assert "open Voice again" in output
    assert not actions(state, "rescanPlugins")
    print("ok - disabled or invalid registry is preserved and unknown summon is reported")

    state, output = run({"compositor": [0]}, command="install", page="local")
    no_mutation(state)
    assert ["omarchy-pkg-add", "maslow-voice", "maslow-voice-local"] in state["calls"]
    assert ["systemctl", "--user", "enable", "--now", "maslow-voice.service"] in state["calls"]
    assert "installed" in output
    assert marker.exists() and marker.stat().st_mode & 0o777 == 0o600
    print("ok - install succeeds and enables Voice while deferring locked desktop refresh")

    state, _ = run({}, pending=True)
    assert len(actions(state, "rescanPlugins")) == 1
    assert len(actions(state, "summon")) == 1
    assert not marker.exists()
    state, _ = run({})
    assert not actions(state, "rescanPlugins")
    print("ok - deferred upgrade refreshes an existing panel once after unlock")

    state, _ = run({}, command="install", page="local")
    assert len(actions(state, "rescanPlugins")) == 1
    assert len(actions(state, "summon")) == 1
    assert not marker.exists()
    print("ok - unlocked install refreshes an already registered old Voice panel")

    state, _ = run({"lock_exits": [0, 0, 1, 0, 0]}, pending=True)
    assert len(actions(state, "rescanPlugins")) == 1
    assert len(actions(state, "listPlugins")) == 3
    assert not marker.exists()
    print("ok - upgrade waits for rebuilt services before accepting the existing registry")

    for _ in range(2):
        state, _ = run({"disabled": True}, pending=True)
        no_mutation(state)
        assert marker.exists()
    state, _ = run({"lock_exit": 1}, pending=True)
    no_mutation(state)
    assert marker.exists()
    state, _ = run({"summon": "unknown"}, pending=True)
    assert marker.exists()
    print("ok - disabled or uncertain upgrade keeps its refresh marker without repeated scans")

    state, output = run({}, command="install", page="local", graphical=False)
    no_mutation(state)
    assert "new desktop session" in output
    print("ok - nongraphical install completes with an honest new-session instruction")

    state_file.write_text(json.dumps(dict(present=False, block_scan=True)))
    first = subprocess.Popen(["bash", str(root / "bin/omarchy-launch-voice")], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 5
        while not (fixture / "started").exists():
            assert time.monotonic() < deadline, "first opener did not reach scan"
            time.sleep(.01)
        second = subprocess.run(["bash", str(root / "bin/omarchy-launch-voice")], env=env, text=True, capture_output=True, timeout=3)
        assert second.returncode == 0 and "already opening" in second.stdout, second
    finally:
        (fixture / "release").touch()
        output, error = first.communicate(timeout=5)
    assert first.returncode == 0, error
    state = json.loads(state_file.read_text())
    assert len(actions(state, "rescanPlugins")) == 1
    assert len(actions(state, "summon")) == 1
    print("ok - simultaneous openers cannot trigger duplicate plugin refresh")

    (fixture / "started").unlink()
    (fixture / "release").unlink()
    state_file.write_text(json.dumps(dict(present=False, block_scan=True)))
    first = subprocess.Popen(["bash", str(root / "bin/omarchy-launch-voice")], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    installer = None
    try:
        deadline = time.monotonic() + 5
        while not (fixture / "started").exists():
            assert time.monotonic() < deadline
            time.sleep(.01)
        installer = subprocess.Popen(["bash", str(root / "bin/omarchy-install-voice")], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 5
        while not any(call[:3] == ["systemctl", "--user", "enable"] for call in json.loads(state_file.read_text())["calls"]):
            assert time.monotonic() < deadline
            time.sleep(.01)
        time.sleep(.1)
        assert not marker.exists(), "installer wrote a marker outside the opener lock"
    finally:
        (fixture / "release").touch()
        output, error = first.communicate(timeout=5)
        if installer:
            install_output, install_error = installer.communicate(timeout=5)
    assert first.returncode == 0, error
    assert installer.returncode == 0, install_error
    state = json.loads(state_file.read_text())
    assert len(actions(state, "rescanPlugins")) == 2
    assert len(actions(state, "summon")) == 2
    assert not marker.exists()
    print("ok - concurrent install cannot lose its refresh marker to an earlier opener")
PY
