"""Real managed Hermes Runs/Unix-tool integration with synthetic inference only.

Run with the installed Voice interpreter. The outer process creates a private
network namespace and temporary home before importing Voice or starting Hermes.
No provider account, installed service, microphone, or consumer profile is used.
"""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
MODEL = "openai/gpt-oss-120b"
TOOLS = {"maslow_list_documents", "maslow_read_document", "maslow_create_note"}
NOTE = b"# Managed integration proof\n\nSynthetic content only.\n"
TOKEN = "synthetic-loopback-fixture-token-000000000000"


class FakeInference:
    def __init__(self, root):
        self.root = root
        self.case = None
        self.requests = []
        self.errors = []
        self.metadata_probes = []
        self.tool_replies = {}
        self.counts = {}

    async def start(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0, limit=262144)
        self.port = self.server.sockets[0].getsockname()[1]

    async def handle(self, reader, writer):
        try:
            header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            lines = header.decode("ascii").split("\r\n")
            method, path, _ = lines[0].split(" ")
            headers = dict(line.lower().split(":", 1) for line in lines[1:] if ":" in line)
            if method == "GET" and path in {"/api/v1/models", "/api/tags", "/v1/props", "/props", "/version", "/v1/models", "/models"}:
                self.metadata_probes.append(path)
                await self.reply(writer, 404, {"error": {"message": "Metadata probing is unsupported by this fixture"}})
                return
            if method != "POST" or path != "/v1/chat/completions":
                self.errors.append({"unexpected_method": method, "unexpected_path": path})
                await self.reply(writer, 404, {"error": {"message": "Fixture supports chat completions only"}})
                return
            if headers.get("authorization", "").strip() != "bearer " + TOKEN:
                raise AssertionError("Unexpected local inference credential")
            size = int(headers.get("content-length", "0"))
            if not 0 < size <= 262144:
                raise AssertionError("Unbounded fixture request")
            body = json.loads(await asyncio.wait_for(reader.readexactly(size), 10))
            self.counts[self.case] = self.counts.get(self.case, 0) + 1
            if self.counts[self.case] > 6:
                raise AssertionError("Fixture request budget exceeded")
            self.requests.append({"case": self.case, "body": body})
            (self.root / "requests.json").write_text(json.dumps(self.requests))
            if body.get("model") != MODEL:
                raise AssertionError("Unexpected inference model")
            advertised = {tool["function"]["name"] for tool in body.get("tools", [])}
            expected_tools = TOOLS | ({"maslow_read_calendar"} if self.case == "calendar" else set())
            if advertised and advertised != expected_tools:
                raise AssertionError("Managed advertised tool set changed: " + repr(sorted(advertised)))
            replies = [message for message in body.get("messages", []) if message.get("role") == "tool"]
            if not advertised:
                # Hermes may generate a session title using its configured main
                # route. This separate bounded call receives no capabilities.
                message = {"role": "assistant", "content": "Synthetic integration title"}
                finish = "stop"
            elif replies:
                self.tool_replies[self.case] = replies
                message = {"role": "assistant", "content": "Synthetic note saved." if self.case == "create" else "Synthetic Calendar event read." if self.case == "calendar" else "Unadvertised terminal tool was denied."}
                finish = "stop"
            else:
                if self.case == "create":
                    name, arguments = "maslow_create_note", {"path": "proof.md", "content": NOTE.decode()}
                elif self.case == "calendar":
                    name, arguments = "maslow_read_calendar", {"accountId":"ca_selected", "timeMin":"2026-10-11T00:00:00Z", "timeMax":"2026-10-12T00:00:00Z"}
                else:
                    name = "terminal"
                    arguments = {"command": "printf fixture-only > " + shlex.quote(str(self.root / "forbidden-marker"))}
                message = {"role": "assistant", "content": None, "tool_calls": [{"id": "call_" + self.case,
                    "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]}
                finish = "tool_calls"
            response = {"id": "fixture_" + self.case, "object": "chat.completion", "created": int(time.time()), "model": MODEL,
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 30, "total_tokens": 230}}
            if body.get("stream"):
                delta = dict(message)
                if delta.get("tool_calls"):
                    delta["tool_calls"] = [dict(call, index=index) for index, call in enumerate(delta["tool_calls"])]
                chunk = {"id": response["id"], "object": "chat.completion.chunk", "created": response["created"], "model": MODEL,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                done = dict(chunk, choices=[{"index": 0, "delta": {}, "finish_reason": finish}], usage=response["usage"])
                payload = ("data: " + json.dumps(chunk) + "\n\ndata: " + json.dumps(done) + "\n\ndata: [DONE]\n\n").encode()
                await self.reply(writer, 200, payload, "text/event-stream")
            else:
                await self.reply(writer, 200, response)
        except Exception as error:
            self.errors.append({"fixture_error": type(error).__name__, "message": str(error)[:300]})
            try:
                await self.reply(writer, 400, {"error": {"message": "Synthetic fixture rejected request"}})
            except (OSError, RuntimeError):
                pass
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    async def reply(writer, status, body, content_type="application/json"):
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        writer.write(f"HTTP/1.1 {status} Fixture\r\nContent-Type: {content_type}\r\nContent-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode() + payload)
        await writer.drain()


class SyntheticRouter:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.owners = set()
        self.released = []

    async def acquire(self, owner):
        if self.owners:
            raise AssertionError("Only one fixture owner is allowed")
        self.owners.add(owner)
        return {"endpoint": self.endpoint, "token": TOKEN, "model": MODEL}

    async def release(self, owner):
        self.owners.remove(owner)
        self.released.append(owner)

    def cooldown_message(self):
        return None


class SyntheticAccounts:
    """Explicit accepted-package/remote-account fixture, never live evidence."""
    def __init__(self):
        self.created, self.reads, self.revoked = [], [], []

    def available(self):
        return True

    async def ensure(self, task, store):
        self.created.append(task["id"])
        return store.update(task["id"], connect_session={"sessionId":"d" * 64})

    async def read(self, task, params):
        assert task["granted_capabilities"]["accounts"] == ["ca_selected"]
        assert task["requested_capabilities"]["send_to_groq_confirmed"] is True
        assert params == {"accountId":"ca_selected", "timeMin":"2026-10-11T00:00:00Z", "timeMax":"2026-10-12T00:00:00Z"}
        self.reads.append(task["id"])
        return {"schemaVersion":1, "accountId":"ca_selected", "operation":"calendar.events.list",
            "untrustedContent":True, "speechAuthorized":False, "data":{"events":[{"summary":"Synthetic selected Calendar event"}], "hasMore":False}}

    async def revoke(self, task):
        self.revoked.append(task["id"])


def prohibited(*args, **kwargs):
    raise AssertionError("Audio, conversation provider, or consumer executor must not run")


class NoCredentials:
    async def get(self, *args, **kwargs):
        raise AssertionError("Credential lookup must not run")


async def inner(root, selected_case):
    if os.readlink("/proc/self/ns/net") == os.environ["MASLOW_PROBE_OUTER_NETNS"]:
        raise AssertionError("A separate network namespace is required")
    if {name for _, name in socket.if_nameindex()} != {"lo"}:
        raise AssertionError("Only loopback may be present")
    sys.path[:0] = [str(ROOT / "voice"), str(ROOT / "free_ai")]
    from maslow_voice.assistant_runtime import AssistantRuntime
    from maslow_voice.daemon import VoiceService
    from maslow_voice.ipc import MAX_REQUEST

    fixture = FakeInference(root)
    await fixture.start()
    router = SyntheticRouter(f"http://127.0.0.1:{fixture.port}/v1")
    service = VoiceService(root / "state", root / "runtime", provider_factory=prohibited,
        audio_transport_factory=prohibited, executor_factory=prohibited, credentials=NoCredentials())
    runtime = AssistantRuntime(service.directory, service.tool_socket, service.tool_token, router)
    service.tasks.assistant_factory = runtime.ensure
    accounts = SyntheticAccounts()
    service.tasks.account_bridge = accounts
    service.tool_server = await asyncio.start_unix_server(service._tool_connection, str(service.tool_socket), limit=MAX_REQUEST + 1)
    service.tool_socket.chmod(0o600)
    cases = []
    try:
        for case in (("create", "denied", "calendar") if selected_case == "all" else (selected_case,)):
            fixture.case = case
            workspace = root / ("workspace-" + case)
            workspace.mkdir()
            task = await service.tasks.submit_assistant("probe-" + case, "Synthetic integration request.", str(workspace),
                {"note": "proof.md"} if case == "create" else {"accounts":["ca_selected"], "send_to_groq_confirmed":True} if case == "calendar" else {})
            monitor = service.tasks.monitors[task["id"]]
            try:
                await asyncio.wait_for(asyncio.shield(monitor), 110)
            except TimeoutError:
                raise AssertionError("Managed Runs task timed out") from None
            saved = service.store.get(task["id"])
            client = service.tasks.clients.get(task["id"])
            facts = {"case": case, "state": saved["state"], "error": saved.get("error"),
                "requests": fixture.counts.get(case, 0), "result": saved.get("result", "")[:300],
                "released": bool(client and client.released), "process_exited": bool(client and client.process.returncode is not None)}
            cases.append(facts)
            if saved["state"] != "completed":
                raise AssertionError("Managed Runs task did not complete: " + json.dumps(facts))
            if not client or not client.released or client.process.returncode is None or router.owners:
                raise AssertionError("Managed process/router ownership was not released")
            try:
                os.killpg(client.process.pid, 0)
            except ProcessLookupError:
                facts["process_group_absent"] = True
            else:
                raise AssertionError("Owned Hermes process group survived release")
            replies = fixture.tool_replies.get(case, [])
            if not replies:
                raise AssertionError("No real tool response reached inference")
            if case == "create":
                path = workspace / "proof.md"
                if path.read_bytes() != NOTE:
                    raise AssertionError("Saved file bytes differ")
                receipt = {"path": str(path), "size": len(NOTE), "sha256": hashlib.sha256(NOTE).hexdigest()}
                artifact = saved.get("artifacts", [{}])[0]
                if {key: artifact.get(key) for key in receipt} != receipt or artifact.get("exists") is not True or saved.get("note_receipt", {}).get("state") != "created":
                    raise AssertionError("Persisted verified receipt differs")
                if not any(json.loads(reply["content"]).get("result") == receipt for reply in replies):
                    raise AssertionError("Verified bridge receipt did not reach the actual Hermes tool result")
                facts["file_sha256"] = receipt["sha256"]
                facts["file_bytes"] = len(NOTE)
                facts["receipt_verified"] = True
            elif case == "calendar":
                if accounts.created != [task["id"]] or accounts.reads != [task["id"]] or accounts.revoked != [task["id"]]:
                    raise AssertionError("Selected Calendar grant/read/revoke sequence differs")
                if not any("Synthetic selected Calendar event" in reply["content"] for reply in replies):
                    raise AssertionError("Calendar tool result did not reach the real Hermes tool bridge")
                if "Synthetic Calendar event read." in json.dumps(service.task_summary(saved)):
                    raise AssertionError("Private task result reached consumer speech summary")
                facts.update(conditional_account_tool=True, exact_selected_fixture_account=True, grant_revoked=True,
                    consumer_speech_withheld=True, live_account_verified=False)
            else:
                if (root / "forbidden-marker").exists():
                    raise AssertionError("Unadvertised terminal tool executed")
                denial = " ".join(str(reply.get("content", "")) for reply in replies)
                facts["tool_rejection"] = denial[:600]
                expected = "Tool 'terminal' does not exist. Available tools: " + ", ".join(sorted(TOOLS))
                if denial != expected:
                    raise AssertionError("Unadvertised tool did not return the installed name-gate rejection")
                facts["marker_absent"] = True
                facts["tool_rejection"] = denial[:400]
        if fixture.errors:
            raise AssertionError("Unexpected inference requests: " + json.dumps(fixture.errors))
        return {"status": "passed", "network": "private-loopback-only", "cases": cases, "router_releases": len(router.released),
            "unsupported_metadata_probes": fixture.metadata_probes,
            "inference_requests": [{"case": record["case"], "fields": sorted(record["body"]),
                "stream": record["body"].get("stream", False), "max_tokens": record["body"].get("max_tokens"),
                "tools": sorted(tool["function"]["name"] for tool in record["body"].get("tools", []))} for record in fixture.requests]}
    finally:
        await service.tasks.close()
        service.tool_server.close()
        await service.tool_server.wait_closed()
        fixture.server.close()
        await fixture.server.wait_closed()
        (root / "requests.json").write_text(json.dumps(fixture.requests))
        (root / "diagnostic.json").write_text(json.dumps({"cases": cases, "inference_errors": fixture.errors}))
        service.store.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inner-root", type=Path)
    parser.add_argument("--case", choices=("all", "create", "denied", "calendar"), default="all")
    parser.add_argument("--node", type=Path, help="Pinned Node executable for optional actual router policy validation")
    parser.add_argument("--upstream", type=Path, help="Applied upstream source tree containing the existing tsx dependency")
    args = parser.parse_args()
    if bool(args.node) != bool(args.upstream):
        parser.error("--node and --upstream must be supplied together")
    if args.inner_root:
        try:
            result = asyncio.run(inner(args.inner_root, args.case))
        except Exception as error:
            print(json.dumps({"status": "failed", "error": type(error).__name__, "message": str(error)[:1500]}), flush=True)
            return 1
        print(json.dumps(result), flush=True)
        return 0
    with tempfile.TemporaryDirectory(prefix="maslow-hermes-runs-") as folder:
        root = Path(folder)
        environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(root), "PYTHONDONTWRITEBYTECODE": "1",
            "MASLOW_PROBE_OUTER_NETNS": os.readlink("/proc/self/ns/net")}
        command = ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-net", "--ro-bind", "/", "/",
            "--tmpfs", "/home", "--ro-bind", str(ROOT), str(ROOT), "--tmpfs", "/tmp", "--bind", str(root), str(root),
            "--tmpfs", "/run/user", "--dev", "/dev", "--proc", "/proc", "--chdir", str(root), "--",
            sys.executable, str(Path(__file__).resolve()), "--inner-root", str(root), "--case", args.case]
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=370)
        print(result.stdout.strip())
        if args.node and result.returncode == 0:
            policy = args.upstream / "server/src/maslow/policy.ts"
            if policy.read_bytes() != (ROOT / "free_ai/router/src/maslow/policy.ts").read_bytes():
                raise AssertionError("Applied upstream policy differs from the reviewed source")
            check = """import fs from 'node:fs';
const {assertTextRequest}=await import(process.argv[2]);
const records=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
for(const record of records)assertTextRequest(record.body);
console.log(JSON.stringify({policy_compatible_requests:records.length}));
"""
            checked = subprocess.run([str(args.node), "--import", "tsx", "--input-type=module", "-", policy.as_uri(), str(root / "requests.json")],
                input=check, text=True, capture_output=True, cwd=args.upstream, env=environment, timeout=30)
            print(checked.stdout.strip())
            if checked.returncode:
                print(checked.stderr[-2000:], file=sys.stderr)
                return checked.returncode
        if result.returncode:
            diagnostic = root / "diagnostic.json"
            if diagnostic.exists():
                print(diagnostic.read_text())
            print(result.stderr[-2000:], file=sys.stderr)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
