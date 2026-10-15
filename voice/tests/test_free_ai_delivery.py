import asyncio
import copy
import json
import os
import hashlib
import sqlite3
from pathlib import Path
import tempfile
import sys
import time
import unittest
from unittest.mock import AsyncMock, Mock, patch

# Optional backend source is a test input, not a Voice production dependency.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "free_ai"))

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.free_ai_delivery import (DeliveryCoordinator, canonical_ticket, barrier_present, operation_binding,
    process_start, read_ticket, startup_check)
from maslow_voice.ipc import ControlServer
from maslow_free_ai.errors import FreeAIError

TX = 'd' * 32
NONCE = 'a' * 64


def ticket():
    return {'schema':1,'action':'free-ai-install','transactionId':TX,'nonce':NONCE,'uid':os.getuid(),
        'expiresAt':int(time.time())+900,'sourceCommit':'b'*40,
        'targetArtifacts':{'maslow-free-ai':{'version':'0.1.0-2','sha256':'1'*64},'maslow-voice':{'version':'0.1.5-39','sha256':'2'*64}},
        'previousArtifacts':{'maslow-free-ai':{'version':'0.1.0-1','sha256':'3'*64},'maslow-voice':{'version':'0.1.5-38','sha256':'4'*64}}}


class TicketTests(unittest.TestCase):
    def test_rejection_ticket_encoding_is_ascii_sorted_compact_without_newline(self):
        self.assertEqual(b'{"a":1,"z":"\\u00e9"}',canonical_ticket({'z':'é','a':1}))

    def test_fixed_ticket_validates_identity_expiry_exact_fields_and_package_subset(self):
        value=ticket()
        with patch('maslow_voice.free_ai_delivery._protected_ticket',return_value=value):
            self.assertEqual(read_ticket(TX,NONCE),value)
        for field,changed in (('uid',os.getuid()+1),('nonce','f'*64),('expiresAt',int(time.time())-1),
            ('expiresAt',int(time.time())+4000),('schema',True),('targetArtifacts',{}),('previousArtifacts',{}),('sourceCommit','../module')):
            invalid=value|{field:changed}
            with self.subTest(field=field,changed=changed),patch('maslow_voice.free_ai_delivery._protected_ticket',return_value=invalid):
                with self.assertRaises(VoiceError):read_ticket(TX,NONCE)
        with patch('maslow_voice.free_ai_delivery._protected_ticket',return_value=value|{'path':'/unreviewed'}):
            with self.assertRaises(VoiceError):read_ticket(TX,NONCE)

    def test_actual_unprivileged_ticket_cannot_authorize_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/str(os.getuid());directory.mkdir();file=directory/'ticket.json'
            file.write_text(json.dumps(ticket()));file.chmod(0o644)
            with patch('maslow_voice.free_ai_delivery.TICKET_ROOT',root):
                self.assertTrue(barrier_present())
                with self.assertRaises(VoiceError):read_ticket(TX,NONCE)
                with self.assertRaises(VoiceError):startup_check()

    def test_kernel_start_identity_is_decimal_and_matches_self_stat(self):
        self.assertTrue(process_start().isdigit())
        expected=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        self.assertEqual(process_start(),expected)


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.service=VoiceService(self.root/'state',self.root/'runtime',credentials=Mock())
        self.ticket=ticket()
        self.receipt={'schema':1,'id':TX,'kind':'snapshot','database_sha256':'8'*64,'settings_sha256':'9'*64,
            'key_fingerprint':'7'*64,'artifacts':{'maslow-free-ai':'3'*64,'maslow-voice':'4'*64}}
        self.router=Mock(process=None,owners=set())
        self.router.state.directory=self.service.directory.parent/'maslow-free-ai'
        self.router.prepare_recovery=AsyncMock(return_value=self.receipt)
        self.router.recovery.pending=Mock(return_value=True)
        self.router.recovery.verify=AsyncMock(return_value=self.receipt)
        self.service._free_ai=Mock(return_value=self.router)
        self.read=patch('maslow_voice.free_ai_delivery._protected_ticket',return_value=self.ticket);self.read.start()
        self.addCleanup(self.read.stop)
        self.canonical=patch('maslow_voice.free_ai_delivery.canonical_paths',return_value=(self.service.directory,self.service.runtime))
        self.canonical.start();self.addCleanup(self.canonical.stop)
        self.startup=patch('maslow_voice.free_ai_delivery.canonical_startup')
        self.startup.start();self.addCleanup(self.startup.stop)
        self.sessions=patch('maslow_voice.free_ai_delivery.no_agent_sessions')
        self.sessions.start();self.addCleanup(self.sessions.stop)

    async def asyncTearDown(self):
        await self.service.tasks.close();self.service.store.close();self.temp.cleanup()

    async def test_failed_lazy_construction_cannot_later_claim_no_preparation(self):
        for failure in ('constructor', 'capability', 'canonical-path'):
            with self.subTest(failure=failure):
                self.service.delivery = DeliveryCoordinator(self.service)
                self.service.provider = None
                marker = self.root / ('constructor-touched-' + failure)
                def construct():
                    marker.write_text('synthetic constructor side effect')
                    if failure == 'constructor':
                        raise RuntimeError('synthetic constructor failure')
                    if failure == 'capability':
                        return object()
                    self.router.state.directory = Path('/not-canonical-router-state')
                    return self.router
                self.service._free_ai = Mock(side_effect=construct)
                with self.assertRaises((RuntimeError, VoiceError)):
                    await self.service.dispatch(self.request())
                self.assertTrue(marker.exists())
                self.assertFalse(self.service.delivery.closed)
                self.service.provider = object()
                with self.assertRaises(VoiceError) as error:
                    await self.service.dispatch(self.request())
                self.assertEqual(error.exception.code, 'FREE_AI_DELIVERY_PENDING')
                self.service._free_ai.assert_called_once()
                self.router.prepare_recovery.assert_not_called()
                self.assertIsNone(self.service.delivery.rejected)
                changed = self.ticket | {'expiresAt':self.ticket['expiresAt'] - 1}
                with patch('maslow_voice.free_ai_delivery._protected_ticket', return_value=changed):
                    with self.assertRaises(VoiceError) as error:
                        await self.service.dispatch(self.request())
                self.assertEqual(error.exception.code, 'FREE_AI_TICKET_INVALID')

    def request(self,operation='prepare'):
        return {'action':'free_ai_delivery','operation':operation,'transactionId':TX,'nonce':NONCE}

    def assertRejected(self, result, reason='active-work'):
        receipt=result['result']['rejection']
        self.assertEqual(receipt['reason'],reason)
        self.assertEqual(receipt['originalTicketSha256'],hashlib.sha256(canonical_ticket(self.ticket)).hexdigest())
        self.assertEqual(receipt['nonce'],self.ticket['nonce'])
        self.assertEqual(receipt['daemonPid'],os.getpid());self.assertEqual(receipt['daemonStart'],process_start())
        self.assertIs(receipt['admissionClosed'],False);self.assertIs(receipt['preparationStarted'],False)
        self.assertIs(receipt['continuationPending'],False)
        self.assertFalse(self.service.delivery.closed)
        self.service._free_ai.assert_not_called();self.router.prepare_recovery.assert_not_called()
        return receipt

    async def test_noncanonical_custom_state_is_rejected_before_preparation(self):
        with patch('maslow_voice.free_ai_delivery.canonical_paths',return_value=(Path('/not-the-state'),self.service.runtime)):
            with self.assertRaises(VoiceError) as error:
                await self.service.dispatch(self.request())
        self.assertEqual(error.exception.code,'FREE_AI_CANONICAL_STATE_REQUIRED')
        self.assertFalse(self.service.delivery.closed)
        self.router.prepare_recovery.assert_not_called()

    async def test_prepare_check_envelope_is_bound_and_snapshot_is_not_repeated(self):
        response=await self.service.dispatch(self.request())
        facts=response['result']
        self.assertEqual(facts['recoveryReceipt'],self.receipt)
        self.assertEqual(facts['uid'],os.getuid());self.assertEqual(facts['daemonPid'],os.getpid())
        self.assertTrue(facts['admissionClosed']);self.assertTrue(facts['ownedRouterStopped'])
        self.assertEqual(await self.service.dispatch(self.request('check')),response)
        self.router.prepare_recovery.assert_awaited_once_with(self.receipt['artifacts'],reserved_id=TX,operation=operation_binding(self.ticket))
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request())
        self.router.prepare_recovery.assert_awaited_once()

    async def test_active_tasks_or_conversation_reject_before_admission_changes(self):
        self.service.provider=object()
        self.assertRejected(await self.service.dispatch(self.request()))
        self.assertFalse(self.service.delivery.closed)
        self.router.prepare_recovery.assert_not_called()
        self.service.provider=None
        self.service.delivery=DeliveryCoordinator(self.service)
        self.service.store.create('active',{'objective':'private title','summary':'private'},str(self.root),'typed','private')
        result=await self.service.dispatch(self.request());self.assertRejected(result)
        self.assertFalse(self.service.delivery.closed)
        self.assertNotIn('private',json.dumps(result))

    async def test_inflight_control_rejects_busy_without_canceling_it(self):
        existing=asyncio.create_task(asyncio.sleep(20))
        self.service.control_requests.add(existing)
        try:
            self.assertRejected(await self.service.dispatch(self.request()))
            self.assertFalse(existing.cancelled());self.assertFalse(self.service.delivery.closed)
        finally:
            existing.cancel();await asyncio.gather(existing,return_exceptions=True)
            self.service.control_requests.clear()

    async def test_closure_precedes_first_await_and_blocks_every_new_workflow(self):
        entered,finish=asyncio.Event(),asyncio.Event()
        async def snapshot(artifacts, **kwargs):
            entered.set();await finish.wait();return self.receipt
        self.router.prepare_recovery.side_effect=snapshot
        pending=asyncio.create_task(self.service.dispatch(self.request()))
        await asyncio.wait_for(entered.wait(),2)
        try:
            for request in ({'action':'start_voice'},{'action':'task_submit'},{'action':'configure','settings':{}},
                {'action':'credential','name':'google','value':'synthetic'},{'action':'assistant_accounts','account_request_id':'example'}):
                with self.subTest(action=request['action']),self.assertRaises(VoiceError) as error:
                    await self.service.dispatch(request)
                self.assertEqual(error.exception.code,'FREE_AI_DELIVERY_PENDING')
            with self.assertRaises(VoiceError):
                await self.service.tasks.submit('new',{'objective':'new','summary':'new'},str(self.root),'typed','new',policy='review')
            self.assertIsNone(self.service.store.by_request('new'))
        finally:
            finish.set();await pending

    async def test_concurrent_or_failed_preparation_cannot_take_another_snapshot(self):
        entered, finish = asyncio.Event(), asyncio.Event()
        async def snapshot(artifacts, **kwargs):
            entered.set()
            await finish.wait()
            return self.receipt
        self.router.prepare_recovery.side_effect = snapshot
        pending = asyncio.create_task(self.service.dispatch(self.request()))
        await asyncio.wait_for(entered.wait(), 2)
        try:
            with self.assertRaises(VoiceError) as error:
                await self.service.dispatch(self.request())
            self.assertEqual(error.exception.code, 'FREE_AI_DELIVERY_PENDING')
            self.assertEqual(self.router.prepare_recovery.await_count, 1)
        finally:
            finish.set()
            await pending
        self.service.delivery.prepared = None
        with self.assertRaises(VoiceError) as error:
            await self.service.dispatch(self.request())
        self.assertEqual(error.exception.code, 'FREE_AI_DELIVERY_PENDING')
        self.assertEqual(self.router.prepare_recovery.await_count, 1)

    async def test_pending_reconnect_or_cleanup_rejects_without_starting_or_canceling(self):
        for field in ('reconnect_task','provider_cleanup'):
            self.service.delivery=DeliveryCoordinator(self.service)
            pending = asyncio.create_task(asyncio.sleep(20))
            setattr(self.service,field,pending)
            try:
                self.assertRejected(await self.service.dispatch(self.request()))
                self.assertFalse(self.service.delivery.closed)
                self.assertFalse(pending.cancelled())
            finally:
                pending.cancel();await asyncio.gather(pending,return_exceptions=True)
                setattr(self.service,field,None)
        self.service.delivery.closed = True
        with self.assertRaises(VoiceError):await self.service.start_voice(audio=False)
        with self.assertRaises(VoiceError):await self.service._start_voice_attempt(audio=False)

    async def test_old_nonterminal_task_is_not_hidden_by_large_completed_history(self):
        old,_=self.service.store.create('old',{'objective':'old','summary':'old'},str(self.root),'typed','old')
        now=time.time()
        self.service.store.db.executemany('INSERT INTO tasks VALUES(?,?,?,?,?,?)',
            [(f'complete-{n}',f'complete-{n}','0'*64,'completed',json.dumps({'id':f'complete-{n}','state':'completed'}),now+n) for n in range(10000)])
        self.assertEqual([task['id'] for task in self.service.store.active()],[old['id']])
        self.assertRejected(await self.service.dispatch(self.request()))
        self.assertFalse(self.service.delivery.closed)

    async def test_deferred_background_agent_reservation_prevents_preparation(self):
        entered,finish=asyncio.Event(),asyncio.Event()
        async def tell(*args,**kwargs):
            entered.set();await finish.wait();return {'status':'sent'}
        self.service.desktop=Mock(tell=AsyncMock(side_effect=tell))
        self.service.free_seat=AsyncMock(return_value='web-1')
        self.service.show_caption=AsyncMock()
        self.service.watch_agent=Mock()
        action=asyncio.create_task(self.service.agent_action({'kind':'web_task','text':'Synthetic web request'}, {'source':'Synthetic web request'}))
        await asyncio.wait_for(entered.wait(),2)
        try:
            self.assertFalse(self.service.jobs)
            self.assertRejected(await self.service.dispatch(self.request()))
            self.assertFalse(self.service.delivery.closed)
            self.assertFalse(action.cancelled())
        finally:
            finish.set();await action
        self.assertEqual(self.service.jobs['web-1']['state'],'working')
        self.assertFalse(self.service.action_work)

    async def test_inherited_sessions_and_custom_router_fail_before_closure(self):
        with patch('maslow_voice.free_ai_delivery.no_agent_sessions',side_effect=VoiceError('FREE_AI_PREPARATION_BUSY','busy')):
            self.assertRejected(await self.service.dispatch(self.request()),'agent-sessions')
        self.service._free_ai.assert_not_called()
        self.assertFalse(self.service.delivery.closed)
        with patch.dict(os.environ,{'XDG_STATE_HOME':str(self.root/'custom-state')}):
            with self.assertRaises(VoiceError) as error:await self.service.dispatch(self.request())
        self.assertEqual(error.exception.code,'FREE_AI_CANONICAL_STATE_REQUIRED')
        self.service._free_ai.assert_not_called()
        self.assertFalse((self.root/'custom-state').exists())
        self.router.state.directory=self.root/'different-router'
        self.service.delivery=DeliveryCoordinator(self.service)
        with self.assertRaises(VoiceError) as error:await self.service.dispatch(self.request())
        self.assertEqual(error.exception.code,'FREE_AI_CANONICAL_STATE_REQUIRED')
        self.assertFalse(self.service.delivery.closed)

    async def test_constructor_barrier_precedes_state_creation(self):
        with patch('maslow_voice.free_ai_delivery.barrier_present',return_value=True):
            with self.assertRaises(VoiceError):VoiceService(self.root/'untouched-state',self.root/'untouched-runtime')
        self.assertFalse((self.root/'untouched-state').exists())
        self.assertFalse((self.root/'untouched-runtime').exists())

    async def test_backup_failure_stays_closed_and_never_returns_success(self):
        self.router.prepare_recovery.side_effect=FreeAIError('RECOVERY_SNAPSHOT_FAILED','Backup failed')
        with self.assertRaises(VoiceError) as error:await self.service.dispatch(self.request())
        self.assertEqual(error.exception.code,'RECOVERY_SNAPSHOT_FAILED')
        self.assertTrue(self.service.delivery.closed)
        self.assertIsNone(self.service.delivery.prepared)
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request('check'))

    async def test_check_revalidates_key_pair_and_detects_restarted_router(self):
        await self.service.dispatch(self.request())
        self.router.process=object()
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request('check'))
        self.router.process=None
        self.router.recovery.verify.side_effect=FreeAIError('KEYRING_LOCKED','Locked')
        with self.assertRaises(VoiceError) as error:await self.service.dispatch(self.request('check'))
        self.assertEqual(error.exception.code,'KEYRING_LOCKED')
        self.assertTrue(self.service.delivery.closed)

    async def test_changed_ticket_and_unowned_idle_coordinator_fail_closed(self):
        self.service.hermes.clients['inherited']=object()
        self.assertRejected(await self.service.dispatch(self.request()),'inherited-coordinator')
        self.assertFalse(self.service.delivery.closed)
        self.service.hermes.clients.clear()
        self.service.delivery=DeliveryCoordinator(self.service)
        await self.service.dispatch(self.request())
        self.ticket['sourceCommit']='f'*40
        # Deepcopy isolates root ticket from the retained in-memory record.
        changed=copy.deepcopy(self.ticket)
        changed['nonce']='e'*64
        with patch('maslow_voice.free_ai_delivery.read_ticket',return_value=changed):
            with self.assertRaises(VoiceError):await self.service.dispatch(self.request('check'))

    async def test_rejected_ticket_stays_rejected_when_idle_and_receipt_is_not_mutable_authority(self):
        self.service.provider=object()
        result=await self.service.dispatch(self.request());expected=copy.deepcopy(result)
        self.assertRejected(result)
        result['result']['rejection']['continuationPending']=True
        self.service.provider=None
        self.assertEqual(expected,await self.service.dispatch(self.request()))
        self.service.delivery.admit_tasks();self.service.delivery.admit_control({'action':'start_voice'})
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request('check'))
        self.service._free_ai.assert_not_called()

    async def test_existing_router_owner_rejects_before_backend_construction(self):
        self.service.free_ai_router=self.router;self.router.owners={'synthetic owner'}
        self.assertRejected(await self.service.dispatch(self.request()),'router-work')
        self.assertEqual(self.router.owners,{'synthetic owner'})

    async def test_changed_same_transaction_denies_but_new_current_operation_can_replace_latch(self):
        self.service.provider=object();await self.service.dispatch(self.request())
        self.ticket['sourceCommit']='e'*40
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request())
        self.ticket.update(transactionId='f'*32,nonce='b'*64)
        request=self.request()|{'transactionId':self.ticket['transactionId'],'nonce':self.ticket['nonce']}
        result=await self.service.dispatch(request);self.assertRejected(result)
        self.assertEqual(result['result']['rejection']['transactionId'],'f'*32)
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request())

    async def test_expired_or_replaced_public_ticket_does_not_create_or_replay_positive(self):
        self.service.provider=object()
        expired=self.ticket|{'expiresAt':int(time.time())-1}
        changed=self.ticket|{'nonce':'e'*64}
        for value in (expired,changed):
            with patch('maslow_voice.free_ai_delivery._protected_ticket',side_effect=[copy.deepcopy(self.ticket),value]),self.assertRaises(VoiceError):
                await self.service.dispatch(self.request())
            self.assertIsNone(self.service.delivery.rejected)
        await self.service.dispatch(self.request())
        self.ticket.update(expired)
        with self.assertRaises(VoiceError):await self.service.dispatch(self.request())
        self.service._free_ai.assert_not_called()

    async def test_corrupt_task_state_and_postclosure_busy_are_not_positive_rejection(self):
        self.service.provider=object()
        with patch.object(self.service.store,'active',side_effect=sqlite3.DatabaseError('synthetic corrupt')),self.assertRaises(sqlite3.DatabaseError):
            await self.service.dispatch(self.request())
        self.assertIsNone(self.service.delivery.rejected);self.assertFalse(self.service.delivery.closed)
        self.service.provider=None
        self.router.prepare_recovery.side_effect=FreeAIError('FREE_AI_PREPARATION_BUSY','after closure')
        with self.assertRaises(VoiceError) as error:await self.service.dispatch(self.request())
        self.assertEqual(error.exception.code,'FREE_AI_PREPARATION_BUSY')
        self.assertTrue(self.service.delivery.closed);self.assertIsNone(self.service.delivery.rejected)

    async def test_two_actual_ipc_connections_and_disconnect_cannot_prepare_rejected_ticket(self):
        control=ControlServer(self.root/'rejection.sock',self.service.dispatch,lambda:{})
        original_send=control.send
        rejected,sending,release=asyncio.Event(),asyncio.Event(),asyncio.Event()
        async def gated_send(writer,value):
            if not sending.is_set():
                sending.set();rejected.set();await release.wait()
            await original_send(writer,value)
        control.send=gated_send
        await control.start();clients=[]
        try:
            first_reader,first=await asyncio.open_unix_connection(str(control.path));clients.append(first)
            self.service.provider=object()
            first.write(json.dumps(self.request()).encode()+b'\n');await first.drain()
            await asyncio.wait_for(rejected.wait(),2)
            expected=copy.deepcopy(self.service.delivery.rejected['receipt'])
            first.close();await first.wait_closed()  # no reply was delivered
            self.service.provider=None
            reader,second=await asyncio.open_unix_connection(str(control.path));clients.append(second)
            second.write(json.dumps(self.request()).encode()+b'\n');await second.drain()
            result=json.loads(await asyncio.wait_for(reader.readline(),2))
            self.assertIs(result['ok'],True);self.assertEqual(result['result']['rejection'],expected)
            self.assertRejected(result);self.assertIsNone(self.service.delivery.prepared)
            release.set();await asyncio.wait_for(asyncio.gather(*tuple(control.requests)),2)
            self.assertFalse(control.requests)
        finally:
            release.set()
            for writer in clients:writer.close();await writer.wait_closed()
            await control.close()

    async def test_actual_disconnect_after_closure_keeps_preparation_pending(self):
        entered,release=asyncio.Event(),asyncio.Event()
        async def snapshot(*args,**kwargs):
            entered.set();await release.wait();return self.receipt
        self.router.prepare_recovery.side_effect=snapshot
        control=ControlServer(self.root/'pending.sock',self.service.dispatch,lambda:{})
        await control.start();clients=[]
        try:
            _,first=await asyncio.open_unix_connection(str(control.path));clients.append(first)
            first.write(json.dumps(self.request()).encode()+b'\n');await first.drain()
            await asyncio.wait_for(entered.wait(),2)
            first.close();await first.wait_closed()
            reader,second=await asyncio.open_unix_connection(str(control.path));clients.append(second)
            second.write(json.dumps(self.request()).encode()+b'\n');await second.drain()
            response=json.loads(await asyncio.wait_for(reader.readline(),2))
            self.assertIs(response['ok'],False);self.assertEqual(response['error']['code'],'FREE_AI_DELIVERY_PENDING')
            self.assertTrue(self.service.delivery.closed);self.assertIsNone(self.service.delivery.rejected)
            self.assertEqual(self.router.prepare_recovery.await_count,1)
            release.set();await asyncio.wait_for(asyncio.gather(*tuple(control.requests)),2)
            self.assertIsNotNone(self.service.delivery.prepared)
        finally:
            release.set()
            for writer in clients:writer.close();await writer.wait_closed()
            await control.close()
