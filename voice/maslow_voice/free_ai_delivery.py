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


class DeliveryCoordinator:
    def __init__(self, service):
        self.service = service
        self.closed = False
        self.prepared = None

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
