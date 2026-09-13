import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from maslow_voice.errors import VoiceError
from maslow_voice import offline_worker
from maslow_voice.offline import OfflineRuntime, OfflineWorkspace, manifest, sandbox_command, snapshot, validate_model_tree


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "original"
        self.project.mkdir()
        (self.project / "readme.txt").write_text("original")

    def tearDown(self):
        self.temporary.cleanup()

    def test_copy_cannot_write_original_and_review_requires_stopped(self):
        workspace = OfflineWorkspace(self.root / "private", self.project)
        self.assertNotEqual((workspace.project / "readme.txt").stat().st_ino, (self.project / "readme.txt").stat().st_ino)
        (workspace.project / "readme.txt").write_text("private change")
        self.assertEqual((self.project / "readme.txt").read_text(), "original")
        workspace.active = True
        with self.assertRaises(VoiceError) as failure:
            workspace.review()
        self.assertEqual(failure.exception.code, "OFFLINE_STILL_RUNNING")
        workspace.active = False
        self.assertEqual(workspace.review()["changes"], [{"path": "readme.txt", "action": "modify"}])

    def test_symbolic_links_and_sockets_are_never_snapshotted(self):
        for kind in ("symlink", "socket", "fifo"):
            with self.subTest(kind=kind):
                unsafe = self.project / "unsafe"
                server = None
                if kind == "symlink":
                    unsafe.symlink_to(self.project / "readme.txt")
                elif kind == "socket":
                    server = socket.socket(socket.AF_UNIX)
                    server.bind(str(unsafe))
                else:
                    os.mkfifo(unsafe)
                try:
                    with self.assertRaises(VoiceError):
                        snapshot(self.project, self.root / "snapshot")
                    self.assertFalse((self.root / "snapshot").exists())
                finally:
                    if server:
                        server.close()
                    unsafe.unlink()

    def test_symlink_directory_ancestor_is_refused(self):
        (self.root / "alias").symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(VoiceError):
            snapshot(self.root / "alias", self.root / "snapshot")

    def test_export_is_explicit_and_binds_reviewed_bytes(self):
        workspace = OfflineWorkspace(self.root / "private", self.project)
        (workspace.project / "readme.txt").write_text("reviewed")
        review = workspace.review()
        (workspace.project / "readme.txt").write_text("changed after review")
        with self.assertRaises(VoiceError) as failure:
            workspace.export(review["digest"], ["readme.txt"])
        self.assertEqual(failure.exception.code, "EXPORT_REVIEW_EXPIRED")
        self.assertEqual((self.project / "readme.txt").read_text(), "original")

    def test_export_refuses_host_conflict_before_any_write(self):
        workspace = OfflineWorkspace(self.root / "private", self.project)
        (workspace.project / "new.txt").write_text("new")
        (workspace.project / "readme.txt").write_text("private")
        (self.project / "readme.txt").write_text("host edited")
        review = workspace.review()
        with self.assertRaises(VoiceError) as failure:
            workspace.export(review["digest"], ["new.txt", "readme.txt"])
        self.assertEqual(failure.exception.code, "EXPORT_CONFLICT")
        self.assertFalse((self.project / "new.txt").exists())

    def test_selected_add_modify_delete_export(self):
        (self.project / "delete.txt").write_text("remove")
        workspace = OfflineWorkspace(self.root / "private", self.project)
        (workspace.project / "readme.txt").write_text("new content")
        (workspace.project / "sub").mkdir()
        (workspace.project / "sub/new.sh").write_text("#!/bin/sh\n")
        (workspace.project / "sub/new.sh").chmod(0o700)
        (workspace.project / "delete.txt").unlink()
        review = workspace.review()
        workspace.export(review["digest"], ["sub/new.sh", "delete.txt"])
        self.assertEqual((self.project / "readme.txt").read_text(), "original")
        self.assertFalse((self.project / "delete.txt").exists())
        self.assertTrue((self.project / "sub/new.sh").stat().st_mode & 0o100)
        self.assertEqual(workspace.review()["changes"], [{"path": "readme.txt", "action": "modify"}])

    def test_saved_workspace_recovers_original_baseline_after_restart(self):
        workspace = OfflineWorkspace(self.root / "private", self.project)
        (workspace.project / "readme.txt").write_text("private change")
        restored = OfflineWorkspace.restore(workspace.directory)
        self.assertEqual(restored.source, self.project)
        self.assertEqual(restored.review(), workspace.review())
        restored.export(restored.review()["digest"], ["readme.txt"])
        self.assertEqual((self.project / "readme.txt").read_text(), "private change")
        self.assertEqual(OfflineWorkspace.restore(workspace.directory).review()["changes"], [])

    def test_saved_metadata_cannot_authorize_parent_traversal(self):
        workspace = OfflineWorkspace(self.root / "private", self.project)
        data = json.loads((workspace.directory / "workspace.json").read_text())
        data["baseline"]["../outside"] = data["baseline"]["readme.txt"]
        (workspace.directory / "workspace.json").write_text(json.dumps(data))
        with self.assertRaises(VoiceError):
            OfflineWorkspace.restore(workspace.directory)

    def test_private_snapshot_symlink_cannot_be_exported(self):
        workspace = OfflineWorkspace(self.root / "private", self.project)
        (workspace.project / "readme.txt").unlink()
        (workspace.project / "readme.txt").symlink_to(self.project / "readme.txt")
        with self.assertRaises(VoiceError):
            workspace.review()

    def test_models_reject_socket_without_suffix_guessing(self):
        validate_model_tree(self.project)
        (self.project / "model-cloud").write_text("regular model entry")
        validate_model_tree(self.project)
        (self.project / "model-link").symlink_to(self.project / "readme.txt")
        with self.assertRaises(VoiceError):
            validate_model_tree(self.project)


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    def test_command_has_no_host_ipc_or_host_home_mount(self):
        command = sandbox_command(Path("/state/work"), Path("/state/models"))
        self.assertIn("--unshare-all", command)
        self.assertIn("--clearenv", command)
        self.assertNotIn("--unshare-net-try", command)
        self.assertNotIn("--share-net", command)
        self.assertNotIn("/run/user", " ".join(command))
        for key in ("DBUS_SESSION_BUS_ADDRESS", "DISPLAY", "WAYLAND_DISPLAY", "SSH_AUTH_SOCK", "HTTP_PROXY"):
            self.assertNotIn(key, command)
        self.assertNotIn(["--ro-bind", "/", "/"], [command[i:i+3] for i in range(len(command))])
        display = sandbox_command(Path("/state/work"), Path("/state/models"), display_socket="/private/new-weston")
        self.assertIn("/private/new-weston", display)
        self.assertNotIn("/private", display)

    async def test_platform_failure_cannot_fall_back_to_host(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = OfflineRuntime(Path(root).resolve(), {"server_kind": "ollama", "ollama_models": "/unused"})
            with patch("maslow_voice.offline.sys.platform", "darwin"), patch("asyncio.create_subprocess_exec") as spawn:
                with self.assertRaises(VoiceError):
                    await runtime.start()
                spawn.assert_not_called()

    async def test_lmstudio_refused_for_strict_offline(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = OfflineRuntime(Path(root).resolve(), {"server_kind": "lmstudio"})
            with patch("maslow_voice.offline.sys.platform", "linux"), patch("maslow_voice.offline.shutil.which", return_value="/usr/bin/bwrap"):
                with self.assertRaises(VoiceError) as failure:
                    await runtime.start()
                self.assertEqual(failure.exception.code, "OFFLINE_OLLAMA_REQUIRED")

    async def test_worker_reports_only_confirmed_owned_hermes_exit(self):
        endpoint = "http://127.0.0.1:18000"
        params = {"url": endpoint + "/v1/runs/run_1", "method": "GET"}

        class Process:
            returncode = 75

        offline_worker.HERMES[endpoint] = {"token": "local", "process": Process()}
        emitted = []
        try:
            with patch.object(offline_worker, "READY", True), patch.object(offline_worker, "terminate") as terminate, \
                    patch.object(offline_worker, "emit", emitted.append):
                await offline_worker.handle({"id": 1, "method": "hermes_request", "params": params})
            self.assertEqual(emitted, [{"id": 1, "error": {"code": "OFFLINE_HERMES_EXITED"}}])
            terminate.assert_awaited_once_with(offline_worker.HERMES[endpoint]["process"])

            Process.returncode = None
            emitted.clear()
            with patch.object(offline_worker, "READY", True), patch.object(offline_worker, "emit", emitted.append), \
                    patch.object(offline_worker, "json_request", side_effect=OSError):
                await offline_worker.handle({"id": 2, "method": "hermes_request", "params": params})
            self.assertEqual(emitted, [{"id": 2, "error": "Isolated operation failed."}])
        finally:
            offline_worker.HERMES.pop(endpoint, None)

    async def test_terminate_cleans_owned_session_after_parent_exit(self):
        class Process:
            pid = 4321
            returncode = 75
            wait = AsyncMock()

        with patch.object(offline_worker.os, "killpg") as killpg:
            await offline_worker.terminate(Process())
        killpg.assert_called_once_with(4321, offline_worker.signal.SIGKILL)
        Process.wait.assert_not_awaited()

    async def test_runtime_allows_only_owned_hermes_exit_error(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = OfflineRuntime(Path(root).resolve(), {})

            class Process:
                returncode = 0

            for error, expected in (({"code": "OFFLINE_HERMES_EXITED"}, "OFFLINE_HERMES_EXITED"),
                                    ({"code": "UNTRUSTED_CODE"}, "OFFLINE_OPERATION_FAILED")):
                reader = asyncio.StreamReader()
                reader.feed_data((json.dumps({"id": 1, "error": error}) + "\n").encode())
                reader.feed_eof()
                runtime.process = Process()
                runtime.process.stdout = reader
                future = asyncio.get_running_loop().create_future()
                runtime.pending[1] = future
                await runtime._read()
                with self.assertRaises(VoiceError) as failure:
                    await future
                self.assertEqual(failure.exception.code, expected)


@unittest.skipUnless(sys.platform == "linux" and shutil.which("bwrap"), "requires real Linux bubblewrap")
class LinuxIsolationTests(unittest.TestCase):
    def test_real_isolated_process_rpc_streams_and_kills_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            run = root / "workspace"
            run.mkdir()
            for name in ("home", "project"):
                (run / name).mkdir()
            models = root / "models"
            models.mkdir()
            host_secret = root / "host-secret"
            host_secret.write_text("outside")
            worker = Path(__file__).resolve().parent.parent / "maslow_voice/offline_worker.py"
            command = sandbox_command(run, models, worker=worker)
            child = (
                "import os,sys,subprocess,time; "
                f"assert not os.path.exists({str(host_secret)!r}); "
                "assert 'SECRET_SENTINEL' not in os.environ; "
                "subprocess.Popen(['/usr/bin/python3','-c',"
                "\"import time;time.sleep(0.5);open('/project/escaped-child','w').write('alive')\"]); "
                "print(sys.stdin.readline().strip(),flush=True);time.sleep(60)"
            )
            code = '''import asyncio,json,runpy
worker=runpy.run_path('/worker.py')
rpc=worker['process_rpc']
async def check():
 result=await rpc('process_start',{'argv':['/usr/bin/python3','-u','-c',%r],'cwd':'/project'})
 handle=result['handle']
 assert isinstance(handle,str) and len(handle)==48
 try:
  await rpc('process_stop',{'handle':'foreign'})
 except ValueError: pass
 else: raise AssertionError('foreign handle accepted')
 await rpc('process_write',{'handle':handle,'data':'permission denied\\n'})
 assert (await rpc('process_readline',{'handle':handle}))['line']=='permission denied\\n'
 assert (await rpc('process_stop',{'handle':handle}))['returncode'] != 0
 assert handle not in worker['PROCESSES']
 await asyncio.sleep(0.7)
 from pathlib import Path
 assert not Path('/project/escaped-child').exists()
 print(json.dumps({'rpc':'private','stream':'roundtrip','descendants':'stopped'}))
asyncio.run(check())
''' % child
            result = subprocess.run(command[:-1] + ["-c", code],
                env={"PATH": os.environ["PATH"], "SECRET_SENTINEL": "hidden"}, capture_output=True, text=True, timeout=15)
            if result.returncode and "namespace" in result.stderr and not os.environ.get("MASLOW_REQUIRE_ISOLATION_TEST"):
                self.skipTest("host kernel/container cannot create namespaces; no enforcement claim")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["descendants"], "stopped")
            self.assertFalse((run / "project/escaped-child").exists())
            self.assertEqual(host_secret.read_text(), "outside")

    def test_real_network_filesystem_and_descendant_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            run = root / "workspace"
            run.mkdir()
            for name in ("home", "project"):
                (run / name).mkdir()
            models = root / "models"
            models.mkdir()
            host_secret = root / "host-secret"
            host_secret.write_text("must remain outside")
            host_ipc = root / "host.sock"
            with socket.socket() as tcp, socket.socket(socket.AF_UNIX) as unix:
                tcp.bind(("127.0.0.1", 0))
                tcp.listen()
                unix.bind(str(host_ipc))
                unix.listen()
                port = tcp.getsockname()[1]
                worker = Path(__file__).resolve().parent.parent / "maslow_voice/offline_worker.py"
                command = sandbox_command(run, models, worker=worker)
                code = '''import json, os, socket, subprocess
assert not os.path.exists(%r)
assert not os.path.exists(%r)
assert 'SECRET_SENTINEL' not in os.environ
assert not os.path.exists('/run/dbus/system_bus_socket')
assert not os.path.exists('/tmp/.X11-unix')
for target in [('127.0.0.1', %d), ('1.1.1.1', 53)]:
 s=socket.socket(); s.settimeout(1)
 try: s.connect(target)
 except OSError: pass
 else: raise AssertionError('host or internet reachable')
 s.close()
subprocess.run(['/usr/bin/python3','-c',"import os; assert not os.path.exists(%r); open('/project/result','w').write('private')"],check=True)
print(json.dumps({'network':'isolated','host_ipc':'absent','descendants':'isolated'}))
''' % (str(host_secret), str(host_ipc), port, str(host_secret))
                result = subprocess.run(command[:-1] + ["-c", code], env={"PATH": os.environ["PATH"], "SECRET_SENTINEL": "hidden"}, capture_output=True, text=True)
                if result.returncode and "namespace" in result.stderr and not os.environ.get("MASLOW_REQUIRE_ISOLATION_TEST"):
                    self.skipTest("host kernel/container cannot create namespaces; no enforcement claim")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["network"], "isolated")
                self.assertEqual((run / "project/result").read_text(), "private")
                self.assertEqual(host_secret.read_text(), "must remain outside")
