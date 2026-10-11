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
        result = subprocess.run([sys.executable,'-I','-c',script,str(source),str(self.root / 'tickets')],
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
        with patch.object(control,'RouterRuntime') as runtime:
            runtime.return_value.status.return_value={'state':'ready'}
            code,value = self.run_control('status')
        self.assertEqual((code,value),(0,{'ok':True,'status':{'state':'ready'}}))
        runtime.assert_called_once_with()
