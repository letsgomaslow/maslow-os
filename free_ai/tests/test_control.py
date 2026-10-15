import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from maslow_free_ai import control


class DeliveryStatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ticket = self.root / 'tickets' / str(os.getuid()) / 'ticket.json'
        self.ticket.parent.mkdir(parents=True)
        self.state = self.root / 'state'

    def run_control(self, operation):
        output = io.StringIO()
        with patch.object(control,'DELIVERY_TICKETS',self.root / 'tickets'), \
                patch.dict(os.environ,{'XDG_STATE_HOME':str(self.state)}), \
                patch.object(control.sys,'argv',['omarchy-free-ai',operation]), \
                contextlib.redirect_stdout(output):
            try:
                control.main()
            except SystemExit as error:
                return error.code,json.loads(output.getvalue())
        return 0,json.loads(output.getvalue())

    def test_any_ticket_presence_reports_maintenance_without_creating_state(self):
        for text in ('not JSON','{"expiresAt":1}'):
            with self.subTest(text=text):
                self.ticket.write_text(text)
                with patch.object(control,'RouterRuntime') as runtime:
                    code,value = self.run_control('status')
                self.assertEqual(code,0)
                self.assertEqual(value['status']['state'],'maintenance')
                self.assertFalse(value['status']['ready'])
                runtime.assert_not_called()
                self.assertFalse(self.state.exists())
        self.ticket.unlink()
        self.ticket.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_control('status')[1]['status']['state'],'maintenance')
        self.assertFalse(self.state.exists())

    def test_pending_setup_and_mutations_do_not_prompt_or_start_service(self):
        self.ticket.write_text('{}')
        for operation in ('setup','test','enable','disable'):
            with self.subTest(operation=operation), patch.object(control,'request') as request, \
                    patch.object(control.getpass,'getpass') as prompt:
                code,value = self.run_control(operation)
                self.assertEqual(code,1)
                self.assertEqual(value['error']['code'],'RECOVERY_PENDING')
                prompt.assert_not_called()
                request.assert_not_called()
                self.assertFalse(self.state.exists())

    def test_actual_isolated_cli_poll_leaves_fresh_state_absent(self):
        self.ticket.write_text('{"expiresAt":1}')
        script = "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from maslow_free_ai import control; control.DELIVERY_TICKETS=Path(sys.argv[2]); sys.argv=['omarchy-free-ai','status']; control.main()"
        source = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable,'-I','-B','-c',script,str(source),str(self.root / 'tickets')],
            env={'PATH':'/usr/bin:/bin','HOME':str(self.root),'XDG_STATE_HOME':str(self.state),'PYTHONDONTWRITEBYTECODE':'1'},
            cwd=str(self.root),capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status']['state'],'maintenance')
        self.assertFalse(self.state.exists())

    def test_ticket_stat_error_does_not_fall_back_to_ready_or_create_state(self):
        with patch.object(control.Path,'lstat',side_effect=PermissionError()), patch.object(control,'RouterRuntime') as runtime:
            code,value = self.run_control('status')
        self.assertEqual(code,1)
        self.assertEqual(value['error']['code'],'DELIVERY_STATUS_UNAVAILABLE')
        runtime.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_no_ticket_keeps_existing_status_contract(self):
        with patch.object(control,'RouterRuntime') as runtime, patch.object(control.Path,'is_file',return_value=True):
            code,value = self.run_control('status')
        self.assertEqual((code,value),(0,{'ok':True,'status':{'installed':True,'configured':False,
            'ready':False,'enabled':False,'state':'needs-setup','free_plan':'unconfirmed','provider':'groq','task_support':True}}))
        runtime.assert_not_called()
        self.assertFalse(self.state.exists())

    def write_settings(self, **changes):
        directory = self.state / 'maslow-free-ai'
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / 'settings.json'
        value = {'schema':1,'enabled':True,'configured':True,'free_plan':'user-confirmed',
                 'verified_routes':list(control.MODELS)}
        path.write_text(json.dumps({**value, **changes}))
        path.chmod(0o600)
        return path

    def isolated_status(self):
        script = "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from maslow_free_ai import control; control.DELIVERY_TICKETS=Path(sys.argv[2]); sys.argv=['omarchy-free-ai','status']; control.main()"
        return subprocess.run([sys.executable,'-I','-B','-c',script,str(Path(__file__).resolve().parents[1]),str(self.root / 'tickets')],
            env={'PATH':'/usr/bin:/bin','HOME':str(self.root),'XDG_STATE_HOME':str(self.state),'PYTHONDONTWRITEBYTECODE':'1'},
            cwd=str(self.root),capture_output=True,text=True,timeout=10)

    def test_actual_cold_cli_leaves_state_absent_without_a_ticket(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    self.state.mkdir(mode=0o750)
                result = self.isolated_status()
                self.assertEqual(result.returncode,0,result.stderr)
                status = json.loads(result.stdout)['status']
                self.assertEqual(status['state'],'needs-setup')
                self.assertFalse(status['ready'])
                self.assertFalse((self.state / 'maslow-free-ai').exists())
                if existing:
                    self.assertEqual(self.state.stat().st_mode & 0o777,0o750)

    def test_actual_configured_cli_preserves_bytes_modes_and_tree(self):
        path = self.write_settings()
        before = {str(item): (item.stat().st_mode,item.read_bytes() if item.is_file() else None)
                  for item in (self.state,*self.state.rglob('*'))}
        result = self.isolated_status()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['status']['configured'])
        after = {str(item): (item.stat().st_mode,item.read_bytes() if item.is_file() else None)
                 for item in (self.state,*self.state.rglob('*'))}
        self.assertEqual(before,after)
        self.assertFalse((path.parent / 'recovery').exists())

    def test_saved_status_matches_ready_disabled_and_partial_contract(self):
        cases = (({},True,'ready'),({'enabled':False},True,'disabled'),
                 ({'configured':False},False,'needs-setup'),({'free_plan':'unconfirmed'},False,'needs-setup'),
                 ({'verified_routes':[control.MODELS[0]]},False,'needs-setup'))
        for changes, ready, state in cases:
            with self.subTest(changes=changes):
                self.write_settings(**changes)
                with patch.object(control.Path,'is_file',return_value=True), \
                        patch.object(control,'RouterRuntime') as router, \
                        patch('maslow_free_ai.runtime.State') as storage, \
                        patch('maslow_free_ai.runtime.Recovery') as recovery, \
                        patch('maslow_free_ai.runtime.EncryptionKey') as keys, \
                        patch.object(control,'request') as request:
                    code,value = self.run_control('status')
                self.assertEqual(code,0)
                self.assertEqual((value['status']['ready'],value['status']['state']),(ready,state))
                for constructor in (router,storage,recovery,keys,request):
                    constructor.assert_not_called()

    def test_missing_package_or_task_support_cannot_report_ready(self):
        self.write_settings()
        for missing in ('node/bin/node','router/server/dist/maslow-main.js','assistant_worker.py','assistant_plugin/plugin.yaml'):
            with self.subTest(missing=missing), patch.object(control.Path,'is_file',lambda path: not str(path).endswith(missing)):
                code,value = self.run_control('status')
            self.assertEqual(code,0)
            self.assertFalse(value['status']['ready'])

    def test_malformed_schema_routes_and_duplicate_fields_are_read_only_errors(self):
        path = self.write_settings()
        good = path.read_text()
        malformed = ['not JSON','[]',good.replace('"schema": 1','"schema": true'),
                     good.replace('"enabled": true','"enabled": 1'),
                     good.replace('"configured": true','"configured": 1'),
                     good.replace('"schema": 1','"schema": 1, "schema": 1'),
                     good.replace('user-confirmed','unknown'),
                     good.replace(control.MODELS[1],control.MODELS[0]),
                     good.replace(control.MODELS[1],'unknown'),
                     good.replace('"verified_routes": [','"verified_routes": [null,'),
                     good[:-1]+', "extra": 1}']
        for raw in malformed:
            with self.subTest(raw=raw):
                path.write_text(raw)
                code,value = self.run_control('status')
                self.assertEqual(code,1)
                self.assertEqual(value['error']['code'],'STATE_UNREADABLE')
                self.assertEqual(path.read_text(),raw)
                self.assertEqual(path.stat().st_mode & 0o777,0o600)
        path.write_bytes(b'\xff')
        self.assertEqual(self.run_control('status')[1]['error']['code'],'STATE_UNREADABLE')
        self.assertEqual(path.read_bytes(),b'\xff')

    def test_marker_presence_is_maintenance_including_broken_symlinks(self):
        path = self.write_settings()
        marker = path.parent / 'maintenance.json'
        for kind in ('malformed','symlink','directory'):
            with self.subTest(kind=kind):
                if kind == 'malformed': marker.write_text('not JSON')
                elif kind == 'symlink': marker.symlink_to(self.root / 'missing')
                else: marker.mkdir()
                with patch.object(control.Path,'is_file',return_value=True):
                    code,value = self.run_control('status')
                self.assertEqual(code,0)
                self.assertEqual(value['status']['state'],'maintenance')
                self.assertFalse(value['status']['ready'])
                self.assertTrue(value['status']['configured'])
                if kind == 'directory': marker.rmdir()
                else: marker.unlink()

    def test_public_unaliased_and_bounded_settings_require_safe_storage(self):
        path = self.write_settings()
        for target, mode in ((path,0o640),(path.parent,0o750)):
            with self.subTest(target=str(target)):
                original = target.stat().st_mode & 0o777
                target.chmod(mode)
                code,value = self.run_control('status')
                self.assertEqual(code,1)
                self.assertEqual(value['error']['code'],'UNSAFE_STATE')
                self.assertEqual(target.stat().st_mode & 0o777,mode)
                target.chmod(original)
        alias = path.parent / 'alias'
        os.link(path,alias)
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        alias.unlink()
        path.write_bytes(b' ' * 16385)
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')

    def test_symlink_ancestors_and_settings_are_rejected_without_changes(self):
        path = self.write_settings()
        path.unlink()
        path.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        path.unlink()
        path.parent.rmdir()
        path.parent.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        path.parent.unlink()
        self.state.rmdir()
        self.state.symlink_to(self.root / 'missing')
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        self.assertFalse((self.root / 'missing').exists())

    def test_settings_open_error_does_not_create_or_repair_storage(self):
        path = self.write_settings()
        original = control.os.open
        def denied(name, *args, **kwargs):
            if name == 'settings.json': raise PermissionError()
            return original(name,*args,**kwargs)
        with patch.object(control.os,'open',side_effect=denied):
            code,value = self.run_control('status')
        self.assertEqual(code,1)
        self.assertEqual(value['error']['code'],'UNSAFE_STATE')
        self.assertFalse((path.parent / 'recovery').exists())

    def test_wrong_owner_and_nonregular_settings_fail_closed(self):
        path = self.write_settings()
        with patch.object(control.os,'getuid',return_value=os.getuid()+1):
            self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        path.unlink()
        path.mkdir(mode=0o700)
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        path.rmdir()
        os.mkfifo(path,0o600)
        self.assertEqual(self.run_control('status')[1]['error']['code'],'UNSAFE_STATE')
        self.assertFalse((path.parent / 'recovery').exists())
