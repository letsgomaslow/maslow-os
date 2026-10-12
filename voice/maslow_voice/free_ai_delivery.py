"""Root-ticket-bound quiescence; never privileged installation authorization."""

import copy
import json
import hashlib
import os
from pathlib import Path
import re
import pwd
import stat
import subprocess
import time

from .errors import VoiceError

TICKET_ROOT = Path('/run/maslow-hub-free-ai')
NAMES = {'maslow-free-ai', 'maslow-voice'}
MANAGED_SOURCE = 'c2b03842a81645998a79cbca525c03ddf67813b4'
MANAGED_POLICY = '49415ed44255c32e06e8815fb2b5374b821bf31484f40336559dfda81bbcfca5'
MANAGED_MARKER = Path('/usr/share/maslow-voice/free-ai-lifecycle.json')
MANAGED_MODULE = Path('/usr/lib/maslow-voice/maslow_voice/free_ai_delivery.py')


def _unique(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def ticket_path():
    return TICKET_ROOT / str(os.getuid()) / 'ticket.json'


def barrier_present():
    path = ticket_path()
    return path.exists() or path.is_symlink()


def startup_check():
    if barrier_present():
        raise VoiceError('FREE_AI_DELIVERY_PENDING', 'Voice is paused for the pending Free cloud AI package operation. Finish or recover it through Hub.')


def _protected_ticket(path):
    for item in (path,*path.parents):
        info = item.lstat()
        if item.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError()
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) != 0o644 or before.st_size > 16384:
        raise ValueError()
    fd = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev,opened.st_ino) != (before.st_dev,before.st_ino):
            raise ValueError()
        data = os.read(fd,16385)
        after = os.fstat(fd)
        if len(data)>16384 or (before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError()
        return json.loads(data,object_pairs_hook=_unique)
    finally:
        os.close(fd)


def _artifacts(value, *, target):
    if not isinstance(value,dict) or (set(value) != NAMES if target else not value or not set(value) <= NAMES):
        raise ValueError()
    for record in value.values():
        if not isinstance(record,dict) or set(record) != {'version','sha256'} or not isinstance(record['version'],str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-[1-9][0-9]*',record['version']) or not isinstance(record['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',record['sha256']):
            raise ValueError()


def read_ticket(transaction,nonce):
    try:
        if not isinstance(transaction,str) or not re.fullmatch(r'[a-f0-9]{32}',transaction) or not isinstance(nonce,str) or not re.fullmatch(r'[a-f0-9]{64}',nonce):
            raise ValueError()
        value = _protected_ticket(ticket_path())
        if not isinstance(value,dict) or set(value) != {'schema','action','transactionId','nonce','uid','expiresAt','sourceCommit','targetArtifacts','previousArtifacts'}:
            raise ValueError()
        if type(value['schema']) is not int or value['schema'] != 1 or value['action'] != 'free-ai-install' or value['transactionId'] != transaction or value['nonce'] != nonce or type(value['uid']) is not int or value['uid'] <= 0 or value['uid'] != os.getuid():
            raise ValueError()
        if type(value['expiresAt']) is not int or not 0 < value['expiresAt'] - time.time() <= 900 or not isinstance(value['sourceCommit'],str) or not re.fullmatch(r'[a-f0-9]{40}',value['sourceCommit']):
            raise ValueError()
        _artifacts(value['targetArtifacts'],target=True)
        _artifacts(value['previousArtifacts'],target=False)
        if 'maslow-voice' not in value['previousArtifacts']:
            raise ValueError()
        return value
    except (OSError,ValueError,KeyError,TypeError):
        raise VoiceError('FREE_AI_TICKET_INVALID','The fixed root package ticket is missing, expired or invalid. No package operation was authorized.') from None


def canonical_paths():
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    return home / '.local/state/maslow-voice', Path('/run/user') / str(os.getuid()) / 'maslow-voice'


def canonical_environment():
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    expected = {'HOME':str(home), 'XDG_STATE_HOME':str(home / '.local/state'),
                'XDG_RUNTIME_DIR':str(Path('/run/user') / str(os.getuid()))}
    if any(os.environ.get(key) and os.environ[key] != value for key,value in expected.items()) or os.environ.get('TMUX_TMPDIR') not in {None,'','/tmp'}:
        raise VoiceError('FREE_AI_CANONICAL_STATE_REQUIRED','Custom state or agent-session locations were left unchanged. Review them before package changes.')


def canonical_service(service):
    canonical_environment()
    directory, runtime = canonical_paths()
    if (service.directory != directory or service.runtime != runtime
            or any(item.is_symlink() for path in (directory,runtime) for item in (path,*path.parents))):
        raise VoiceError('FREE_AI_CANONICAL_STATE_REQUIRED','This installation needs the standard Maslow state and session locations. Custom or developer configurations were left unchanged.')


def no_agent_sessions():
    """Bounded synchronous read before closure, so BUSY changes no admission.

    This is metadata only on Voice's fixed private tmux server. It never types,
    closes a session or treats a generic command error as proof of no work.
    """
    if os.environ.get('TMUX_TMPDIR') not in {None,'','/tmp'}:
        raise VoiceError('FREE_AI_CANONICAL_STATE_REQUIRED','Custom agent-session locations need review before package changes.')
    expected = f"/tmp/tmux-{os.getuid()}/maslow-voice"
    try:
        result = subprocess.run(['/usr/bin/tmux','-L','maslow-voice','list-sessions','-F','#{session_id}'],
            capture_output=True,text=True,timeout=2,env={'PATH':'/usr/bin:/bin','LANG':'C'},cwd='/')
        missing = {f"error connecting to {expected} (No such file or directory)", f"no server running on {expected}"}
        if result.returncode != 1 or result.stdout.strip() or result.stderr.strip() not in missing:
            raise ValueError()
    except (OSError,ValueError,subprocess.TimeoutExpired):
        raise VoiceError('FREE_AI_PREPARATION_BUSY','Existing Voice agent sessions could not be proven idle. No preparation started.') from None


def operation_binding(ticket):
    return {'schema':1,'transactionId':ticket['transactionId'],
            'nonce_sha256':hashlib.sha256(ticket['nonce'].encode('ascii')).hexdigest()}


def process_start():
    # comm may contain spaces/parentheses; parse after its closing delimiter.
    return Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]


def _managed_hex(value, size):
    return isinstance(value,str) and re.fullmatch(r'[a-f0-9]{' + str(size) + '}',value) is not None


def _managed_artifacts(value, names):
    if not isinstance(value,dict) or set(value) != names:
        raise ValueError()
    for record in value.values():
        if (not isinstance(record,dict) or set(record) != {'version','sha256','sourceCommit'}
                or not isinstance(record['version'],str) or len(record['version']) > 64
                or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-[1-9][0-9]*',record['version'])
                or not _managed_hex(record['sha256'],64) or not _managed_hex(record['sourceCommit'],40)):
            raise ValueError()


def read_managed_ticket(transaction, nonce):
    """Separate V2 parser: never widen/relabel V1 installed-before evidence."""
    try:
        value = _protected_ticket(ticket_path())
        fields = {'schema','action','transactionId','nonce','uid','expiresAt','packagesBefore','packagesAfter','verifier','checkpoint','preservation'}
        if (not _managed_hex(transaction,32) or not _managed_hex(nonce,64) or not isinstance(value,dict) or set(value) != fields
                or type(value['schema']) is not int or value['schema'] != 2
                or value['action'] not in {'free-ai-remove','free-ai-reinstall'}
                or value['transactionId'] != transaction or value['nonce'] != nonce
                or type(value['uid']) is not int or not 0 < value['uid'] < 2 ** 32 or value['uid'] != os.getuid()
                or type(value['expiresAt']) is not int or not 0 < value['expiresAt'] - time.time() <= 900):
            raise ValueError()
        remove = value['action'] == 'free-ai-remove'
        before,after,verifier = value['packagesBefore'],value['packagesAfter'],value['verifier']
        _managed_artifacts(before,NAMES if remove else {'maslow-voice'})
        _managed_artifacts(after,{'maslow-voice'} if remove else NAMES)
        vf = {'policy','sha256','sourceCommit','artifacts'} | (set() if remove else {'originGeneration'})
        if (not isinstance(verifier,dict) or set(verifier) != vf or type(verifier['policy']) is not int
                or verifier['policy'] != 1 or verifier['sha256'] != MANAGED_POLICY or verifier['sourceCommit'] != MANAGED_SOURCE):
            raise ValueError()
        _managed_artifacts(verifier['artifacts'],NAMES)
        pair = verifier['artifacts']
        if (pair != (before if remove else after) or before['maslow-voice'] != after['maslow-voice']
                or pair['maslow-free-ai']['version'] != '0.1.0-2' or pair['maslow-free-ai']['sourceCommit'] != MANAGED_SOURCE
                or tuple(map(int,re.split(r'[.-]',pair['maslow-voice']['version']))) < (0,1,5,40)):
            raise ValueError()
        checkpoint,preserved = value['checkpoint'],value['preservation']
        if (not isinstance(checkpoint,dict) or set(checkpoint) != {'id','nonce_sha256'}
                or checkpoint != {'id':transaction,'nonce_sha256':hashlib.sha256(nonce.encode('ascii')).hexdigest()}
                or not isinstance(preserved,dict) or set(preserved) != {'generation','anchorSha256'}
                or not _managed_hex(preserved['generation'],32)):
            raise ValueError()
        if remove:
            if preserved != {'generation':transaction,'anchorSha256':None}:
                raise ValueError()
        elif (not _managed_hex(preserved['anchorSha256'],64) or preserved['generation'] == transaction
                or verifier['originGeneration'] != preserved['generation']):
            raise ValueError()
        return value
    except (OSError,ValueError,KeyError,TypeError):
        raise VoiceError('FREE_AI_MANAGED_TICKET_INVALID','The current managed lifecycle ticket could not be verified.') from None


def _managed_file(path, maximum):
    fd = os.open('/',os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not path.is_absolute() or '..' in path.parts or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError()
        for part in path.parts[1:-1]:
            child = os.open(part,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
            info = os.fstat(fd)
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError()
        target = os.open(path.name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=fd)
        try:
            info = os.fstat(target)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o644 or not 1 <= info.st_size <= maximum:
                raise ValueError()
            with os.fdopen(target,'rb',closefd=False) as stream:
                raw = stream.read(maximum+1)
            after = os.fstat(target)
            if len(raw) != info.st_size or (info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink) != (after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_nlink):
                raise ValueError()
            return raw
        finally:
            os.close(target)
    finally:
        os.close(fd)


def managed_capability(ticket):
    """Actual protected package marker/version/code, not a caller capability."""
    try:
        value = json.loads(_managed_file(MANAGED_MARKER,4096),object_pairs_hook=_unique)
        fields = {'schema','package','version','sourceCommit','managedLifecycle','freeAiDeliverySha256'}
        voice = ticket['packagesBefore']['maslow-voice']
        if (not isinstance(value,dict) or set(value) != fields or type(value['schema']) is not int or value['schema'] != 1
                or value['package'] != 'maslow-voice' or type(value['managedLifecycle']) is not int or value['managedLifecycle'] != 2
                or value['version'] != voice['version'] or value['sourceCommit'] != voice['sourceCommit']
                or not _managed_hex(value['freeAiDeliverySha256'],64) or Path(__file__) != MANAGED_MODULE
                or hashlib.sha256(_managed_file(MANAGED_MODULE,128*1024)).hexdigest() != value['freeAiDeliverySha256']):
            raise ValueError()
        for argv, expected in ((['/usr/bin/pacman','-Q','maslow-voice'],f"maslow-voice {value['version']}\n"),
                (['/usr/bin/pacman','-Qqo',str(MANAGED_MARKER)],'maslow-voice\n'),
                (['/usr/bin/pacman','-Qqo',str(MANAGED_MODULE)],'maslow-voice\n')):
            result = subprocess.run(argv,capture_output=True,text=True,timeout=2,env={'PATH':'/usr/bin:/bin','LANG':'C'},cwd='/')
            if result.returncode or result.stdout != expected or result.stderr:
                raise ValueError()
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired):
        raise VoiceError('FREE_AI_MANAGED_CAPABILITY_UNAVAILABLE','This installed Voice package has no verified managed lifecycle capability.') from None


class DeliveryCoordinator:
    def __init__(self, service):
        self.service = service
        self.closed = False
        self.prepared = None
        self.managed_prepared = None

    def admit_tasks(self):
        if self.closed:
            raise VoiceError('FREE_AI_DELIVERY_PENDING','Finish the pending Free cloud AI package operation before starting new work.')

    def admit_control(self, request):
        if not self.closed:
            return
        if request.get('action') in {'status','end_voice','stop_gemini_voice_preview','silence','mute','free_ai_delivery'}:
            return
        raise VoiceError('FREE_AI_DELIVERY_PENDING','Voice work and configuration are paused for the pending package operation.')

    def idle(self, *, initial=False):
        service = self.service
        if (service.provider is not None or service.preview_task is not None or service.startup_task is not None
                or service.conversation_requests or service.control_requests or service.configuration_lock.locked()
                or service.lifecycle_lock.locked() or service.action_lock.locked() or service.action_work
                or (service.reconnect_task and not service.reconnect_task.done())
                or (service.provider_cleanup and not service.provider_cleanup.done()) or service.store.active() or service.tasks.assistant_reservations
                or any(not worker.done() for worker in service.tasks.monitors.values()) or service.agent_jobs
                or any(job.get('state') not in {'finished','closed'} for job in service.jobs.values())):
            raise VoiceError('FREE_AI_PREPARATION_BUSY' if initial else 'FREE_AI_WORK_ACTIVE','Finish active Voice conversations, tasks and agent jobs before installing components. No work was cancelled.')

    async def handle(self, request):
        if type(request.get('schema')) is int and request.get('schema') == 2:
            return await self.handle_managed(request)
        if set(request) != {'action','operation','transactionId','nonce'} or request.get('operation') not in {'prepare','check'}:
            raise VoiceError('INVALID_REQUEST','Choose the fixed package preparation or verification operation.')
        ticket = read_ticket(request['transactionId'],request['nonce'])
        canonical_service(self.service)
        if request['operation'] == 'check':
            try:
                return {'result':await self.check(ticket)}
            except VoiceError:
                raise
            except Exception as error:
                from maslow_free_ai.errors import FreeAIError
                if isinstance(error,FreeAIError):
                    raise VoiceError(error.code,error.message) from None
                raise VoiceError('FREE_AI_VERIFICATION_FAILED','The stopped recovery record could not be verified. Admission remains closed.') from None
        if self.closed or self.prepared is not None:
            raise VoiceError('FREE_AI_DELIVERY_PENDING','Preparation has started for this operation. Verify or recover it rather than creating another snapshot.')
        self.idle(initial=True)
        if set(self.service.hermes.clients) - set(self.service.hermes.processes):
            raise VoiceError('FREE_AI_PREPARATION_BUSY','An inherited coordinator cannot be shut down safely. Review it before package changes. No preparation started.')
        if self.service.free_ai_router and self.service.free_ai_router.owners:
            raise VoiceError('FREE_AI_PREPARATION_BUSY','An assistant request still owns the router. No preparation started.')
        no_agent_sessions()
        router = self.service._free_ai()
        if not hasattr(router,'prepare_recovery'):
            raise VoiceError('FREE_AI_RECOVERY_UNAVAILABLE','The installed private runtime does not support paired recovery. No package operation was authorized.')
        voice_directory, _ = canonical_paths()
        if router.state.directory != voice_directory.parent / 'maslow-free-ai':
            raise VoiceError('FREE_AI_CANONICAL_STATE_REQUIRED','Custom router storage was left unchanged. Review it before package changes.')
        # No await between idle checks and closure. All new controls/tasks are
        # blocked before coordinator shutdown, keyring access or SQLite backup.
        self.closed = True
        try:
            from .coordinator import _terminate_hermes_process_group
            for process in tuple(self.service.hermes.processes.values()):
                if process.returncode is None:
                    await _terminate_hermes_process_group(process)
                try:
                    os.killpg(process.pid,0)
                except ProcessLookupError:
                    pass
                else:
                    raise VoiceError('FREE_AI_COORDINATOR_RUNNING','An owned coordinator has not stopped. Package changes are blocked.')
            self.service.hermes.clients.clear()
            self.service.hermes.processes.clear()
            if self.service.offline:
                await self.service.offline.stop()
                self.service.offline = None
                self.service.offline_clients.clear()
            artifacts = {name:record['sha256'] for name,record in ticket['previousArtifacts'].items()}
            receipt = await router.prepare_recovery(artifacts, reserved_id=ticket['transactionId'], operation=operation_binding(ticket))
            if receipt.get('id') != ticket['transactionId']:
                raise VoiceError('FREE_AI_RECOVERY_CHANGED','The snapshot identity differs from the reserved root operation.')
            self.prepared = {'ticket':copy.deepcopy(ticket),'receipt':copy.deepcopy(receipt)}
            return {'result':await self.check(ticket)}
        except VoiceError:
            raise
        except Exception as error:
            from maslow_free_ai.errors import FreeAIError
            if isinstance(error,FreeAIError):
                raise VoiceError(error.code,error.message) from None
            raise VoiceError('FREE_AI_PREPARATION_FAILED','Package preparation did not finish. Admission remains closed; recover through Hub.') from None

    async def check(self, ticket):
        if self.prepared is None or ticket != self.prepared['ticket'] or not self.closed:
            raise VoiceError('FREE_AI_NOT_PREPARED','This exact package operation has not been prepared.')
        self.idle()
        router = self.service._free_ai()
        if router.process is not None or router.owners or not router.recovery.pending():
            raise VoiceError('FREE_AI_NOT_QUIESCENT','The owned router or recovery state is not quiescent.')
        router.recovery.verify_operation(ticket['transactionId'],operation_binding(ticket))
        receipt = await router.recovery.verify(self.prepared['receipt']['id'],artifacts=self.prepared['receipt']['artifacts'])
        if receipt != self.prepared['receipt']:
            raise VoiceError('FREE_AI_RECOVERY_CHANGED','The recovery record changed after preparation.')
        return {'schema':1,'transactionId':ticket['transactionId'],'nonce':ticket['nonce'],'uid':os.getuid(),
            'daemonPid':os.getpid(),'daemonStart':process_start(),'admissionClosed':True,'activeTasks':0,
            'conversationActive':False,'agentJobsActive':False,'ownedRouterStopped':True,'recoveryReceipt':receipt}

    async def handle_managed(self, request):
        if (set(request) != {'action','schema','operation','transactionId','nonce'} or request.get('action') != 'free_ai_delivery'
                or request.get('operation') not in {'quiesce','check'}):
            raise VoiceError('INVALID_REQUEST','Choose the fixed managed quiescence or verification operation.')
        ticket = read_managed_ticket(request['transactionId'],request['nonce'])
        managed_capability(ticket)
        canonical_service(self.service)
        if request['operation'] == 'check':
            return {'result':self.managed_check(ticket)}
        if self.closed or self.prepared is not None or self.managed_prepared is not None:
            raise VoiceError('FREE_AI_DELIVERY_PENDING','An operation has already closed admission. Verify or recover it.')
        self.idle(initial=True)
        if set(self.service.hermes.clients) - set(self.service.hermes.processes):
            raise VoiceError('FREE_AI_PREPARATION_BUSY','An inherited coordinator cannot be shut down safely.')
        router = self.service.free_ai_router  # never lazily import/create an absent backend
        if ticket['action'] == 'free-ai-reinstall' and router is not None:
            raise VoiceError('FREE_AI_PREPARATION_BUSY','An absent backend still has router state in Voice.')
        if router is not None and (router.owners or router.lock.locked()):
            raise VoiceError('FREE_AI_PREPARATION_BUSY','The owned router still has active work.')
        no_agent_sessions()
        self.closed = True  # no await between idle proof and admission closure
        try:
            if self.service.hermes.processes:
                from .coordinator import _terminate_hermes_process_group
                for process in tuple(self.service.hermes.processes.values()):
                    if process.returncode is None:
                        await _terminate_hermes_process_group(process)
                    try:
                        os.killpg(process.pid,0)
                    except ProcessLookupError:
                        pass
                    else:
                        raise VoiceError('FREE_AI_COORDINATOR_RUNNING','An owned coordinator has not stopped.')
            self.service.hermes.clients.clear();self.service.hermes.processes.clear()
            if self.service.offline:
                await self.service.offline.stop()
                self.service.offline = None
                self.service.offline_clients.clear()
            if router is not None:
                async with router.lock:
                    if router.owners:
                        raise VoiceError('FREE_AI_PREPARATION_BUSY','The owned router acquired work before shutdown.')
                    router.admission = False
                    if router.idle_stop:
                        router.idle_stop.cancel();router.idle_stop = None
                    process = router.process
                    await router._stop()
                    if process is not None:
                        try:
                            os.killpg(process.pid,0)
                        except ProcessLookupError:
                            pass
                        else:
                            raise VoiceError('FREE_AI_NOT_QUIESCENT','An owned router process group remains.')
            self.managed_prepared = copy.deepcopy(ticket)
            return {'result':self.managed_check(ticket)}
        except VoiceError:
            raise
        except Exception:
            raise VoiceError('FREE_AI_PREPARATION_FAILED','Managed quiescence did not finish. Admission remains closed.') from None

    def managed_check(self, ticket):
        if not self.closed or self.managed_prepared != ticket:
            raise VoiceError('FREE_AI_NOT_PREPARED','This exact managed operation has not quiesced Voice.')
        self.idle()
        router = self.service.free_ai_router
        if router is not None and (router.process is not None or router.owners or router.admission):
            raise VoiceError('FREE_AI_NOT_QUIESCENT','The owned router is not stopped.')
        if self.service.hermes.processes or self.service.hermes.clients or self.service.offline is not None:
            raise VoiceError('FREE_AI_NOT_QUIESCENT','An owned coordinator is not stopped.')
        no_agent_sessions()
        return {'schema':2,'action':ticket['action'],'transactionId':ticket['transactionId'],'nonce':ticket['nonce'],'uid':os.getuid(),
                'daemonPid':os.getpid(),'daemonStart':process_start(),'admissionClosed':True,'activeTasks':0,
                'conversationActive':False,'agentJobsActive':False,'ownedRouterStopped':True}
