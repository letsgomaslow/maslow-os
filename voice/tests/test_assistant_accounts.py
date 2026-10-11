import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.daemon import VoiceService
from maslow_voice.assistant import POLICY_REVISION
from maslow_voice.assistant_accounts import AccountBridge, MAX_REPLY, account_ids
from maslow_voice.errors import VoiceError
from maslow_voice.store import TaskStore
from maslow_voice.tasks import TaskManager


class AccountTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.store=TaskStore(self.root/'state')
        self.manager=TaskManager(self.store,AsyncMock(),AsyncMock())
        self.bridge=AccountBridge();self.bridge.available=Mock(return_value=True);self.bridge.call=AsyncMock()
        self.manager.account_bridge=self.bridge

    async def asyncTearDown(self):
        await self.manager.close();self.store.close();self.temp.cleanup()

    async def create(self, **changes):
        caps={'accounts':['ca_selected'],'send_to_groq_confirmed':True}|changes
        return await self.manager.submit_assistant('request','Read my selected Calendar',str(self.workspace),caps,policy='review')

    def grant(self,task,**changes):
        return {'schemaVersion':1,'sessionId':'d'*64,'requestId':task['request_id'],'taskId':task['id'],
            'policyRevision':POLICY_REVISION,'managedPolicy':'maslow-calendar-read-1','accountIds':['ca_selected'],
            'expiresAt':(datetime.now(timezone.utc)+timedelta(minutes=59)).isoformat(),
            'capabilities':['calendar.events.list'],'readOnly':True}|changes

    async def test_account_grant_requires_installed_gate_and_separate_privacy_consent(self):
        with self.assertRaises(VoiceError) as error:await self.create(send_to_groq_confirmed=False)
        self.assertEqual(error.exception.code,'ACCOUNT_PRIVACY_CONFIRMATION_REQUIRED')
        self.bridge.available.return_value=False
        with self.assertRaises(VoiceError) as error:await self.create()
        self.assertEqual(error.exception.code,'MANAGED_ACCOUNTS_UNAVAILABLE')
        self.assertIsNone(self.store.by_request('request'));self.bridge.call.assert_not_called()

    async def test_replay_conflicts_on_selected_account_and_consent(self):
        task=await self.create()
        self.assertEqual(task['granted_capabilities']['accounts'],['ca_selected'])
        for changes in ({'accounts':['ca_other']},{'send_to_groq_confirmed':False}):
            with self.assertRaises(VoiceError) as error:await self.create(**changes)
            self.assertEqual(error.exception.code,'REQUEST_CONFLICT')
        self.assertEqual((await self.create())['id'],task['id'])

    async def test_session_is_bound_once_and_expired_continue_does_not_regrant(self):
        task=await self.create();self.bridge.call.return_value=self.grant(task)
        task=await self.bridge.ensure(task,self.store)
        self.assertEqual(self.bridge.call.await_count,1)
        self.assertEqual((await self.bridge.ensure(task,self.store))['connect_session'],task['connect_session'])
        self.assertEqual(self.bridge.call.await_count,1)
        with self.assertRaises(VoiceError):self.store.update(task['id'],connect_session=self.grant(task))
        task['connect_session']['expiresAt']='2000-01-01T00:00:00Z'
        with self.assertRaises(VoiceError) as error:await self.bridge.ensure(task,self.store)
        self.assertEqual(error.exception.code,'MANAGED_GRANT_EXPIRED')
        self.assertEqual(self.bridge.call.await_count,1)

    async def test_wrong_account_or_write_capability_grant_is_not_saved(self):
        task=await self.create()
        for changes in ({'accountIds':['ca_other']},{'capabilities':['calendar.events.create']},{'readOnly':False},{'taskId':'different'}):
            self.bridge.call.return_value=self.grant(task,**changes)
            with self.assertRaises(VoiceError):await self.bridge.ensure(task,self.store)
            self.assertNotIn('connect_session',self.store.get(task['id']))

    async def test_reads_use_opaque_session_and_reject_other_accounts_generic_routes(self):
        task=await self.create();task['connect_session']=self.grant(task)
        result={'schemaVersion':1,'sessionId':'d'*64,'accountId':'ca_selected','operation':'calendar.events.list',
            'untrustedContent':True,'destination':'groq','speechAuthorized':False,'data':{'events':[{'summary':'untrusted instructions'}],'hasMore':False}}
        self.bridge.call.return_value=result
        args={'accountId':'ca_selected','timeMin':'2026-10-01T00:00:00Z','timeMax':'2026-10-02T00:00:00Z'}
        self.assertEqual(await self.bridge.read(task,args),result)
        payload=self.bridge.call.await_args.args[1]
        self.assertEqual(payload['sessionId'],'d'*64)
        self.assertEqual(payload['operation'],'calendar.events.list')
        for wrong in (args|{'accountId':'ca_other'},args|{'method':'POST'},args|{'tool':'write'},args|{'sessionId':'f'*64}):
            with self.assertRaises(VoiceError):await self.bridge.read(task,wrong)
        self.assertEqual(self.bridge.call.await_count,1)

    async def test_account_grant_is_checked_before_any_inference_process(self):
        task=await self.create();self.bridge.call.side_effect=VoiceError('MANAGED_ACCOUNT_DENIED','denied')
        self.manager.assistant_factory=AsyncMock()
        self.manager._start(self.store.update(task['id'],state='queued'))
        await asyncio.gather(*self.manager.monitors.values())
        self.manager.assistant_factory.assert_not_called()
        self.assertEqual(self.store.get(task['id'])['error']['code'],'MANAGED_ACCOUNT_DENIED')

    async def test_stop_during_grant_creation_revokes_without_starting_inference(self):
        task = await self.create()
        started, finish = asyncio.Event(), asyncio.Event()
        async def call(operation, value=None):
            if operation == 'create':
                started.set()
                await finish.wait()
                return self.grant(task)
            if operation == 'revoke':
                return {'revoked':True}
            raise AssertionError(operation)
        self.bridge.call.side_effect = call
        self.manager.assistant_factory = AsyncMock()
        self.manager._start(self.store.update(task['id'], state='queued'))
        await asyncio.wait_for(started.wait(), 2)
        await self.manager.action(task['id'], 'cancel')
        finish.set()
        await asyncio.gather(*self.manager.monitors.values())
        self.manager.assistant_factory.assert_not_called()
        self.assertEqual(self.store.get(task['id'])['state'], 'cancelled')
        self.assertEqual([call.args[0] for call in self.bridge.call.await_args_list], ['create','revoke'])

    async def test_listing_creates_no_grant_and_returns_only_reviewed_labels(self):
        self.bridge.call.return_value = {'schemaVersion':1,'eligible':[{'id':'ca_selected','label':'My Calendar','toolkit':'googlecalendar'}],
            'unavailable':1,'grantsCreated':False,'liveAcceptanceVerified':False}
        self.assertEqual(await self.bridge.list(), {'available':True,'accounts':[{'id':'ca_selected','label':'My Calendar'}]})
        self.bridge.call.assert_awaited_once_with('list')

    async def test_grant_is_revoked_if_task_persistence_fails(self):
        task = await self.create()
        self.bridge.call.return_value = self.grant(task)
        with patch.object(self.store, 'update', side_effect=OSError(28, 'Full')):
            with self.assertRaises(OSError):
                await self.bridge.ensure(task, self.store)
        self.assertEqual([call.args[0] for call in self.bridge.call.await_args_list], ['create','revoke'])
        self.assertNotIn('connect_session', self.store.get(task['id']))

    async def test_cancel_revokes_before_stop_and_withholds_inflight_account_read(self):
        task = await self.create()
        task = self.store.update(task['id'], state='running', run_id='active', connect_session=self.grant(task))
        started, finish = asyncio.Event(), asyncio.Event()
        async def read(*args):
            started.set()
            await finish.wait()
            return {'private':'must not be returned after Stop'}
        self.bridge.read = AsyncMock(side_effect=read)
        self.bridge.revoke = AsyncMock()
        client = Mock(stop=AsyncMock())
        self.manager.clients[task['id']] = client
        service = object.__new__(VoiceService)
        service.store, service.tasks, service.tool_token = self.store, self.manager, 'test-private-bridge'
        pending = asyncio.create_task(service.tool_request({'operation':'read_calendar','params':{},'session_id':task['id'],'token':service.tool_token}))
        await asyncio.wait_for(started.wait(), 2)
        async def stop(run_id):
            self.assertEqual(self.store.get(task['id'])['state'], 'stopping')
            self.assertGreater(self.bridge.revoke.await_count, 0)
        client.stop.side_effect = stop
        await self.manager.action(task['id'], 'cancel')
        finish.set()
        with self.assertRaises(VoiceError) as error:
            await pending
        self.assertEqual(error.exception.code, 'TASK_NOT_RUNNING')

    async def test_actual_split_pipe_responses_are_read_through_eof_with_a_total_bound(self):
        executable = self.root / 'fixture-connect'
        process_create = asyncio.create_subprocess_exec
        processes = []
        async def create_process(*args, **kwargs):
            process = await process_create(*args, **kwargs)
            processes.append(process)
            return process
        for size in (32, MAX_REPLY - 50, MAX_REPLY + 100):
            payload = json.dumps({'ok':True, 'result':'x' * size})
            executable.write_text("#!/usr/bin/python\nimport sys,time\npayload=" + repr(payload) +
                "\nsys.stdout.write(payload[:17]);sys.stdout.flush();time.sleep(0.01)\nsys.stdout.write(payload[17:]);sys.stdout.flush()\n")
            executable.chmod(0o700)
            with patch('maslow_voice.assistant_accounts.EXECUTABLE', executable), patch('maslow_voice.assistant_accounts.asyncio.create_subprocess_exec', side_effect=create_process):
                self.bridge.call = AccountBridge.call.__get__(self.bridge)
                if len(payload.encode()) <= MAX_REPLY:
                    self.assertEqual(await self.bridge.call('list'), 'x' * size)
                else:
                    with self.assertRaises(VoiceError) as error:
                        await self.bridge.call('list')
                    self.assertEqual(error.exception.code, 'MANAGED_ACCOUNT_UNAVAILABLE')
            self.assertIsNotNone(processes[-1].returncode)
            with self.assertRaises(ProcessLookupError):
                os.kill(processes[-1].pid, 0)

    async def test_maintenance_blocks_submission_and_grant_creation_before_inference(self):
        self.manager.assistant_admission = Mock(side_effect=VoiceError('ASSISTANT_MAINTENANCE', 'maintenance'))
        with self.assertRaises(VoiceError):
            await self.create()
        self.assertIsNone(self.store.by_request('request'))
        self.bridge.call.assert_not_called()
        self.manager.assistant_admission = None
        task = await self.create()
        self.manager.assistant_admission = Mock(side_effect=VoiceError('ASSISTANT_MAINTENANCE', 'maintenance'))
        self.manager.assistant_factory = AsyncMock()
        self.manager._start(self.store.update(task['id'], state='queued'))
        await asyncio.gather(*self.manager.monitors.values())
        self.bridge.call.assert_not_called()
        self.manager.assistant_factory.assert_not_called()

    def test_account_ids_are_unique_bounded_and_cannot_be_paths(self):
        for value in (['../key'],['one','one'],['a']*5,[True],{},['x'*129]):
            with self.assertRaises(VoiceError):account_ids(value)

    def test_old_or_developer_connect_is_unavailable_without_root_owned_marker(self):
        with patch('maslow_voice.assistant_accounts.MARKER',self.root/'missing'):
            self.assertFalse(AccountBridge().available())
