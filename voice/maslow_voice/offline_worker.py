"""Private bwrap child. Deliberately standalone and standard-library only."""

import asyncio
import json
import os
import re
import secrets
import shutil
import signal
import sys
import time
from pathlib import Path
from urllib import request
from urllib.parse import urlsplit

MAX_FRAME = 4 * 1024 * 1024
CHILDREN = []
PROCESSES = {}
TOOLS = {}
HERMES = {}
TOOL_SERVER = None
READY = False
HERMES_START_TIMEOUT = 120
HERMES_START_POLL_INTERVAL = 0.5


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect rejected")


def json_request(url, method="GET", body=None, token="", headers=None):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("invalid private endpoint")
    data = json.dumps(body).encode() if body is not None else None
    safe_headers = {"Content-Type": "application/json"}
    if token:
        safe_headers["Authorization"] = "Bearer " + token
    for key, value in (headers or {}).items():
        if key.lower() == "idempotency-key":
            safe_headers[key] = value
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    with opener.open(request.Request(url, data=data, method=method, headers=safe_headers), timeout=150) as response:
        raw = response.read(MAX_FRAME + 1)
        if len(raw) > MAX_FRAME:
            raise ValueError("response too large")
        return json.loads(raw)


def emit(message):
    raw = json.dumps(message, ensure_ascii=False)
    if len(raw.encode()) > MAX_FRAME:
        raise ValueError("frame too large")
    sys.stdout.write(raw + "\n")
    sys.stdout.flush()


async def tool_client(reader, writer):
    identity = secrets.token_hex(16)
    try:
        raw = await asyncio.wait_for(reader.readline(), 10)
        if len(raw) > 262144:
            raise ValueError()
        payload = json.loads(raw)
        future = asyncio.get_running_loop().create_future()
        TOOLS[identity] = future
        emit({"type": "tool", "id": identity, "payload": payload})
        result = await asyncio.wait_for(future, 300)
        writer.write(json.dumps(result).encode() + b"\n")
        await writer.drain()
    except Exception:
        writer.write(b'{"error":{"code":"OFFLINE_TOOL_REJECTED","message":"The offline tool request could not complete."}}\n')
        await writer.drain()
    finally:
        TOOLS.pop(identity, None)
        writer.close()
        await writer.wait_closed()


async def launch(argv, *, env=None, cwd="/project", **kwargs):
    process = await asyncio.create_subprocess_exec(*argv, env=env or dict(os.environ), cwd=cwd,
        start_new_session=True, **kwargs)
    CHILDREN.append(process)
    return process


async def terminate(process):
    if process.returncode is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


async def _wait_for_hermes(process, probe, *, timeout=HERMES_START_TIMEOUT,
                           poll_interval=HERMES_START_POLL_INTERVAL, clock=None, sleep=None):
    loop = asyncio.get_running_loop()
    clock = clock or loop.time
    sleep = sleep or asyncio.sleep
    deadline = clock() + timeout
    while True:
        if process.returncode is not None:
            raise ValueError("hermes start failed")
        remaining = deadline - clock()
        if remaining <= 0:
            raise ValueError("hermes timeout")
        try:
            await asyncio.wait_for(probe(), remaining)
            return
        except TimeoutError:
            if clock() >= deadline:
                raise ValueError("hermes timeout") from None
        except Exception:
            pass
        remaining = deadline - clock()
        if remaining <= 0:
            raise ValueError("hermes timeout")
        await sleep(min(poll_interval, remaining))


