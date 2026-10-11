"""Actual Python entry isolation with fixture install paths, no credentials."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ControlEntryTests(unittest.TestCase):
    def test_private_entry_ignores_project_modules_and_inherited_python_paths(self):
        source=Path(__file__).resolve().parents[1] / 'bin/omarchy-free-ai'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            package=root/'installed/maslow_free_ai';package.mkdir(parents=True)
            (package/'__init__.py').write_text('')
            (package/'control.py').write_text("import json,sys\ndef main(): print(json.dumps({'entry':'reviewed-private-package','argv':sys.argv[1:]}))\n")
            project=root/'project';(project/'maslow_free_ai').mkdir(parents=True)
            (project/'maslow_free_ai/__init__.py').write_text("raise RuntimeError('unselected project module executed')\n")
            (project/'sitecustomize.py').write_text("raise RuntimeError('inherited Python path executed')\n")
            launcher=root/'omarchy-free-ai'
            # Only the absolute installation fixture path differs. Execute the
            # shipped launcher expression with real bash/Python and hostile cwd.
            launcher.write_text(source.read_text().replace('/usr/lib/maslow-free-ai',str(root/'installed')))
            launcher.chmod(0o700)
            result=subprocess.run([str(launcher),'status'],cwd=project,
                env={'PATH':'/usr/bin:/bin','HOME':str(root),'PYTHONPATH':str(project),'PYTHONSTARTUP':str(project/'sitecustomize.py')},
                text=True,capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),{'entry':'reviewed-private-package','argv':['status']})
            self.assertEqual(result.stderr,'')
