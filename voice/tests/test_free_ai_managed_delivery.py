"""Lifecycle2 parser/capability/quiescence only; no installed acceptance."""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice import free_ai_delivery as delivery
from maslow_voice.errors import VoiceError

TX, NONCE = 'a'*32,'b'*64


def ticket(remove=True):
    pair = {'maslow-free-ai':{'version':'0.1.0-2','sha256':'c'*64,'sourceCommit':delivery.MANAGED_SOURCE},
            'maslow-voice':{'version':'0.1.5-40','sha256':'d'*64,'sourceCommit':'e'*40}}
    verifier = {'policy':1,'sha256':delivery.MANAGED_POLICY,'sourceCommit':delivery.MANAGED_SOURCE,'artifacts':copy.deepcopy(pair)}
    if not remove:verifier['originGeneration']='f'*32
    return {'schema':2,'action':'free-ai-remove' if remove else 'free-ai-reinstall','transactionId':TX,'nonce':NONCE,
            'uid':os.getuid(),'expiresAt':int(time.time())+900,
            'packagesBefore':copy.deepcopy(pair) if remove else {'maslow-voice':copy.deepcopy(pair['maslow-voice'])},
            'packagesAfter':{'maslow-voice':copy.deepcopy(pair['maslow-voice'])} if remove else copy.deepcopy(pair),
            'verifier':verifier,'checkpoint':{'id':TX,'nonce_sha256':hashlib.sha256(NONCE.encode()).hexdigest()},
            'preservation':{'generation':TX if remove else 'f'*32,'anchorSha256':None if remove else '1'*64}}


