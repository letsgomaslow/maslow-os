"""Bounded local desktop actions, independent of coding tasks and their cwd."""

import asyncio
import configparser
import json
import os
import re
import shutil
import time
from pathlib import Path

from . import agent_terminal
from .errors import VoiceError
from .execution import validate_url


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
    APPLICATIONS = {"browser", "files", "hub", "terminal", "codex", "claude"}

    def __init__(self, run=command, *, timeout=8, agent_cwd=None):
        self.run = run
        self.timeout = timeout
        self.agent_cwd = Path(agent_cwd) if agent_cwd else Path.home() / "Projects" / "Maslow Voice"
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

    async def open(self, application, url=None, *, title=None, view=False):
        # Web task seats are opened only by Voice itself. They run in the
        # background at a fixed size: the browser is what the person watches,
        # and Voice always has a full screen to read. view attaches a window.
        if not isinstance(application, str) or application.casefold() not in self.APPLICATIONS | set(agent_terminal.WEB_SEATS):
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Voice can open Browser, Files, Hub, Terminal, Codex, or Claude Code.")
        application = application.casefold()
        if url is not None:
            if application != "browser":
                raise VoiceError("INVALID_REQUEST", "Only the browser can open a website address.")
            url = validate_url(url)
        if agent_terminal.program(application) == "codex" and not shutil.which("codex"):
            raise VoiceError("CODEX_MISSING", "Codex is not installed. Open Hub setup to install or repair it.")
        if application == "claude" and not shutil.which("claude"):
            raise VoiceError("CLAUDE_MISSING", "Claude Code is not installed. Open Hub setup to install or repair it.")
        if application in agent_terminal.SEATS and not shutil.which("tmux"):
            raise VoiceError("APPLICATION_UNAVAILABLE", "Voice needs tmux to keep coding agents visible. Install tmux and try again.")
        if application in agent_terminal.WEB_SEATS and not view:
            async with self.lock:
                if not await agent_terminal.exists(self.run, application):
                    # Start through uwsm-app so the tmux server gets its own desktop
                    # scope. Started directly, it would belong to the Voice
                    # service and be stopped with it on every update.
                    await self.run("setsid", "-f", "uwsm-app", "--", *agent_terminal.detached_argv(application, self.agent_folder()))
                    deadline = time.monotonic() + self.timeout
                    while not await agent_terminal.exists(self.run, application):
                        if time.monotonic() >= deadline:
                            raise VoiceError("AGENT_NOT_READY", "The web task could not start. Try again in a moment.")
                        await asyncio.sleep(0.1)
                    await self.run(*agent_terminal.tmux("set-option", "-w", "-t", agent_terminal.target(application), "window-size", "manual"))
            return {"application": application, "status": "started", "verification": "session_started"}
        async with self.lock:
            # Hub is a Quickshell surface, not a Hyprland client. Successful IPC
            # means its summon was accepted; do not invent window-ready evidence.
            if application == "hub":
                await self.run("omarchy-launch-hub", "setup")
                return {"application": application, "status": "requested", "verification": "shell_acknowledged"}
            matching = await self.matcher(application)
            clients = await self.clients()
            cached = self.windows.get(application)
            found = next((c for c in clients if c.get("address") == cached and matching(c)), None)
            found = found or next((c for c in clients if matching(c)), None)
            # A website always goes through the launcher, which reuses and
            # focuses a running browser itself. An agent window whose session
            # has ended is only closing; start a fresh one instead.
            if found and application in agent_terminal.SEATS and not await agent_terminal.exists(self.run, application):
                found = None
            if found and url is None:
                await self.focus(found)
                self.windows[application] = found["address"]
                return {"application": application, "status": "focused", "verification": "window_observed"}
            if application == "terminal" or application in agent_terminal.SEATS:
                title = "Maslow " + (title or agent_terminal.NAMES.get(application, application.title()))
                argv = ["uwsm-app", "--", "xdg-terminal-exec", f"--app-id=maslow.voice.{application}", "--title=" + title]
                if application in agent_terminal.SEATS:
                    # Attach to the running agent, or start it here so it
                    # inherits this desktop session's environment.
                    argv += ["--", *agent_terminal.attach_argv(application, self.agent_folder())]
                # Terminal processes remain attached. Detach through setsid -f;
                # the observable window, not this helper's exit, is the receipt.
                await self.run("setsid", "-f", *argv)
            elif application == "browser":
                # validate_url guarantees an http(s) scheme, so the address can
                # never be read as a browser option.
                await self.run("setsid", "-f", "omarchy-launch-browser", *([url] if url else []))
            else:
                await self.run("setsid", "-f", "omarchy-launch-nautilus")
            deadline = time.monotonic() + self.timeout
            while True:
                found = next((c for c in await self.clients() if matching(c)), None)
                if found:
                    self.windows[application] = found["address"]
                    await self.focus(found)
                    receipt = {"application": application, "status": "opened", "verification": "window_observed"}
                    return receipt | ({"url": url} if url else {})
                if time.monotonic() >= deadline:
                    raise VoiceError("APPLICATION_NOT_OBSERVED", "The launch was requested, but its window did not appear. Check the desktop before trying again.")
                await asyncio.sleep(0.1)

    async def matcher(self, application):
        classes = await self.browser_classes() if application == "browser" else {
            "files": {"org.gnome.nautilus"}, "terminal": {"maslow.voice.terminal"},
            "codex": {"maslow.voice.codex"}, "claude": {"maslow.voice.claude"},
        }.get(application) or {"maslow.voice." + application}
        def matching(client):
            return bool(client.get("mapped", True)) and any(str(client.get(key, "")).casefold() in classes for key in ("class", "initialClass"))
        return matching

    async def close(self, application):
        """Close one window of an allowlisted application: the one Voice opened, else the most recently used."""
        if not isinstance(application, str) or application.casefold() not in self.APPLICATIONS:
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Voice can close Browser, Files, Terminal, Codex, or Claude Code.")
        application = application.casefold()
        if application == "hub":
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Close Hub from its own window.")
        async with self.lock:
            matching = await self.matcher(application)
            clients = [c for c in await self.clients() if matching(c)]
            cached = self.windows.get(application)
            found = next((c for c in clients if c.get("address") == cached), None)
            found = found or min(clients, key=lambda c: c.get("focusHistoryID", 1 << 30), default=None)
            if not found:
                return {"application": application, "status": "not_open"}
            address = found.get("address", "")
            if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
                raise VoiceError("DESKTOP_UNAVAILABLE", "The application window identity is invalid.")
            try:
                await self.run("hyprctl", "dispatch", 'hl.dsp.window.close({ window = "address:' + address + '" })')
            except VoiceError:
                await self.run("hyprctl", "dispatch", "closewindow", "address:" + address)
            self.windows.pop(application, None)
            receipt = {"application": application, "status": "closed", "verification": "close_requested"}
            if application in agent_terminal.SEATS:
                # Only the viewer detaches; the tmux session keeps the agent running.
                name = agent_terminal.NAMES[application]
                receipt["note"] = f"{name} keeps running. Opening {name} again brings the same session back."
            return receipt

    def agent_folder(self):
        # The same managed root as Voice projects, with the same refusal of
        # redirected folders.
        if any(parent.is_symlink() for parent in (self.agent_cwd, *self.agent_cwd.parents)):
            raise VoiceError("UNSAFE_PROJECT", "The managed Voice project folder cannot use symbolic links.")
        self.agent_cwd.mkdir(parents=True, exist_ok=True)
        return self.agent_cwd

    async def tell(self, agent, text="", reply="", *, title=None, busy_ok=True):
        """Type the person's words into the visible agent, or answer its waiting prompt."""
        if agent not in agent_terminal.SEATS:
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Voice can talk to Codex or Claude Code.")
        if reply not in {"", *agent_terminal.KEYS[agent_terminal.program(agent)]}:
            raise VoiceError("INVALID_REQUEST", "Answer with approve or deny.")
        words = "" if reply else agent_terminal.clean(text)
        # Opening first keeps the agent on screen, reattaching a session whose
        # window was closed, so nothing is typed out of sight.
        await self.open(agent, title=title)
        name = agent_terminal.NAMES[agent]
        if not await agent_terminal.ready(self.run, agent, self.timeout):
            raise VoiceError("AGENT_NOT_READY", f"{name} is not ready in its terminal yet. Check its window and try again.")
        prompt = agent_terminal.pending_prompt(agent, await agent_terminal.screen(self.run, agent))
        if reply:
            if not prompt:
                raise VoiceError("NO_PENDING_PROMPT", f"{name} is not waiting for an answer.")
            if any(marker in prompt for marker in agent_terminal.WINDOW_ONLY[agent_terminal.program(agent)]):
                raise VoiceError("ANSWER_IN_WINDOW", f"{name} would remember this answer permanently. Answer it in the {name} window.")
            await agent_terminal.press(self.run, agent, reply)
            return {"agent": agent, "status": "answered", "reply": reply, "verification": "keys_delivered"}
        if prompt:
            # Never type words into a decision screen; they could pick an option.
            return {"agent": agent, "status": "needs_answer", "prompt": prompt,
                    "message": f"{name} is waiting for a decision. Nothing was typed."}
        if not busy_ok and agent_terminal.BUSY in await agent_terminal.screen(self.run, agent):
            # Words sent to a working agent redirect its current work. Only an
            # explicit correction to that job may do that.
            return {"agent": agent, "status": "busy", "message": f"{name} is still working on something else. Nothing was typed."}
        await agent_terminal.type_line(self.run, agent, words)
        return {"agent": agent, "status": "sent", "verification": "keys_delivered"}

    async def end_seat(self, seat):
        """End a finished web task's session so its seat can take a new job."""
        if seat not in agent_terminal.WEB_SEATS:
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Only web task seats are reused.")
        if await agent_terminal.exists(self.run, seat):
            await self.run(*agent_terminal.tmux("kill-session", "-t", "=" + agent_terminal.session(seat)))
        self.windows.pop(seat, None)

    async def agent_state(self, agent):
        """What the visible agent is doing now, read from its screen."""
        if agent not in agent_terminal.SEATS:
            raise VoiceError("APPLICATION_NOT_ALLOWED", "Voice can check Codex or Claude Code.")
        if not await agent_terminal.exists(self.run, agent):
            return {"agent": agent, "state": "closed"}
        text = await agent_terminal.screen(self.run, agent)
        prompt = agent_terminal.pending_prompt(agent, text)
        if prompt:
            state = "waiting"
        elif agent_terminal.BUSY in text:
            state = "working"
        else:
            state = "idle"
        # The agent's own words sit above its input box; the box and footer
        # below it are interface text, not the answer.
        conversation = agent_terminal.split_input(text)[0]
        tail = "\n".join(line.rstrip() for line in conversation.splitlines()[-30:] if line.strip())[-2000:]
        return {"agent": agent, "state": state, "prompt": prompt, "screen": tail}

    async def focus(self, client):
        address = client.get("address", "")
        if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
            raise VoiceError("DESKTOP_UNAVAILABLE", "The application window identity is invalid.")
        try:
            await self.run("hyprctl", "dispatch", 'hl.dsp.focus({ window = "address:' + address + '" })')
        except VoiceError:
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
