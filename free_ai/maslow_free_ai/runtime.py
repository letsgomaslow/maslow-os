"""Lazy owned router: private stdin bootstrap, one account, task-held lifetime."""

import asyncio
from contextlib import closing
import hashlib
import json
import os
import re
import secrets
import signal
import socket
import sqlite3
import time
from pathlib import Path

from .credentials import EncryptionKey
from .errors import FreeAIError
from .state import State

MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
PACKAGE = Path("/usr/lib/maslow-free-ai")


class RouterRuntime:
    def __init__(self, directory=None, *, keys=None, package=PACKAGE, port=18573, grace=5):
        self.state = State(directory)
        self.keys = keys or EncryptionKey()
        self.package, self.port, self.grace = Path(package), port, grace
        self.process, self.token = None, None
        self.owners = set()
        self.lock = asyncio.Lock()
        self.idle_stop = None
        self.admission = True

    @property
    def database(self):
        return self.state.directory / "router.sqlite3"

    def status(self):
        installed = (self.package / "node/bin/node").is_file() and (self.package / "router/server/dist/maslow-main.js").is_file()
        value = self.state.value
        task_support = self.task_supported()
        ready = installed and task_support and value["configured"] and set(value["verified_routes"]) == set(MODELS) and value["free_plan"] == "user-confirmed"
        state = "working" if self.owners else "disabled" if not value["enabled"] and ready else "ready" if ready else "needs-setup"
        return {"installed": installed, "configured": value["configured"], "ready": ready, "enabled": value["enabled"],
                "state": state, "free_plan": value["free_plan"], "provider": "groq", "task_support": task_support}

    def task_supported(self):
        return Path("/usr/lib/maslow-voice/assistant_worker.py").is_file() and Path("/usr/lib/maslow-voice/assistant_plugin/plugin.yaml").is_file()

    def cooldown_message(self):
        if not self.database.exists():
            return None
        info = self.database.lstat()
        if self.database.is_symlink() or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise FreeAIError("UNSAFE_STATE", "The router database needs recovery.")
        try:
            with closing(sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)) as db:
                row = db.execute("SELECT value FROM settings WHERE key='maslow_groq_cooldown_until'").fetchone()
            until = int(row[0]) / 1000 if row else 0
        except (sqlite3.Error, ValueError):
            raise FreeAIError("STATE_UNREADABLE", "Free cloud AI's saved allowance state needs recovery.") from None
        if until > time.time():
            clock = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(until))
            return "Groq's account allowance is paused until " + clock + ". Use Continue after that time; no other service was used."
        return None

    async def _start(self, groq_key=None):
        if self.process and self.process.returncode is None:
            return {"endpoint": f"http://127.0.0.1:{self.port}/v1", "token": self.token, "model": MODELS[0]}
        if not self.status()["installed"]:
            raise FreeAIError("FREE_AI_NOT_INSTALLED", "Install the reviewed Free cloud AI components through Hub first.")
        key = await self.keys.get()
        if key is None:
            if not groq_key or self.database.exists():
                raise FreeAIError("ENCRYPTION_KEY_MISSING", "The matching encryption key is missing. Recover it before continuing.")
            key = secrets.token_hex(32)
            await self.keys.create(key)
        if self.database.is_symlink():
            raise FreeAIError("UNSAFE_STATE", "The router database cannot use symbolic links.")
        with socket.socket() as candidate:
            try:
                candidate.bind(("127.0.0.1", self.port))
            except OSError:
                raise FreeAIError("FREE_AI_PORT_OCCUPIED", "Free cloud AI's private port is in use. No other process was stopped.") from None
        token = secrets.token_urlsafe(32)
        environment = {key: os.environ[key] for key in ("LANG", "LC_ALL", "TZ") if key in os.environ}
        environment.update(PATH="/usr/bin:/bin", NODE_ENV="production")
        process = await asyncio.create_subprocess_exec("/usr/bin/python", str(self.package / "maslow_free_ai/router_worker.py"),
            str(os.getpid()), cwd=str(self.package / "router"), env=environment,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True, limit=4096)
        self.process, self.token = process, token
        payload = {"encryptionKey": key, "instanceToken": token, "dbPath": str(self.database), "port": self.port}
        if groq_key:
            payload["groqKey"] = groq_key
        try:
            process.stdin.write(json.dumps(payload).encode())
            await process.stdin.drain()
            process.stdin.close()
            line = await asyncio.wait_for(process.stdout.readline(), 45)
            event = json.loads(line)
            if process.returncode is not None or event != {"event": "ready", "host": "127.0.0.1", "port": self.port,
                    "tokenId": hashlib.sha256(token.encode()).hexdigest()}:
                raise ValueError()
        except asyncio.CancelledError:
            await self._stop()
            raise
        except (OSError, ValueError, TimeoutError):
            await self._stop()
            raise FreeAIError("FREE_AI_START_FAILED", "Free cloud AI did not start safely. No fallback was used.") from None
        return {"endpoint": f"http://127.0.0.1:{self.port}/v1", "token": token, "model": MODELS[0]}

    async def _stop(self):
        process = self.process
        if process and process.returncode is None:
            # Never infer ownership from a health response, PID file, or port.
            # This object owns only the process group it directly spawned.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
        self.process, self.token = None, None

    async def acquire(self, owner):
        async with self.lock:
            if not self.admission or not self.state.value["enabled"] or not self.status()["ready"]:
                raise FreeAIError("FREE_AI_SETUP_REQUIRED", "Finish Free cloud AI setup and enable it through Hub first.")
            if self.owners - {owner}:
                raise FreeAIError("ASSISTANT_TASK_ACTIVE", "Finish or stop the active assistant request first.")
            cooldown = self.cooldown_message()
            if cooldown:
                raise FreeAIError("FREE_AI_QUOTA_PAUSED", cooldown)
            if self.idle_stop:
                self.idle_stop.cancel()
                self.idle_stop = None
            route = await self._start()
            self.owners.add(owner)
            return route

    async def release(self, owner):
        async with self.lock:
            self.owners.discard(owner)
            if not self.owners and not self.idle_stop:
                self.idle_stop = asyncio.create_task(self._after_grace())

    async def _after_grace(self):
        try:
            await asyncio.sleep(self.grace)
            async with self.lock:
                if not self.owners:
                    await self._stop()
        finally:
            if self.idle_stop is asyncio.current_task():
                self.idle_stop = None

    async def setup(self, key, confirmed, probe):
        if not isinstance(key, str) or not re.fullmatch(r"gsk_[A-Za-z0-9_-]{16,256}", key) or confirmed is not True:
            raise FreeAIError("FREE_PLAN_CONFIRMATION_REQUIRED", "Confirm your Groq account is on Free and enter its key in private setup.")
        async with self.lock:
            if self.owners:
                raise FreeAIError("TASKS_ACTIVE", "Finish or stop assistant tasks before changing the provider key.")
            await self._stop()
            self.state.update(configured=False, verified_routes=[], enabled=False, free_plan="unconfirmed")
            route = await self._start(key)
            try:
                self.state.update(configured=True, free_plan="user-confirmed")
                verified = await probe(route)
                self.state.update(verified_routes=verified)
            finally:
                await self._stop()
        return self.status()

    async def test(self, probe):
        async with self.lock:
            if self.owners:
                raise FreeAIError("TASKS_ACTIVE", "Finish or stop assistant tasks before testing setup.")
            self.state.update(verified_routes=[])
            route = await self._start()
            try:
                self.state.update(verified_routes=await probe(route))
            finally:
                await self._stop()
        return self.status()

    async def enable(self, enabled):
        async with self.lock:
            if enabled and not self.status()["ready"]:
                raise FreeAIError("FREE_AI_SETUP_REQUIRED", "Connect and check your Free cloud AI account first.")
            self.state.update(enabled=enabled)
        return self.status()

    async def close(self):
        if self.idle_stop:
            self.idle_stop.cancel()
            await asyncio.gather(self.idle_stop, return_exceptions=True)
        async with self.lock:
            self.admission = False
            await self._stop()
