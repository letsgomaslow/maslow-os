"""Secret Service only. Distinguish locked items from genuinely missing keys."""

import asyncio
import re

from .errors import FreeAIError


class EncryptionKey:
    async def _run(self, args, secret=None):
        try:
            process = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        except OSError:
            raise FreeAIError("KEYRING_UNAVAILABLE", "The desktop keyring is unavailable. Unlock or repair it to continue.") from None
        try:
            output, _ = await asyncio.wait_for(process.communicate(secret.encode() if secret else None), 30)
        except (TimeoutError, asyncio.CancelledError) as error:
            process.kill()
            await process.wait()
            if isinstance(error, asyncio.CancelledError):
                raise
            raise FreeAIError("KEYRING_LOCKED", "Unlock the desktop keyring and try again.") from None
        if len(output) > 16384:
            raise FreeAIError("KEYRING_UNAVAILABLE", "The keyring returned an invalid response.")
        return process.returncode, output.decode().strip()

    async def get(self):
        return await self._get("encryption")

    async def _get(self, account):
        code, paths = await self._run(["/usr/bin/gdbus", "call", "--session", "--dest", "org.freedesktop.secrets",
            "--object-path", "/org/freedesktop/secrets", "--method", "org.freedesktop.Secret.Service.SearchItems",
            "{'application': 'maslow-free-ai', 'account': '" + account + "'}"])
        # gdbus prints the two arrays of object paths (unlocked, locked). Never
        # unlock silently, replace a locked key, or infer 'missing' from failure.
        match = re.fullmatch(r"\((?:@ao\s*)?\[([^]]*)\],\s*(?:@ao\s*)?\[([^]]*)\]\)", paths)
        if code or not match:
            raise FreeAIError("KEYRING_UNAVAILABLE", "The desktop keyring is unavailable. Unlock or repair it to continue.")
        if match[2].strip():
            raise FreeAIError("KEYRING_LOCKED", "Unlock the desktop keyring and try again.")
        if not match[1].strip():
            return None
        code, value = await self._run(["/usr/bin/secret-tool", "lookup", "application", "maslow-free-ai", "account", account])
        if code or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise FreeAIError("KEYRING_UNAVAILABLE", "The saved encryption key cannot be read. It was not replaced.")
        return value

    async def create(self, value):
        if await self.get() is not None:
            raise FreeAIError("KEY_ALREADY_EXISTS", "The encryption key already exists and was left unchanged.")
        code, _ = await self._run(["/usr/bin/secret-tool", "store", "--label=Maslow Free cloud AI encryption",
            "application", "maslow-free-ai", "account", "encryption"], value)
        if code or await self.get() != value:
            raise FreeAIError("KEYRING_LOCKED", "The encryption key could not be saved. Unlock the desktop keyring and try again.")

    @staticmethod
    def _recovery_account(identity):
        if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{32}", identity):
            raise FreeAIError("INVALID_RECOVERY", "Choose a recorded recovery snapshot.")
        return "recovery-" + identity

    async def get_recovery(self, identity):
        return await self._get(self._recovery_account(identity))

    async def save_recovery(self, identity, value):
        account = self._recovery_account(identity)
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise FreeAIError("RECOVERY_KEY_UNAVAILABLE", "The recovery key is invalid.")
        current = await self._get(account)
        if current is not None:
            if current != value:
                raise FreeAIError("RECOVERY_KEY_MISMATCH", "The recovery key already exists and was left unchanged.")
            return
        code, _ = await self._run(["/usr/bin/secret-tool", "store", "--label=Maslow Free cloud AI recovery",
            "application", "maslow-free-ai", "account", account], value)
        if code or await self._get(account) != value:
            raise FreeAIError("KEYRING_LOCKED", "The recovery key could not be saved. Package changes are blocked.")
