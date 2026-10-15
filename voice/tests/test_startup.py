"""Actual Python import/cache controls with an inert derived package fixture."""
import importlib._bootstrap_external
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from maslow_voice.errors import VoiceError
from maslow_voice import startup

FLAGS = ["-I", "-S", "-B", "-X", "pycache_prefix=/dev/null"]


class StartupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="voice-startup-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "package"
        self.module = self.package / "maslow_voice"
        self.module.mkdir(parents=True)
        self.site = self.package / "venv/lib/python3.14/site-packages"
        self.site.mkdir(parents=True)
        interpreter = self.package / "venv/bin/python"
        interpreter.parent.mkdir(parents=True)
        interpreter.symlink_to(sys.executable)
        self.python = str(interpreter)
        self.bootstrap = self.package / "bootstrap.py"
        source = Path(__file__).resolve().parents[1] / "bootstrap.py"
        # Only fixed fixture path changes; this is import-resolution proof,
        # not root ownership, signed-package or installed acceptance evidence.
        self.bootstrap.write_text(source.read_text().replace('ROOT = "/usr/lib/maslow-voice"', 'ROOT = ' + repr(str(self.package))))
        (self.module / "__init__.py").write_text("")
        self.good = "import json,sys;print(json.dumps({'source':'REVIEWED','argv':sys.argv[1:],'isolated':sys.flags.isolated,'noSite':sys.flags.no_site,'prefix':sys.pycache_prefix}))\n"
        for name in ("daemon", "control"):
            (self.module / (name + ".py")).write_text(self.good)
        self.hostile = self.root / "hostile"
        shadow = self.hostile / "maslow_voice"
        shadow.mkdir(parents=True)
        (shadow / "__init__.py").write_text("print('CWD-SHADOW')\n")
        (shadow / "daemon.py").write_text("print('WRONG-DAEMON')\n")
        (self.hostile / "sitecustomize.py").write_text("print('USER-STARTUP')\n")
        (self.site / "evil.pth").write_text("import builtins;builtins.print('PTH-STARTUP')\n")
        (self.site / "sitecustomize.py").write_text("print('SITE-STARTUP')\n")
        self.environment = dict(os.environ, PYTHONPATH=str(self.hostile), PYTHONPYCACHEPREFIX=str(self.hostile / "cache"),
                                PYTHONUSERBASE=str(self.hostile), PYTHONSTARTUP=str(self.hostile / "sitecustomize.py"))

    def run_bootstrap(self, mode="daemon", args=(), flags=FLAGS):
        return subprocess.run([self.python, *flags, str(self.bootstrap), mode, *args],
            cwd=self.hostile, env=self.environment, capture_output=True, text=True, timeout=10)

    def test_fixed_isolated_bootstrap_ignores_cwd_pythonpath_and_site_startup_hooks(self):
        result = self.run_bootstrap()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"source": "REVIEWED", "argv": [], "isolated": 1, "noSite": 1, "prefix": "/dev/null"}, json.loads(result.stdout))
        self.assertEqual("", result.stderr)
        self.assertFalse((self.hostile / "cache").exists())

    def test_matching_timestamp_size_stale_bytecode_is_read_by_B_alone_but_not_fixed_prefix(self):
        source = self.module / "daemon.py"
        info = source.stat()
        cache = Path(importlib.util.cache_from_source(str(source)))
        cache.parent.mkdir()
        cache.write_bytes(importlib._bootstrap_external._code_to_timestamp_pyc(
            compile("print('STALE-CACHE')\n", str(source), "exec"), int(info.st_mtime), info.st_size))
        command = "import sys;sys.path.insert(0," + repr(str(self.package)) + ");import maslow_voice.daemon"
        # -I removes hostile PYTHONPYCACHEPREFIX, yet -B still reads a valid
        # adjacent cache; this control isolates the need for the fixed prefix.
        vulnerable = subprocess.run([self.python, "-I", "-S", "-B", "-c", command], cwd=self.hostile,
            env=self.environment, capture_output=True, text=True, timeout=10)
        self.assertEqual("STALE-CACHE\n", vulnerable.stdout)
        self.assertEqual(0, vulnerable.returncode)
        safe = self.run_bootstrap()
        self.assertEqual(0, safe.returncode, safe.stderr)
        self.assertEqual("REVIEWED", json.loads(safe.stdout)["source"])

    def test_literal_control_selector_preserves_watch_and_refuses_arbitrary_module_path(self):
        result = self.run_bootstrap("control", ["--watch"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["--watch"], json.loads(result.stdout)["argv"])
        for mode, args in (("../arbitrary", []), ("other_module", []), ("daemon", ["--arbitrary"])):
            result = self.run_bootstrap(mode, args)
            self.assertNotEqual(0, result.returncode)
            self.assertNotIn("REVIEWED", result.stdout)
            self.assertNotIn("CWD-SHADOW", result.stdout)

    def test_missing_fixed_package_never_executes_site_fallback_parent(self):
        (self.module / "__init__.py").unlink()
        fallback = self.site / "maslow_voice"
        fallback.mkdir()
        (fallback / "__init__.py").write_text("print('WRONG-PARENT')\n")
        (fallback / "daemon.py").write_text("print('WRONG-DAEMON')\n")
        result = self.run_bootstrap()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("origin could not be verified", result.stderr)

    def test_missing_isolation_cache_or_site_flags_fail_before_module(self):
        for flags in (["-S", "-B", "-X", "pycache_prefix=/dev/null"], ["-I", "-B", "-X", "pycache_prefix=/dev/null"],
                      ["-I", "-S", "-X", "pycache_prefix=/dev/null"], ["-I", "-S", "-B"]):
            result = self.run_bootstrap(flags=flags)
            with self.subTest(flags=flags):
                self.assertNotEqual(0, result.returncode)
                self.assertNotIn("REVIEWED", result.stdout)

    def test_control_shell_ignores_BASH_ENV_and_executes_fixed_isolated_argv(self):
        source = Path(__file__).resolve().parents[1] / "bin/omarchy-voice-control"
        wrapper = self.root / "control"
        wrapper.write_text(source.read_text().replace("/usr/lib/maslow-voice", str(self.package)))
        wrapper.chmod(0o700)
        bash_env = self.hostile / "bash-env"
        bash_env.write_text("echo BASH-STARTUP\n")
        result = subprocess.run([str(wrapper), "--watch"], cwd=self.hostile,
            env=self.environment | {"BASH_ENV": str(bash_env)}, capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["--watch"], json.loads(result.stdout)["argv"])
        self.assertNotIn("BASH-STARTUP", result.stdout)

    def test_live_preparation_requires_flags_fixed_executable_and_loaded_module_origin(self):
        valid = SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)
        with patch.object(startup.sys, "flags", valid), patch.object(startup.sys, "pycache_prefix", "/dev/null"), \
                patch.object(startup.sys, "executable", "/usr/lib/maslow-voice/venv/bin/python"), \
                patch.object(startup.sys, "argv", ["/usr/lib/maslow-voice/maslow_voice/daemon.py"]), \
                patch.object(startup, "__file__", "/usr/lib/maslow-voice/maslow_voice/startup.py"):
            startup.canonical_startup()
            for key in ("isolated", "no_site", "dont_write_bytecode"):
                setattr(valid, key, 0)
                with self.subTest(key=key), self.assertRaises(VoiceError):
                    startup.canonical_startup()
                setattr(valid, key, 1)
            for owner, field, bad in ((startup.sys, "pycache_prefix", "/tmp/cache"), (startup.sys, "executable", "/tmp/python"),
                                      (startup.sys, "argv", ["/tmp/daemon.py"]), (startup, "__file__", "/tmp/startup.py")):
                with patch.object(owner, field, bad), self.assertRaises(VoiceError):
                    startup.canonical_startup()

    def test_packaged_unit_uses_fixed_bootstrap_and_clears_loader_injection(self):
        unit = (Path(__file__).resolve().parents[1] / "systemd/maslow-voice.service").read_text()
        self.assertIn("ExecStart=/usr/lib/maslow-voice/venv/bin/python -I -S -B -X pycache_prefix=/dev/null /usr/lib/maslow-voice/bootstrap.py daemon\n", unit)
        self.assertNotIn("\nEnvironment=PYTHONPATH", unit)
        unset = next(line.split("=", 1)[1].split() for line in unit.splitlines() if line.startswith("UnsetEnvironment="))
        self.assertTrue({"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE", "PYTHONPYCACHEPREFIX", "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT"} <= set(unset))