class ManagedTicketTests(unittest.TestCase):
    def test_exact_two_purposes_and_new_checkpoint_validate(self):
        for remove in (True,False):
            value=ticket(remove)
            with patch.object(delivery,'_protected_ticket',return_value=value):
                self.assertEqual(value,delivery.read_managed_ticket(TX,NONCE))
                with self.assertRaises(VoiceError):delivery.read_ticket(TX,NONCE)

    def test_bool_expiry_uid_unknown_fields_source_old_voice_and_replay_refuse(self):
        for changed in ({'schema':True},{'uid':True},{'uid':os.getuid()+1},{'expiresAt':True},{'expiresAt':int(time.time())-1},
                        {'expiresAt':int(time.time())+1000},{'snapshotId':'old'},{'packagesBefore':{}},{'action':'free-ai-recover'},
                        {'checkpoint':{'id':'f'*32,'nonce_sha256':'0'*64}}):
            with patch.object(delivery,'_protected_ticket',return_value=ticket()|changed),self.assertRaises(VoiceError):
                delivery.read_managed_ticket(TX,NONCE)
        for remove in (True,False):
            value=ticket(remove);value['verifier']['sourceCommit']='0'*40
            with patch.object(delivery,'_protected_ticket',return_value=value),self.assertRaises(VoiceError):delivery.read_managed_ticket(TX,NONCE)
        value=ticket()
        for records in (value['packagesBefore'],value['packagesAfter'],value['verifier']['artifacts']):records['maslow-voice']['version']='0.1.5-39'
        with patch.object(delivery,'_protected_ticket',return_value=value),self.assertRaises(VoiceError):delivery.read_managed_ticket(TX,NONCE)

    def test_actual_user_owned_or_symlink_marker_does_not_supply_capability(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker=Path(temporary)/'marker.json';marker.write_text('{}');marker.chmod(0o644)
            with patch.object(delivery,'MANAGED_MARKER',marker),self.assertRaises(VoiceError):delivery.managed_capability(ticket())
            marker.unlink();marker.symlink_to(Path(temporary)/'missing')
            with patch.object(delivery,'MANAGED_MARKER',marker),self.assertRaises(VoiceError):delivery.managed_capability(ticket())

    def test_package_version_source_code_and_ownership_queries_bind_capability(self):
        code=b'synthetic reviewed package module'
        marker={'schema':1,'package':'maslow-voice','version':'0.1.5-40','sourceCommit':'e'*40,
                'managedLifecycle':2,'freeAiDeliverySha256':hashlib.sha256(code).hexdigest()}
        def files(path,maximum):return json.dumps(marker).encode() if path==delivery.MANAGED_MARKER else code
        def query(argv,**kwargs):
            self.assertEqual(2,kwargs['timeout'])
            return subprocess.CompletedProcess(argv,0,'maslow-voice 0.1.5-40\n' if argv[1]=='-Q' else 'maslow-voice\n','')
        with patch.object(delivery,'_managed_file',side_effect=files),patch.object(delivery,'__file__',str(delivery.MANAGED_MODULE)),patch.object(delivery.subprocess,'run',side_effect=query) as run:
            delivery.managed_capability(ticket())
            self.assertEqual(3,run.call_count)
            for field,bad in (('schema',True),('managedLifecycle',True),('version','0.1.5-39'),('sourceCommit','0'*40),('freeAiDeliverySha256','0'*64),('callerCapability',2)):
                original=copy.deepcopy(marker);marker[field]=bad
                with self.subTest(field=field),self.assertRaises(VoiceError):delivery.managed_capability(ticket())
                marker.clear();marker.update(original)
            for response in (subprocess.CompletedProcess([],0,'maslow-voice 0.1.5-39\n',''),
                             subprocess.CompletedProcess([],0,'other-package\n',''),subprocess.CompletedProcess([],1,'','SECRET')):
                with patch.object(delivery.subprocess,'run',return_value=response),self.assertRaises(VoiceError) as error:delivery.managed_capability(ticket())
                self.assertNotIn('SECRET',error.exception.message)


def service():
    return SimpleNamespace(provider=None,preview_task=None,startup_task=None,conversation_requests=set(),control_requests=set(),
        configuration_lock=asyncio.Lock(),lifecycle_lock=asyncio.Lock(),action_lock=asyncio.Lock(),action_work={},
        reconnect_task=None,provider_cleanup=None,store=SimpleNamespace(active=lambda:[]),
        tasks=SimpleNamespace(assistant_reservations=set(),monitors={}),agent_jobs=set(),jobs={},
        hermes=SimpleNamespace(clients={},processes={}),offline=None,offline_clients={},free_ai_router=None,
        _free_ai=Mock(side_effect=AssertionError('absent backend import')))


class ManagedQuiescenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service=service();self.coordinator=delivery.DeliveryCoordinator(self.service);self.ticket=ticket(False)
        for p in (patch.object(delivery,'read_managed_ticket',side_effect=lambda *args:copy.deepcopy(self.ticket)),
                  patch.object(delivery,'managed_capability'),patch.object(delivery,'canonical_service'),patch.object(delivery,'no_agent_sessions')):
            p.start();self.addCleanup(p.stop)

    def request(self,operation='quiesce'):
        return {'action':'free_ai_delivery','schema':2,'operation':operation,'transactionId':TX,'nonce':NONCE}

    async def test_absent_backend_quiesces_without_import_snapshot_key_or_initialization(self):
        result=(await self.coordinator.handle(self.request()))['result']
        self.assertEqual(2,result['schema']);self.assertTrue(result['admissionClosed']);self.assertTrue(result['ownedRouterStopped'])
        self.assertNotIn('recoveryReceipt',result);self.assertNotIn('checkpoint',result)
        self.service._free_ai.assert_not_called()
        self.assertEqual(result,(await self.coordinator.handle(self.request('check')))['result'])
        with self.assertRaises(VoiceError):self.coordinator.admit_tasks()
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request())

    async def test_active_conversation_jobs_tasks_configuration_and_reservations_do_not_close(self):
        changes=(('provider',object()),('conversation_requests',{'active'}),('agent_jobs',{'active'}),('jobs',{'j':{'state':'running'}}),('action_work',{'active':True}))
        for field,bad in changes:
            previous=getattr(self.service,field);setattr(self.service,field,bad)
            with self.subTest(field=field),self.assertRaises(VoiceError):await self.coordinator.handle(self.request())
            self.assertFalse(self.coordinator.closed);setattr(self.service,field,previous)
        self.service.tasks.assistant_reservations.add('active')
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request())
        self.assertFalse(self.coordinator.closed);self.service.tasks.assistant_reservations.clear()
        await self.service.configuration_lock.acquire()
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request())
        self.assertFalse(self.coordinator.closed)

    async def test_inherited_coordinator_or_router_when_backend_absent_refuse(self):
        self.service.hermes.clients['inherited']=object()
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request())
        self.assertFalse(self.coordinator.closed);self.service.hermes.clients.clear()
        self.service.free_ai_router=object()
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request())
        self.assertFalse(self.coordinator.closed)

    async def test_remove_stops_only_existing_owned_idle_router_without_snapshot(self):
        self.ticket=ticket(True)
        router=SimpleNamespace(lock=asyncio.Lock(),owners=set(),admission=True,idle_stop=None,process=None,
            _stop=AsyncMock(),prepare_recovery=AsyncMock(),recovery=Mock())
        self.service.free_ai_router=router
        result=await self.coordinator.handle(self.request())
        router._stop.assert_awaited_once();router.prepare_recovery.assert_not_called();self.service._free_ai.assert_not_called()
        self.assertFalse(router.admission);self.assertTrue(result['result']['ownedRouterStopped'])
        router.process=object()
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request('check'))

    async def test_shutdown_failure_or_surviving_owned_group_keeps_admission_closed(self):
        self.ticket=ticket(True)
        router=SimpleNamespace(lock=asyncio.Lock(),owners=set(),admission=True,idle_stop=None,process=SimpleNamespace(pid=123),
            _stop=AsyncMock(side_effect=OSError('SECRET')))
        self.service.free_ai_router=router
        with self.assertRaises(VoiceError) as error:await self.coordinator.handle(self.request())
        self.assertNotIn('SECRET',error.exception.message);self.assertTrue(self.coordinator.closed)
        self.coordinator=delivery.DeliveryCoordinator(self.service);router._stop=AsyncMock()
        with patch.object(delivery.os,'killpg',return_value=None),self.assertRaises(VoiceError):await self.coordinator.handle(self.request())
        self.assertTrue(self.coordinator.closed)

    async def test_checked_ticket_change_and_unknown_request_never_admit(self):
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request()|{'snapshotId':'old'})
        self.assertFalse(self.coordinator.closed)
        await self.coordinator.handle(self.request())
        self.ticket['nonce']='0'*64
        with self.assertRaises(VoiceError):await self.coordinator.handle(self.request('check'))


if __name__=='__main__':unittest.main()
