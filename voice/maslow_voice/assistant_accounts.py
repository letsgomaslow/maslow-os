"""Fixed read-only Connect IPC. No Composio credentials enter Voice or Hermes."""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import stat

from .assistant import POLICY_REVISION
from .errors import VoiceError

EXECUTABLE = Path('/usr/bin/maslow-connect')
MARKER = Path('/usr/share/maslow-connect/managed-accounts.json')
MAX_REPLY = 65536


def account_ids(value):
    if not isinstance(value,list) or len(value) > 4 or any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',x) for x in value) or len(set(value)) != len(value):
        raise VoiceError('INVALID_CAPABILITIES','Select each supported account only once, up to four accounts.')
    return sorted(value)


def _installed_file(path):
    for item in (path,*path.parents):
        info = item.lstat()
        if item.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError()
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError()


class AccountBridge:
    def available(self):
        try:
            _installed_file(EXECUTABLE)
            _installed_file(MARKER)
            if MARKER.stat().st_size > 4096:
                return False
            data=json.loads(MARKER.read_text())
            return set(data)=={'schema','policyRevision','operations','sourceRevision'} and data['schema']==1 and data['policyRevision']==POLICY_REVISION and data['operations']==['calendar.events.list'] and isinstance(data['sourceRevision'],str) and bool(re.fullmatch(r'[a-f0-9]{40}',data['sourceRevision']))
        except (OSError,ValueError,TypeError,KeyError):
            return False

    async def call(self, operation, value=None):
        if operation not in {'list','create','read','revoke'} or not self.available():
            raise VoiceError('MANAGED_ACCOUNTS_UNAVAILABLE','Scoped account access needs the accepted Connect package. No account was accessed.')
        payload=json.dumps(value or {}).encode()
        if len(payload)>4096:
            raise VoiceError('INVALID_CAPABILITIES','The account request is too large.')
        try:
            process=await asyncio.create_subprocess_exec(str(EXECUTABLE),'managed-accounts',operation,
                stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,
                limit=MAX_REPLY+1, start_new_session=True,
                env={key:os.environ[key] for key in ('HOME','XDG_STATE_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','LANG') if key in os.environ} | {'PATH':'/usr/bin:/bin'})
            async def exchange():
                process.stdin.write(payload)
                await process.stdin.drain()
                process.stdin.close()
                output = bytearray()
                while chunk := await process.stdout.read(min(8192, MAX_REPLY + 1 - len(output))):
                    output.extend(chunk)
                    if len(output) > MAX_REPLY:
                        raise ValueError()
                await process.wait()
                return bytes(output)
            try:
                output=await asyncio.wait_for(exchange(),30)
            except BaseException:
                if process.returncode is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                await process.wait()
                raise
            result=json.loads(output)
            if not isinstance(result,dict) or set(result) != ({'ok','result'} if result.get('ok') is True else {'ok','error'}):
                raise ValueError()
            if result['ok'] is not True or process.returncode:
                error = result.get('error')
                code = error.get('code') if isinstance(error,dict) else None
                if code=='MANAGED_GRANT_EXPIRED':
                    raise VoiceError(code,'The selected-account permission expired. Start a new request and select the account again.')
                raise VoiceError('MANAGED_ACCOUNT_DENIED','Connect denied this read. Review the selected account and its read permissions in Connections.')
            return result['result']
        except (OSError,ValueError,TypeError,TimeoutError):
            raise VoiceError('MANAGED_ACCOUNT_UNAVAILABLE','Connect did not return a valid managed read. No other account or tool was used.') from None

    async def list(self):
        if not self.available():
            return {'available':False,'accounts':[]}
        result=await self.call('list')
        if not isinstance(result,dict) or result.get('schemaVersion')!=1 or result.get('grantsCreated') is not False or result.get('liveAcceptanceVerified') is not False or not isinstance(result.get('eligible'),list) or len(result['eligible'])>64:
            raise VoiceError('MANAGED_ACCOUNT_UNAVAILABLE','The selected-account list is unavailable.')
        accounts=[]
        for item in result['eligible']:
            if not isinstance(item,dict) or item.get('toolkit')!='googlecalendar':
                raise VoiceError('MANAGED_ACCOUNT_UNAVAILABLE','The selected-account list is unavailable.')
            identity=account_ids([item.get('id')])[0]
            label=item.get('label')
            if not isinstance(label,str) or not label or len(label)>160 or any(ord(c)<32 for c in label):
                raise VoiceError('MANAGED_ACCOUNT_UNAVAILABLE','An account label is unavailable.')
            accounts.append({'id':identity,'label':label})
        return {'available':True,'accounts':accounts}

    async def ensure(self, task, store):
        selected=account_ids(task['granted_capabilities'].get('accounts',[]))
        if not selected:
            return task
        existing=task.get('connect_session')
        if existing:
            if datetime.fromisoformat(existing['expiresAt'].replace('Z','+00:00')) <= datetime.now(timezone.utc):
                raise VoiceError('MANAGED_GRANT_EXPIRED','The selected-account permission expired. Start a new request and select the account again.')
            return task
        result=await self.call('create',{'requestId':task['request_id'],'taskId':task['id'],
            'policyRevision':POLICY_REVISION,'accountIds':selected,'sendToGroqConfirmed':True})
        try:
            try:
                if set(result) != {'schemaVersion','sessionId','requestId','taskId','policyRevision','managedPolicy','accountIds','expiresAt','capabilities','readOnly'} or result['schemaVersion']!=1 or not re.fullmatch(r'[a-f0-9]{64}',result['sessionId']) or result['requestId']!=task['request_id'] or result['taskId']!=task['id'] or result['policyRevision']!=POLICY_REVISION or result['managedPolicy']!='maslow-calendar-read-1' or result['accountIds']!=selected or result['capabilities']!=['calendar.events.list'] or result['readOnly'] is not True:
                    raise ValueError()
                expiry=datetime.fromisoformat(result['expiresAt'].replace('Z','+00:00'))
                remaining=(expiry-datetime.now(timezone.utc)).total_seconds()
                if not 0<remaining<=3605:
                    raise ValueError()
            except (ValueError,TypeError,KeyError,AttributeError):
                raise VoiceError('INVALID_ACCOUNT_GRANT','Connect returned a different or invalid account permission.') from None
            return store.update(task['id'],event='managed_account_granted',connect_session=result)
        except BaseException:
            identity = result.get('sessionId') if isinstance(result,dict) else None
            if isinstance(identity,str) and re.fullmatch(r'[a-f0-9]{64}', identity):
                # The grant may already be durable in Connect even when local
                # task persistence fails. Revoke the returned exact session.
                try:
                    await self.call('revoke', {'sessionId':identity})
                except (VoiceError, asyncio.CancelledError):
                    try:
                        store.update(task['id'], event='account_cleanup_needed', account_cleanup_needed=True)
                    except Exception:
                        # A full/unwritable task store may also reject this flag;
                        # preserve the original failure and never start inference.
                        pass
            raise

    async def revoke(self, task):
        session = task.get('connect_session')
        if session:
            await self.call('revoke', {'sessionId':session['sessionId']})

    async def read(self, task, params):
        if task.get('execution_connection')!='free-cloud' or task.get('policy_revision')!=POLICY_REVISION or not isinstance(params,dict) or set(params)-{'accountId','timeMin','timeMax','maxResults'} or not {'accountId','timeMin','timeMax'} <= set(params):
            raise VoiceError('INVALID_TOOL','Choose the approved Calendar read and bounded time range.')
        if params['accountId'] not in task['granted_capabilities'].get('accounts',[]) or not task.get('connect_session'):
            raise VoiceError('ACCOUNT_NOT_GRANTED','The user did not select that account for this request.')
        arguments={key:value for key,value in params.items() if key!='accountId'}
        result=await self.call('read',{'sessionId':task['connect_session']['sessionId'],'requestId':task['request_id'],
            'taskId':task['id'],'policyRevision':POLICY_REVISION,'accountId':params['accountId'],
            'operation':'calendar.events.list','arguments':arguments})
        if not isinstance(result,dict) or set(result)!={'schemaVersion','sessionId','accountId','operation','untrustedContent','destination','speechAuthorized','data'} or result.get('schemaVersion')!=1 or result.get('sessionId')!=task['connect_session']['sessionId'] or result.get('accountId')!=params['accountId'] or result.get('operation')!='calendar.events.list' or result.get('untrustedContent') is not True or result.get('destination')!='groq' or result.get('speechAuthorized') is not False or len(json.dumps(result).encode())>MAX_REPLY:
            raise VoiceError('INVALID_ACCOUNT_RESULT','Connect returned an invalid managed read result.')
        data=result['data']
        if not isinstance(data,dict) or set(data)!={'events','hasMore'} or not isinstance(data['events'],list) or len(data['events'])>25 or type(data['hasMore']) is not bool:
            raise VoiceError('INVALID_ACCOUNT_RESULT','Connect returned an invalid bounded Calendar result.')
        return result