async def configure(params):
    global READY, TOOL_SERVER
    if READY:
        return {"ready": True}
    models = params.get("models")
    if not isinstance(models, list) or not models or any(not isinstance(m, str) or not m or len(m) > 512 for m in models):
        raise ValueError("model required")
    # A dedicated server starts in the already isolated namespace. No host port
    # or model-manager proxy is reachable, including cloud-backed Ollama entries.
    process = await launch(["ollama", "serve"], stdin=asyncio.subprocess.DEVNULL,
                           stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    for _ in range(100):
        if process.returncode is not None:
            raise ValueError("ollama unavailable")
        try:
            tags = await asyncio.to_thread(json_request, "http://127.0.0.1:11434/api/tags")
            break
        except Exception:
            await asyncio.sleep(0.1)
    else:
        raise ValueError("ollama timeout")
    available = {item.get("name") for item in tags.get("models", [])}
    for model in set(models):
        if model not in available and model + ":latest" not in available:
            raise ValueError("model not downloaded")
        details = await asyncio.to_thread(json_request, "http://127.0.0.1:11434/api/show", "POST", {"model": model})
        if details.get("remote_host") or details.get("remote_model") or not details.get("model_info"):
            raise ValueError("model not local")
        probe = await asyncio.to_thread(json_request, "http://127.0.0.1:11434/api/generate", "POST",
            {"model": model, "prompt": "Reply with READY.", "stream": False, "options": {"num_predict": 16, "temperature": 0}})
        if not probe.get("done") or not isinstance(probe.get("response"), str) or not probe["response"].strip() or probe.get("eval_count", 0) < 1:
            raise ValueError("model inference failed")
    TOOL_SERVER = await asyncio.start_unix_server(tool_client, "/run/voice/tools.sock", limit=262145)
    os.chmod("/run/voice/tools.sock", 0o600)
    READY = True
    return {"ready": True, "models": models, "network": "private-namespace"}


async def spawn(params):
    argv = params.get("argv")
    if not isinstance(argv, list) or not argv or len(argv) > 256 or any(not isinstance(a, str) or "\0" in a for a in argv):
        raise ValueError("invalid command")
    cwd = params.get("cwd", "/project")
    if not isinstance(cwd, str) or not (cwd == "/project" or cwd.startswith("/project/")) or ".." in Path(cwd).parts:
        raise ValueError("invalid working directory")
    extra = params.get("env", {})
    if not isinstance(extra, dict) or any(not isinstance(k, str) or not isinstance(v, str) or "\0" in k + v for k, v in extra.items()):
        raise ValueError("invalid environment")
    forbidden = {"HOME", "PATH", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "LD_PRELOAD", "PYTHONPATH"}
    if set(extra) & forbidden:
        raise ValueError("reserved environment")
    env = dict(os.environ, **extra)
    timeout = params.get("timeout", 120)
    if not isinstance(timeout, (float, int)) or not 0 < timeout <= 3600:
        raise ValueError("invalid timeout")
    text = params.get("input")
    if text is not None and not isinstance(text, str):
        raise ValueError("invalid input")
    process = await launch(argv, env=env, cwd=cwd, stdin=asyncio.subprocess.PIPE,
                           stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    async def bounded(stream):
        result = bytearray()
        while chunk := await stream.read(65536):
            result.extend(chunk)
            if len(result) > MAX_FRAME // 3:
                raise ValueError("output too large")
        return bytes(result).decode("utf-8", errors="replace")
    async def write_input():
        if text:
            process.stdin.write(text.encode())
            await process.stdin.drain()
        process.stdin.close()
    try:
        output, errors, _ = await asyncio.wait_for(asyncio.gather(bounded(process.stdout), bounded(process.stderr), write_input()), timeout)
        await process.wait()
        return {"returncode": process.returncode, "stdout": output, "stderr": errors}
    finally:
        await terminate(process)


async def process_rpc(method, params):
    """Stream only children owned by this namespace; handles are not host PIDs."""
    if method == "process_start":
        argv, cwd, extra = params.get("argv"), params.get("cwd", "/project"), params.get("env", {})
        if not isinstance(argv, list) or not argv or len(argv) > 256 or any(not isinstance(a, str) or "\0" in a for a in argv):
            raise ValueError("invalid command")
        if not isinstance(cwd, str) or not (cwd == "/project" or cwd.startswith("/project/")) or ".." in Path(cwd).parts:
            raise ValueError("invalid working directory")
        if not isinstance(extra, dict) or any(not isinstance(k, str) or not isinstance(v, str) or "\0" in k + v for k, v in extra.items()):
            raise ValueError("invalid environment")
        forbidden = {"HOME", "PATH", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "LD_PRELOAD", "PYTHONPATH"}
        if set(extra) & forbidden or len(PROCESSES) >= 16:
            raise ValueError("reserved environment or process limit")
        process = await launch(argv, cwd=cwd, env=dict(os.environ, **extra), stdin=asyncio.subprocess.PIPE,
                               stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=MAX_FRAME // 2)
        handle = secrets.token_hex(24)
        PROCESSES[handle] = process
        return {"handle": handle}
    handle = params.get("handle")
    if not isinstance(handle, str) or handle not in PROCESSES:
        raise ValueError("unknown process")
    process = PROCESSES[handle]
    if method == "process_readline":
        raw = await process.stdout.readline()
        if len(raw) > MAX_FRAME // 2:
            await terminate(process)
            raise ValueError("frame too large")
        return {"line": raw.decode("utf-8"), "returncode": process.returncode}
    if method == "process_write":
        data = params.get("data")
        if not isinstance(data, str) or len(data.encode()) > MAX_FRAME // 2:
            raise ValueError("frame too large")
        process.stdin.write(data.encode())
        await process.stdin.drain()
        return {}
    if method == "process_wait":
        return {"returncode": await process.wait()}
    if method == "process_stop":
        await terminate(process)
        PROCESSES.pop(handle, None)
        return {"returncode": process.returncode}
    raise ValueError("unsupported process operation")


async def hermes_start(params):
    configuration = params["configuration"]
    if not isinstance(configuration, dict):
        raise ValueError()
    name = secrets.token_hex(12)
    profile = Path("/home/voice/hermes") / name
    profile.mkdir(parents=True, mode=0o700)
    plugin = profile / "plugins/maslow-voice"
    plugin.mkdir(parents=True, mode=0o700)
    for filename in ("__init__.py", "plugin.yaml"):
        content = params["plugin"][filename]
        if not isinstance(content, str) or len(content) > 262144:
            raise ValueError()
        (plugin / filename).write_text(content)
    (profile / "skills").mkdir(mode=0o700)
    model = configuration.get("model", {})
    selected = model.get("default", model.get("model"))
    if not selected:
        raise ValueError()
    configuration["model"] = dict(model, provider="custom", base_url="http://127.0.0.1:11434/v1")
    configuration["fallback_model"], configuration["fallback_models"] = None, []
    configuration["terminal"] = {"backend": "local", "cwd": "/project"}
    port = 18000 + len(HERMES)
    token = secrets.token_urlsafe(32)
    configuration["platforms"] = {"api_server": {"enabled": True, "extra": {"host": "127.0.0.1", "port": port}}}
    (profile / "config.yaml").write_text(json.dumps(configuration))
    env = dict(os.environ)
    # Ignore host profile and provider environment; this profile is local only.
    env.update(HERMES_HOME=str(profile), API_SERVER_HOST="127.0.0.1", API_SERVER_PORT=str(port), API_SERVER_KEY=token,
        OPENAI_API_KEY="offline-local", OPENAI_BASE_URL="http://127.0.0.1:11434/v1", HERMES_ENABLE_PROJECT_PLUGINS="false",
        HERMES_NO_AUTO_INSTALL="1", DO_NOT_TRACK="1", MASLOW_VOICE_TOOL_SOCKET="/run/voice/tools.sock",
        MASLOW_VOICE_TOOL_TOKEN=params.get("environment", {}).get("MASLOW_VOICE_TOOL_TOKEN", "offline"),
        MASLOW_VOICE_MODE="offline", TERMINAL_CWD="/project")
    process = await launch(["hermes", "gateway", "run"], env=env, stdin=asyncio.subprocess.DEVNULL,
                           stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    endpoint = f"http://127.0.0.1:{port}"
    async def probe():
        return await asyncio.to_thread(json_request, endpoint + "/v1/capabilities", "GET", None, token)
    try:
        await _wait_for_hermes(process, probe)
    except BaseException:
        await terminate(process)
        raise
    HERMES[endpoint] = token
    return {"endpoint": endpoint, "token": token}


async def dispatch(method, params):
    if method == "configure":
        return await configure(params)
    if not READY:
        raise ValueError("not ready")
    if method == "model_request":
        path = params.get("path")
        if path not in {"/api/tags", "/api/show", "/api/chat", "/api/generate", "/v1/models", "/v1/chat/completions"}:
            raise ValueError("unsupported model operation")
        body = params.get("body")
        if isinstance(body, dict) and body.get("stream"):
            raise ValueError("streaming unsupported")
        return await asyncio.to_thread(json_request, "http://127.0.0.1:11434" + path, "POST" if body is not None else "GET", body)
    if method in {"process_start", "process_readline", "process_write", "process_wait", "process_stop"}:
        return await process_rpc(method, params)
    if method == "spawn":
        return await spawn(params)
    if method == "hermes_start":
        return await hermes_start(params)
    if method == "hermes_request":
        url = params["url"]
        parsed = urlsplit(url)
        endpoint = f"{parsed.scheme}://{parsed.netloc}"
        if endpoint not in HERMES or not re.fullmatch(r"/v1/(?:capabilities|runs(?:/[A-Za-z0-9_-]{1,160}(?:/(?:stop|steer|approval))?)?)", parsed.path):
            raise ValueError("unsupported hermes operation")
        if parsed.query or parsed.fragment or params.get("method", "GET") not in {"GET", "POST"}:
            raise ValueError()
        return await asyncio.to_thread(json_request, url, params.get("method", "GET"), params.get("body"), HERMES[endpoint], params.get("headers"))
    if method == "open_application":
        applications = {
            "terminal": (["foot", "--working-directory=/project"],),
            "files": (["nautilus", "--new-window", "/project"], ["thunar", "/project"]),
            "editor": (["code", "--user-data-dir=/home/voice/editor", "--extensions-dir=/home/voice/editor-extensions", "/project"],),
            "browser": (["chromium", "--ozone-platform=wayland", "--user-data-dir=/home/voice/browser", "--no-first-run", "--disable-background-networking", "--disable-sync", "--disable-extensions", "about:blank"],
                        ["google-chrome-stable", "--ozone-platform=wayland", "--user-data-dir=/home/voice/browser", "--no-first-run", "--disable-background-networking", "--disable-sync", "--disable-extensions", "about:blank"]),
        }
        choices = applications.get(params.get("application"), ())
        argv = next((candidate for candidate in choices if shutil.which(candidate[0])), None)
        if not os.environ.get("WAYLAND_DISPLAY") or not argv:
            raise ValueError("application unavailable")
        process = await launch(argv, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.sleep(0.5)
        if process.returncode is not None and process.returncode != 0:
            raise ValueError("application failed")
        return {"started": True, "isolated": True}
    if method == "open_url":
        url = params.get("url", "")
        parsed = urlsplit(url)
        if not os.environ.get("WAYLAND_DISPLAY") or parsed.username or parsed.password or parsed.scheme not in {"http", "https", "file"}:
            raise ValueError("invalid offline URL")
        if parsed.scheme in {"http", "https"} and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("offline URL must be local")
        if parsed.scheme == "file" and (parsed.netloc or not parsed.path.startswith("/project/")):
            raise ValueError("offline file must be in project")
        browser = next((shutil.which(b) for b in ("chromium", "google-chrome-stable", "google-chrome") if shutil.which(b)), None)
        if not browser:
            raise ValueError("browser unavailable")
        process = await launch([browser, "--ozone-platform=wayland", "--user-data-dir=/home/voice/browser",
            "--no-first-run", "--disable-background-networking", "--disable-sync", "--disable-extensions", "--new-window", url],
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.sleep(0.5)
        if process.returncode is not None and process.returncode != 0:
            raise ValueError("browser failed")
        return {"started": True, "isolated": True}
    raise ValueError("unsupported operation")


async def handle(message):
    identity = message.get("id")
    try:
        result = await dispatch(message.get("method"), message.get("params", {}))
        emit({"id": identity, "result": result})
    except Exception:
        # Never send raw exception strings, paths, provider responses or secrets.
        emit({"id": identity, "error": "Isolated operation failed."})


async def main():
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader(limit=MAX_FRAME + 1)
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)
    tasks = {}
    try:
        while raw := await reader.readline():
            if len(raw) > MAX_FRAME:
                break
            message = json.loads(raw)
            if not isinstance(message, dict):
                break
            if message.get("type") == "tool_result":
                future = TOOLS.get(message.get("id"))
                if future and not future.done():
                    future.set_result(message.get("result", {"error": message.get("error", "Tool unavailable")}))
                continue
            identity = message.get("id")
            if type(identity) is not int:
                break
            if message.get("type") == "cancel":
                if identity in tasks:
                    tasks[identity].cancel()
                continue
            if identity in tasks or len(tasks) >= 32:
                break
            task = asyncio.create_task(handle(message))
            tasks[identity] = task
            task.add_done_callback(lambda done, key=identity: tasks.pop(key, None))
    finally:
        for task in list(tasks.values()):
            task.cancel()
        if TOOL_SERVER:
            TOOL_SERVER.close()
        for process in CHILDREN:
            await terminate(process)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        sys.exit(1)
