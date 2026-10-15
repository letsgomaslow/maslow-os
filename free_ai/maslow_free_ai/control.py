"""Fixed terminal actions. Keys use a masked prompt and private Voice IPC."""

import asyncio
import getpass
import json
import os
import subprocess
import sys
import socket
import stat
import struct
from pathlib import Path

from .errors import FreeAIError
from .runtime import MODELS, PACKAGE, RouterRuntime

DELIVERY_TICKETS = Path('/run/maslow-hub-free-ai')


def delivery_pending():
    # Presence is a startup barrier even when a ticket is expired or malformed.
    # Do not instantiate State/Recovery: fresh delivery must remain file-free.
    try:
        (DELIVERY_TICKETS / str(os.getuid()) / 'ticket.json').lstat()
    except FileNotFoundError:
        return False
    except OSError:
        raise FreeAIError('DELIVERY_STATUS_UNAVAILABLE', 'Package admission could not be checked. No assistant state was changed.') from None
    return True


def maintenance_status():
    installed = (PACKAGE / 'node/bin/node').is_file() and (PACKAGE / 'router/server/dist/maslow-main.js').is_file()
    task_support = Path('/usr/lib/maslow-voice/assistant_worker.py').is_file() and Path('/usr/lib/maslow-voice/assistant_plugin/plugin.yaml').is_file()
    return {'installed':installed,'configured':False,'ready':False,'enabled':False,
            'state':'maintenance','free_plan':'unconfirmed','provider':'groq','task_support':task_support}


