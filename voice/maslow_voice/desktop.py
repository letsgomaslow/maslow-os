"""Bounded local desktop actions, independent of coding tasks and their cwd."""

import asyncio
import configparser
import json
import os
import re
import shutil
import time
from pathlib import Path

from .errors import VoiceError


async def command(*argv):
    try:
        # Detached applications must not inherit a capture pipe that keeps
        # communicate() waiting for the lifetime of their window.
        stdout = asyncio.subprocess.DEVNULL if argv[0] == "setsid" else asyncio.subprocess.PIPE
        process = await asyncio.create_subprocess_exec(*argv, stdout=stdout, stderr=asyncio.subprocess.DEVNULL)
        try:
            output, _ = await asyncio.wait_for(process.communicate(), 5)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise VoiceError("DESKTOP_TIMEOUT", "The desktop did not answer in time.") from None
        if process.returncode:
            raise VoiceError("DESKTOP_FAILED", "The desktop could not complete that action.")
        return (output or b"").decode(errors="replace")
    except FileNotFoundError:
        raise VoiceError("APPLICATION_UNAVAILABLE", "The desktop application or helper is unavailable.") from None


class DesktopActions:
    APPLICATIONS = {"browser", "files", "hub", "terminal", "codex"}

    def __init__(self, run=command, *, timeout=8):
        self.run = run
        self.timeout = timeout
        self.windows = {}
        self.lock = asyncio.Lock()

    async def clients(self):
        try:
            result = json.loads(await self.run("hyprctl", "-j", "clients"))
            if not isinstance(result, list):
                raise ValueError()
            return result
        except (ValueError, TypeError):
            raise VoiceError("DESKTOP_UNAVAILABLE", "The desktop window list is unavailable.") from None

    async def browser_classes(self):
        desktop_id = (await self.run("xdg-settings", "get", "default-web-browser")).strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*\.desktop", desktop_id):
            raise VoiceError("APPLICATION_UNAVAILABLE", "Choose a default browser before opening it with Voice.")
        names = {desktop_id.removesuffix(".desktop").casefold()}
        roots = [Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))]
        roots += [Path(p) for p in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if p]
        for root in roots:
            entry = root / "applications" / desktop_id
            if entry.is_file():
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read(entry)
                value = parser.get("Desktop Entry", "StartupWMClass", fallback="")
                if value:
                    names.add(value.casefold())
                break
        return names

    async def open(self, application):
        if not isinstance(application, str) or application.casefold() not in self.APPLICATIONS:
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Voice can open Browser, Files, Hub, Terminal, or Codex.")
        application = application.casefold()
        if application == "codex" and not shutil.which("codex"):
            raise VoiceError("CODEX_MISSING", "Codex is not installed. Open Hub setup to install or repair it.")
        async with self.lock:
            # Hub is a Quickshell surface, not a Hyprland client. Successful IPC
            # means its summon was accepted; do not invent window-ready evidence.
            if application == "hub":
                await self.run("omarchy-launch-hub", "setup")
                return {"application": application, "status": "requested", "verification": "shell_acknowledged"}
            classes = await self.browser_classes() if application == "browser" else {
                "files": {"org.gnome.nautilus"}, "terminal": {"maslow.voice.terminal"}, "codex": {"maslow.voice.codex"},
            }[application]
            clients = await self.clients()
            def matching(client):
                return bool(client.get("mapped", True)) and any(str(client.get(key, "")).casefold() in classes for key in ("class", "initialClass"))
            cached = self.windows.get(application)
            found = next((c for c in clients if c.get("address") == cached and matching(c)), None)
            found = found or next((c for c in clients if matching(c)), None)
            if found:
                await self.focus(found)
                self.windows[application] = found["address"]
                return {"application": application, "status": "focused", "verification": "window_observed"}
            if application in {"terminal", "codex"}:
                argv = ["uwsm-app", "--", "xdg-terminal-exec", f"--app-id=maslow.voice.{application}", "--title=Maslow " + application.title()]
                if application == "codex":
                    argv += ["--", "codex"]
                # Terminal processes remain attached. Detach through setsid -f;
                # the observable window, not this helper's exit, is the receipt.
                await self.run("setsid", "-f", *argv)
            else:
                await self.run("setsid", "-f", "omarchy-launch-browser" if application == "browser" else "omarchy-launch-nautilus")
            deadline = time.monotonic() + self.timeout
            while True:
                found = next((c for c in await self.clients() if matching(c)), None)
                if found:
                    self.windows[application] = found["address"]
                    await self.focus(found)
                    return {"application": application, "status": "opened", "verification": "window_observed"}
                if time.monotonic() >= deadline:
                    raise VoiceError("APPLICATION_NOT_OBSERVED", "The launch was requested, but its window did not appear. Check the desktop before trying again.")
                await asyncio.sleep(0.1)

    async def focus(self, client):
        address = client.get("address", "")
        if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
            raise VoiceError("DESKTOP_UNAVAILABLE", "The application window identity is invalid.")
        await self.run("hyprctl", "dispatch", "focuswindow", "address:" + address)

    async def open_path(self, task, relative=None):
        if task.get("mode") == "offline":
            raise VoiceError("OFFLINE_ACTION_UNAVAILABLE", "Open offline results through their isolated workspace.")
        root = Path(task["project"]).resolve()
        if relative is None:
            path = root
        else:
            if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
                raise VoiceError("INVALID_ARTIFACT", "Choose a file from this task's results.")
            if not any(a.get("path") == relative for a in task.get("artifacts", [])):
                raise VoiceError("INVALID_ARTIFACT", "That file is not a recorded task artifact.")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise VoiceError("ARTIFACT_UNAVAILABLE", "The result is missing or outside this project's folder.")
        if not path.exists():
            raise VoiceError("PROJECT_REQUIRED", "This project's folder is no longer available.")
        # URI encoding prevents filenames from becoming handler options.
        await self.run("setsid", "-f", "xdg-open", path.as_uri())
        return {"status": "requested", "path": str(path), "verification": "exists"}
