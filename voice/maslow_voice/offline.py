"""Strict Linux execution boundary for the offline Voice workspace.

The only host IPC exposed to executors is a newly created, dedicated Weston
compositor socket. Model and task traffic crosses a bounded stdio data bridge.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
from pathlib import Path

from .errors import VoiceError

MAX_FRAME = 4 * 1024 * 1024


def fail(code="OFFLINE_UNAVAILABLE", message="The isolated offline workspace could not start. Check Linux isolation support and installed tools."):
    return VoiceError(code, message)


def _directory(path: Path, *, create=False):
    """Open every component without following a symlink, including ancestors."""
    path = Path(os.path.abspath(path))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except OSError:
        os.close(fd)
        raise fail("UNSAFE_OFFLINE_PATH", "Offline folders must be real directories without symbolic links.") from None


def _private(path):
    path = Path(os.path.abspath(path))
    fd = _directory(path, create=True)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            raise fail("UNSAFE_OFFLINE_PATH", "The offline workspace must belong to your account.")
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)
    return path


def _walk(fd, prefix="", destination=None):
    result = {}
    for name in sorted(os.listdir(fd)):
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        relative = prefix + name
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                target = destination / name if destination is not None else None
                if target is not None:
                    target.mkdir(mode=0o700)
                result.update(_walk(child, relative + "/", target))
            finally:
                os.close(child)
        elif stat.S_ISREG(info.st_mode):
            source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                actual = os.fstat(source)
                if not stat.S_ISREG(actual.st_mode) or (info.st_ino, info.st_dev) != (actual.st_ino, actual.st_dev):
                    raise fail("UNSAFE_SNAPSHOT", "A project file changed while preparing its private copy. Retry after saving your work.")
                digest = hashlib.sha256()
                output = (destination / name).open("xb") if destination is not None else None
                try:
                    while chunk := os.read(source, 1024 * 1024):
                        digest.update(chunk)
                        if output is not None:
                            output.write(chunk)
                finally:
                    if output is not None:
                        output.close()
                        (destination / name).chmod(0o700 if info.st_mode & 0o111 else 0o600)
                after = os.fstat(source)
                if (actual.st_mtime_ns, actual.st_size) != (after.st_mtime_ns, after.st_size):
                    raise fail("SNAPSHOT_CHANGED", "The project changed while it was being copied. Save your work and retry.")
                result[relative] = {"sha256": digest.hexdigest(), "executable": bool(info.st_mode & 0o111)}
            finally:
                os.close(source)
        else:
            raise fail("UNSAFE_SNAPSHOT", "The project contains a symbolic link, socket, or special file. Use a project copy containing only regular files and directories.")
    return result


def manifest(path):
    fd = _directory(Path(path))
    try:
        return _walk(fd)
    finally:
        os.close(fd)


def snapshot(source, destination):
    """Copy regular files, never share writable inodes or import host sockets."""
    source, destination = Path(os.path.abspath(source)), Path(os.path.abspath(destination))
    if source == destination or source in destination.parents:
        raise fail("UNSAFE_SNAPSHOT", "The private copy must be outside the source project.")
    fd = _directory(source)
    destination.mkdir(mode=0o700)
    try:
        return _walk(fd, destination=destination)
    except Exception:
        shutil.rmtree(destination)
        raise
    finally:
        os.close(fd)


class OfflineWorkspace:
    """A private project snapshot. Export is separate from executor lifetime."""

    def __init__(self, directory, source=None):
        self.directory = _private(directory)
        self.source = Path(os.path.abspath(source)) if source else None
        self.project = self.directory / "project"
        self.baseline = snapshot(self.source, self.project) if self.source else {}
        if self.source is None:
            self.project.mkdir(mode=0o700)
        self.active = False
        self._save()

    def _save(self):
        fd, temporary = tempfile.mkstemp(prefix=".workspace-", dir=self.directory)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump({"version": 1, "source": str(self.source) if self.source else None, "baseline": self.baseline}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.directory / "workspace.json")
        finally:
            Path(temporary).unlink(missing_ok=True)

    @classmethod
    def restore(cls, directory):
        instance = cls.__new__(cls)
        instance.directory = _private(directory)
        metadata = instance.directory / "workspace.json"
        fd = os.open(metadata, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            with os.fdopen(fd) as stream:
                data = json.load(stream)
            source, baseline = data["source"], data["baseline"]
            if data.get("version") != 1 or (source is not None and (not isinstance(source, str) or not Path(source).is_absolute())) or not isinstance(baseline, dict):
                raise ValueError()
            for name, item in baseline.items():
                if not isinstance(name, str) or name.startswith("/") or any(part in {"", ".", ".."} for part in name.split("/")):
                    raise ValueError()
                if not isinstance(item, dict) or set(item) != {"sha256", "executable"} or type(item["executable"]) is not bool or len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"]):
                    raise ValueError()
            instance.source = Path(source) if source else None
            instance.baseline = baseline
            instance.project = instance.directory / "project"
            instance.active = False
            return instance
        except (OSError, ValueError, TypeError, KeyError):
            raise fail("OFFLINE_RECOVERY_FAILED", "The saved offline workspace metadata could not be verified. Keep its files for manual recovery.") from None

    def review(self):
        if self.active:
            raise fail("OFFLINE_STILL_RUNNING", "Stop the offline workspace before reviewing or exporting files.")
        current = manifest(self.project)
        changes = [{"path": name, "action": "delete" if name not in current else "add" if name not in self.baseline else "modify"}
                   for name in sorted(set(current) | set(self.baseline)) if current.get(name) != self.baseline.get(name)]
        digest = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
        return {"digest": digest, "changes": changes}

    def export(self, reviewed_digest, paths):
        """Export explicitly selected reviewed files, refusing source conflicts.

        This API is host-UI-only; it must never be registered as an agent tool.
        """
        review = self.review()
        if not self.source:
            raise fail("EXPORT_SOURCE_REQUIRED", "This workspace has no original project to export into.")
        if reviewed_digest != review["digest"]:
            raise fail("EXPORT_REVIEW_EXPIRED", "The private files changed after review. Review the changes again.")
        allowed = {item["path"] for item in review["changes"]}
        if not isinstance(paths, list) or not paths or any(not isinstance(p, str) or p not in allowed for p in paths) or len(set(paths)) != len(paths):
            raise fail("INVALID_EXPORT", "Select changed files from the current review.")
        original = manifest(self.source)
        if any(original.get(path) != self.baseline.get(path) for path in paths):
            raise fail("EXPORT_CONFLICT", "The original project changed. Resolve the conflicting files before exporting.")
        current = manifest(self.project)
        root = _directory(self.source)
        try:
            for relative in paths:
                parts = relative.split("/")
                parent = os.dup(root)
                try:
                    for name in parts[:-1]:
                        try:
                            os.mkdir(name, 0o700, dir_fd=parent)
                        except FileExistsError:
                            pass
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                        os.close(parent)
                        parent = child
                    if relative not in current:
                        os.unlink(parts[-1], dir_fd=parent)
                    else:
                        temporary = ".voice-export-" + secrets.token_hex(12)
                        output = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o700 if current[relative]["executable"] else 0o600, dir_fd=parent)
                        try:
                            with os.fdopen(output, "wb") as stream, (self.project / relative).open("rb") as source:
                                shutil.copyfileobj(source, stream)
                                stream.flush()
                                os.fsync(stream.fileno())
                            os.replace(temporary, parts[-1], src_dir_fd=parent, dst_dir_fd=parent)
                        finally:
                            try:
                                os.unlink(temporary, dir_fd=parent)
                            except FileNotFoundError:
                                pass
                    if relative in current:
                        self.baseline[relative] = current[relative]
                    else:
                        self.baseline.pop(relative, None)
                finally:
                    os.close(parent)
        except OSError:
            raise fail("EXPORT_FAILED", "The export could not finish. Review the original and private files before retrying.") from None
        finally:
            os.close(root)
        self._save()
        return {"exported": paths}


def sandbox_command(directory, models, *, display_socket=None, worker=None):
    """Construct a fail-closed empty-root namespace, never bind the host root."""
    directory, models = Path(directory), Path(models)
    command = ["bwrap", "--die-with-parent", "--new-session", "--unshare-all", "--cap-drop", "ALL", "--clearenv"]
    for path in ("/usr", "/bin", "/sbin", "/lib", "/lib64"):
        if Path(path).is_symlink():
            command += ["--symlink", os.readlink(path), path]
        elif Path(path).is_dir():
            command += ["--ro-bind", path, path]
    # Package wrappers reference these exact immutable install trees.
    for path in ("/opt/hermes-agent", "/opt/claude-code", "/opt/google/chrome"):
        if Path(path).is_dir() and not Path(path).is_symlink():
            command += ["--ro-bind", path, path]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/run", "--dir", "/etc", "--dir", "/home",
                "--bind", str(directory / "home"), "/home/voice", "--bind", str(directory / "project"), "/project",
                "--ro-bind", str(models), "/models", "--ro-bind", str(worker or Path(__file__).with_name("offline_worker.py")), "/worker.py"]
    for name in ("passwd", "group", "hosts", "nsswitch.conf"):
        if (directory / "system" / name).is_file():
            command += ["--ro-bind", str(directory / "system" / name), "/etc/" + name]
    for path in ("/etc/fonts", "/etc/ssl/certs", "/etc/ld.so.cache", "/etc/localtime"):
        if Path(path).exists():
            command += ["--ro-bind", path, path]
    command += ["--dir", "/run/voice", "--chmod", "0700", "/run/voice", "--setenv", "HOME", "/home/voice",
                "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin", "--setenv", "XDG_RUNTIME_DIR", "/run/voice",
                "--setenv", "XDG_CONFIG_HOME", "/home/voice/.config", "--setenv", "XDG_CACHE_HOME", "/home/voice/.cache",
                "--setenv", "XDG_DATA_HOME", "/home/voice/.local/share", "--setenv", "LANG", "C.UTF-8",
                "--setenv", "HF_HUB_OFFLINE", "1", "--setenv", "TRANSFORMERS_OFFLINE", "1",
                "--setenv", "OLLAMA_NO_CLOUD", "1", "--setenv", "OLLAMA_NOPRUNE", "1", "--setenv", "OLLAMA_MODELS", "/models",
                "--setenv", "OLLAMA_HOST", "127.0.0.1:11434", "--setenv", "PYTHONUNBUFFERED", "1"]
    if display_socket is not None:
        command += ["--ro-bind", str(display_socket), "/run/voice/wayland-0", "--setenv", "WAYLAND_DISPLAY", "wayland-0"]
    return command + ["--chdir", "/project", "/usr/bin/python3", "/worker.py"]


class OfflineRuntime:
    project_path = "/project"
    model_endpoint = "http://127.0.0.1:11434/v1"

    def __init__(self, directory, settings, *, tool_handler=None):
        self.directory = _private(Path(directory) / "offline")
        self.settings = settings
        self.tool_handler = tool_handler
        self.workspace = None
        self.process = None
        self.display = None
        self.display_socket = None
        self.pending = {}
        self.sequence = 0
        self.reader = None
        self.start_lock = asyncio.Lock()
        self.write_lock = asyncio.Lock()
        self._tool_tasks = set()

    @property
    def config(self):
        return self.settings.value if hasattr(self.settings, "value") else self.settings

    def restore_workspace(self, project):
        """Recover reviewable files without starting a model or display."""
        source = Path(os.path.abspath(project)) if project else None
        if self.workspace and self.workspace.source == source:
            return self.workspace
        if self.process:
            raise fail("OFFLINE_PROJECT_BUSY", "Stop the current offline workspace before selecting another project.")
        for saved in sorted(self.directory.glob("workspace-*/workspace.json"), reverse=True):
            candidate = OfflineWorkspace.restore(saved.parent)
            if candidate.source == source:
                self.workspace = candidate
                return candidate
        return None

    async def open_display(self):
        """A new trusted nested compositor, with no host command launchers."""
        if self.display and self.display.returncode is None:
            return
        if self.process:
            raise fail("OFFLINE_RESTART_REQUIRED", "Stop and reopen the offline workspace to enable its display.")
        root = os.environ.get("XDG_RUNTIME_DIR")
        wayland = os.environ.get("WAYLAND_DISPLAY")
        if sys.platform != "linux" or not root or not wayland or not shutil.which("weston"):
            raise fail("OFFLINE_DISPLAY_UNAVAILABLE", "The offline workspace needs Weston in a Linux Wayland desktop session.")
        parent = Path(wayland) if wayland.startswith("/") else Path(root) / wayland
        info = parent.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise fail("OFFLINE_DISPLAY_UNAVAILABLE", "The desktop display socket could not be verified.")
        display_dir = _private(self.directory / ("display-" + secrets.token_hex(8)))
        runtime = _private(display_dir / "run")
        home = _private(display_dir / "home")
        config = display_dir / "weston.ini"
        config.write_text("[core]\nidle-time=0\nxwayland=false\n[shell]\nlocking=false\n[libinput]\nenable-tap=true\n")
        config.chmod(0o600)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home), "XDG_CONFIG_HOME": str(home),
               "XDG_RUNTIME_DIR": str(runtime), "WAYLAND_DISPLAY": str(parent), "LANG": "C.UTF-8"}
        self.display = await asyncio.create_subprocess_exec("weston", "--backend=wayland-backend.so", "--shell=kiosk-shell.so",
            "--socket=offline-display", "--config=" + str(config), "--width=1280", "--height=800",
            env=env, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        candidate = runtime / "offline-display"
        for _ in range(100):
            if self.display.returncode is not None:
                break
            try:
                info = candidate.lstat()
                if stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid():
                    self.display_socket = candidate
                    return
            except FileNotFoundError:
                pass
            await asyncio.sleep(0.05)
        await self.close_display()
        raise fail("OFFLINE_DISPLAY_UNAVAILABLE", "The isolated desktop window did not start. Check the installed Weston backend.")

    async def close_display(self):
        if self.display and self.display.returncode is None:
            self.display.terminate()
            await self.display.wait()
        self.display = None
        self.display_socket = None

    async def start(self, project=None):
        async with self.start_lock:
            if self.process and self.process.returncode is None:
                if project and self.workspace.source != Path(os.path.abspath(project)):
                    raise fail("OFFLINE_PROJECT_BUSY", "Stop the current offline workspace before selecting another project.")
                return self
            if sys.platform != "linux" or not shutil.which("bwrap"):
                raise fail()
            if self.config.get("server_kind", "ollama") != "ollama":
                raise fail("OFFLINE_OLLAMA_REQUIRED", "Fully offline mode requires dedicated Ollama. Use Server mode for LM Studio.")
            models = self.config.get("ollama_models")
            if not models:
                raise fail("OFFLINE_MODELS_REQUIRED", "Select the existing Ollama model folder before starting offline mode.")
            # Inspect types only: model blobs can be many GB and need not be rehashed.
            await asyncio.to_thread(validate_model_tree, Path(models))
            source = Path(os.path.abspath(project)) if project else None
            if self.workspace is None:
                self.restore_workspace(project)
            if self.workspace is not None and self.workspace.source == source:
                run = self.workspace.directory
            else:
                run = _private(self.directory / ("workspace-" + secrets.token_hex(12)))
                self.workspace = await asyncio.to_thread(OfflineWorkspace, run, project)
            _private(run / "home")
            system = _private(run / "system")
            records = {
                "passwd": f"voice:x:{os.getuid()}:{os.getgid()}:Offline Voice:/home/voice:/bin/bash\n",
                "group": f"voice:x:{os.getgid()}:\n",
                "hosts": "127.0.0.1 localhost\n::1 localhost\n",
                "nsswitch.conf": "passwd: files\ngroup: files\nhosts: files\n",
            }
            for name, content in records.items():
                target = system / name
                if target.is_symlink():
                    raise fail("UNSAFE_OFFLINE_PATH", "The saved offline system files could not be verified.")
                target.write_text(content)
                target.chmod(0o600)
            self.workspace.active = True
            try:
                self.process = await asyncio.create_subprocess_exec(*sandbox_command(run, models, display_socket=self.display_socket),
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin"}, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL, limit=MAX_FRAME + 1, start_new_session=True)
                self.reader = asyncio.create_task(self._read())
                result = await self.request("configure", {"models": [self.config.get("model"), self.config.get("execution_model") or self.config.get("model")]}, timeout=180)
                if not result.get("ready"):
                    raise fail("OFFLINE_MODEL_NOT_READY", "The selected model did not complete inference inside the offline workspace.")
            except BaseException:
                await self.stop()
                raise
            return self

    async def _send(self, message):
        raw = json.dumps(message, ensure_ascii=False).encode() + b"\n"
        if len(raw) > MAX_FRAME:
            raise fail("OFFLINE_MESSAGE_TOO_LARGE", "The offline request exceeds the supported size.")
        async with self.write_lock:
            if not self.process or self.process.returncode is not None:
                raise fail()
            self.process.stdin.write(raw)
            await self.process.stdin.drain()

    async def _read(self):
        try:
            while raw := await self.process.stdout.readline():
                if len(raw) > MAX_FRAME:
                    raise ValueError()
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError()
                if data.get("type") == "tool":
                    if len(self._tool_tasks) >= 32 or not isinstance(data.get("id"), str):
                        raise ValueError()
                    task = asyncio.create_task(self._tool(data))
                    self._tool_tasks.add(task)
                    task.add_done_callback(self._tool_tasks.discard)
                    continue
                if type(data.get("id")) is not int:
                    raise ValueError()
                future = self.pending.pop(data.get("id"), None)
                if future and not future.done():
                    if "error" in data:
                        future.set_exception(fail("OFFLINE_OPERATION_FAILED", "The isolated operation failed. Check local model and tool readiness."))
                    else:
                        future.set_result(data.get("result"))
        except (OSError, ValueError, TypeError, asyncio.LimitOverrunError):
            pass
        finally:
            if self.process and self.process.returncode is None:
                try:
                    self.process.terminate()
                except ProcessLookupError:
                    pass
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(fail())
            self.pending.clear()

    async def _tool(self, data):
        # The handler is trusted policy code. Treat every worker payload as hostile.
        try:
            payload = data.get("payload")
            if not isinstance(payload, dict) or not self.tool_handler:
                raise ValueError()
            result = await self.tool_handler(payload)
            await self._send({"type": "tool_result", "id": data["id"], "result": result})
        except Exception:
            await self._send({"type": "tool_result", "id": data.get("id"), "error": "Offline tool request was rejected."})

    async def request(self, method, params=None, *, timeout=120):
        self.sequence += 1
        identity = self.sequence
        future = asyncio.get_running_loop().create_future()
        self.pending[identity] = future
        try:
            await self._send({"id": identity, "method": method, "params": params or {}})
            return await asyncio.wait_for(future, timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError) as error:
            try:
                await self._send({"type": "cancel", "id": identity})
            except Exception:
                pass
            if isinstance(error, asyncio.CancelledError):
                raise
            raise fail("OFFLINE_OPERATION_TIMEOUT", "The isolated operation timed out. Stop the workspace before retrying unfinished work.") from None
        finally:
            self.pending.pop(identity, None)

    async def model_request(self, path, payload=None):
        return await self.request("model_request", {"path": path, "body": payload}, timeout=180)

    async def spawn(self, argv, *, cwd="/project", env=None, input=None, timeout=120):
        return await self.request("spawn", {"argv": argv, "cwd": cwd, "env": env or {}, "input": input, "timeout": timeout}, timeout=timeout + 5)

    async def create_process(self, argv, *, cwd="/project", env=None):
        result = await self.request("process_start", {"argv": list(argv), "cwd": cwd, "env": env or {}})
        return RemoteProcess(self, result["handle"])

    async def launch_hermes(self, configuration, plugin, environment):
        files = {name: (Path(plugin) / name).read_text() for name in ("__init__.py", "plugin.yaml")}
        return await self.request("hermes_start", {"configuration": configuration, "plugin": files, "environment": environment}, timeout=90)

    async def hermes_request(self, url, method="GET", body=None, token="", headers=None, timeout=60):
        # Matches HermesClient's request injection interface. URL remains worker-local.
        return await self.request("hermes_request", {"url": url, "method": method, "body": body, "token": token, "headers": headers or {}}, timeout=timeout + 5)

    async def open_application(self, application):
        if not self.display_socket:
            raise fail("OFFLINE_DISPLAY_UNAVAILABLE", "Open the offline workspace display before launching an application.")
        return await self.request("open_application", {"application": application})

    async def open_url(self, url):
        if not self.display_socket:
            raise fail("OFFLINE_DISPLAY_UNAVAILABLE", "Open the offline workspace display before launching a browser.")
        return await self.request("open_url", {"url": url})

    async def stop(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.reader:
            await self.reader
        self.process, self.reader = None, None
        for task in self._tool_tasks:
            task.cancel()
        self._tool_tasks.clear()
        if self.workspace:
            self.workspace.active = False
        await self.close_display()


def validate_model_tree(path):
    fd = _directory(path)
    def check(directory):
        for name in os.listdir(directory):
            entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(entry.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                try:
                    check(child)
                finally:
                    os.close(child)
            elif not stat.S_ISREG(entry.st_mode):
                raise fail("UNSAFE_MODEL_FOLDER", "The Ollama model folder contains a symbolic link, socket, or special file.")
    try:
        check(fd)
    finally:
        os.close(fd)


class RemoteProcess:
    """Minimal asyncio process interface backed only by the private worker."""

    def __init__(self, runtime, handle):
        self.runtime, self.handle = runtime, handle
        self.returncode = None
        self.stdin, self.stdout = self, self
        self.buffer = bytearray()
        self.stopping = None

    async def readline(self):
        result = await self.runtime.request("process_readline", {"handle": self.handle}, timeout=3600)
        self.returncode = result.get("returncode")
        return result["line"].encode()

    def write(self, data):
        if len(self.buffer) + len(data) > MAX_FRAME // 2:
            raise fail("OFFLINE_MESSAGE_TOO_LARGE", "The coding request exceeds the supported size.")
        self.buffer.extend(data)

    async def drain(self):
        data = bytes(self.buffer).decode()
        self.buffer.clear()
        await self.runtime.request("process_write", {"handle": self.handle, "data": data})

    def terminate(self):
        if self.stopping is None:
            self.stopping = asyncio.create_task(self.runtime.request("process_stop", {"handle": self.handle}))

    kill = terminate

    async def wait(self):
        result = await self.stopping if self.stopping else await self.runtime.request("process_wait", {"handle": self.handle}, timeout=3600)
        self.returncode = result["returncode"]
        return self.returncode