def readonly_status():
    """Inspect private settings without initializing or repairing user storage."""
    value = {"schema": 1, "enabled": False, "configured": False,
             "free_plan": "unconfirmed", "verified_routes": []}
    root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    directory = (root / "maslow-free-ai").absolute()
    descriptor = os.open(directory.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    pending = False
    try:
        for component in directory.parts[1:]:
            try:
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            except FileNotFoundError:
                break
            except OSError:
                raise FreeAIError("UNSAFE_STATE", "Free cloud AI storage could not be safely inspected. It was left unchanged.") from None
            os.close(descriptor)
            descriptor = child
        else:
            info = os.fstat(descriptor)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise FreeAIError("UNSAFE_STATE", "Free cloud AI storage must be private and belong to this user. It was left unchanged.")
            try:
                os.stat("maintenance.json", dir_fd=descriptor, follow_symlinks=False)
                pending = True
            except FileNotFoundError:
                pass
            try:
                settings = os.open("settings.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
            except FileNotFoundError:
                settings = None
            except OSError:
                raise FreeAIError("UNSAFE_STATE", "Free cloud AI settings could not be safely inspected. They were left unchanged.") from None
            if settings is not None:
                try:
                    info = os.fstat(settings)
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_size > 16384:
                        raise FreeAIError("UNSAFE_STATE", "Free cloud AI settings must be private, bounded and unaliased. They were left unchanged.")
                    with os.fdopen(settings, "rb", closefd=False) as stream:
                        raw = stream.read(16385)
                    if len(raw) > 16384:
                        raise FreeAIError("STATE_UNREADABLE", "Free cloud AI settings need recovery. They were left unchanged.")
                finally:
                    os.close(settings)
                def unique_object(pairs):
                    result = {}
                    for key, item in pairs:
                        if key in result:
                            raise ValueError()
                        result[key] = item
                    return result
                try:
                    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
                    if not isinstance(data, dict) or set(data) != set(value) or type(data["schema"]) is not int or data["schema"] != 1:
                        raise ValueError()
                    if any(type(data[key]) is not bool for key in ("enabled", "configured")):
                        raise ValueError()
                    if data["free_plan"] not in ("unconfirmed", "user-confirmed") or not isinstance(data["verified_routes"], list):
                        raise ValueError()
                    routes = data["verified_routes"]
                    if any(not isinstance(route, str) or route not in MODELS for route in routes) or len(set(routes)) != len(routes):
                        raise ValueError()
                    value = data
                except (ValueError, TypeError, UnicodeError):
                    raise FreeAIError("STATE_UNREADABLE", "Free cloud AI settings need recovery. They were left unchanged.") from None
    finally:
        os.close(descriptor)
    result = maintenance_status()
    ready = result["installed"] and result["task_support"] and value["configured"] and set(value["verified_routes"]) == set(MODELS) and value["free_plan"] == "user-confirmed" and not pending
    result.update(configured=value["configured"], enabled=value["enabled"], free_plan=value["free_plan"], ready=ready,
                  state="maintenance" if pending else "disabled" if ready and not value["enabled"] else "ready" if ready else "needs-setup")
    return result


async def request(value):
    path = Path(os.environ.get("XDG_RUNTIME_DIR", "")) / "maslow-voice/control.sock"
    if not os.environ.get("XDG_RUNTIME_DIR"):
        raise FreeAIError("NO_USER_SESSION", "Start setup in your desktop session.")
    try:
        reader, writer = await asyncio.open_unix_connection(str(path), limit=65536)
    except (FileNotFoundError, ConnectionRefusedError):
        process = await asyncio.create_subprocess_exec("systemctl", "--user", "start", "maslow-voice.service",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(process.wait(), 15)
        if process.returncode:
            raise FreeAIError("ASSISTANT_UNAVAILABLE", "The assistant task service needs repair through Hub.") from None
        for _ in range(30):
            try:
                reader, writer = await asyncio.open_unix_connection(str(path), limit=65536)
                break
            except (FileNotFoundError, ConnectionRefusedError):
                await asyncio.sleep(0.1)
        else:
            raise FreeAIError("ASSISTANT_UNAVAILABLE", "The assistant task service did not become ready.") from None
    try:
        info = path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise FreeAIError("UNSAFE_SOCKET", "The assistant's private connection needs repair.")
        pid, uid, _ = struct.unpack("3i", writer.get_extra_info("socket").getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        unit = await asyncio.create_subprocess_exec("systemctl", "--user", "show", "maslow-voice.service", "--property=MainPID", "--value",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        output, _ = await asyncio.wait_for(unit.communicate(), 5)
        if uid != os.getuid() or unit.returncode or output.strip() != str(pid).encode():
            raise FreeAIError("UNSAFE_SOCKET", "The assistant connection is not owned by its managed service.")
        writer.write(json.dumps(value).encode() + b"\n")
        await writer.drain()
        response = json.loads(await asyncio.wait_for(reader.readline(), 130))
        if response.get("ok") is not True:
            error = response.get("error", {})
            raise FreeAIError(error.get("code", "FREE_AI_FAILED"), error.get("message", "Free cloud AI needs attention."))
        return response
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in {"status", "setup", "test", "enable", "disable", "open", "update", "recover"}:
            raise FreeAIError("INVALID_ARGUMENT", "Choose status, setup, test, enable, disable, open, update, or recover.")
        operation = sys.argv[1]
        pending = delivery_pending()
        if operation == "status":
            result = {"ok": True, "status": maintenance_status() if pending else readonly_status()}
        elif operation in {"update", "recover"}:
            raise FreeAIError("DELIVERY_NOT_VERIFIED", "Package and database recovery are awaiting verification. No files were changed.")
        elif pending and operation in {'setup','test','enable','disable'}:
            raise FreeAIError('RECOVERY_PENDING', 'Finish the pending package operation before changing or checking the connection. No assistant state was changed.')
        elif operation == "open":
            launcher = "/usr/lib/maslow-voice/launch" if Path("/usr/lib/maslow-voice/launch").is_file() else "omarchy-launch-voice"
            subprocess.run([launcher, "tasks"], check=True, stdout=subprocess.DEVNULL)
            result = {"ok": True}
        else:
            value = {"action": "free_ai", "operation": operation}
            if operation == "setup":
                if not sys.stdin.isatty():
                    raise FreeAIError("PRIVATE_SETUP_REQUIRED", "Connect Groq through the masked desktop terminal setup.")
                print("Groq setup: create your own account at https://console.groq.com/keys", file=sys.stderr)
                print("Stay on Free. Do not add billing or upgrade to Developer. Your prompts and selected documents go to Groq.", file=sys.stderr)
                print("Review Groq privacy and optional Zero Data Retention at https://console.groq.com/docs/your-data. Maslow does not verify your retention settings.", file=sys.stderr)
                print("Maslow cannot independently verify your billing plan. Connected accounts are optional and awaiting scoped-access verification.", file=sys.stderr)
                if input("Confirm your account is on Free with no billing upgrade (type FREE): ") != "FREE":
                    raise FreeAIError("FREE_PLAN_CONFIRMATION_REQUIRED", "Setup was left unchanged. Confirm the Free plan when ready.")
                key = getpass.getpass("Groq API key (hidden): ")
                if input("Run up to two harmless function requests to check both approved routes? (type CHECK): ") != "CHECK":
                    raise FreeAIError("CHECK_NOT_REQUESTED", "Setup was left unchanged. No provider request was made.")
                value.update(key=key, free_plan_confirmed=True)
            result = asyncio.run(request(value))
        print(json.dumps(result), flush=True)
    except (FreeAIError, OSError, ValueError, EOFError, TimeoutError, subprocess.CalledProcessError) as error:
        safe = error.as_dict() if isinstance(error, FreeAIError) else {"code": "FREE_AI_UNAVAILABLE", "message": "Free cloud AI could not complete this operation."}
        print(json.dumps({"ok": False, "error": safe}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
