"""Use the installed Secret Service client without secrets in process arguments."""

import asyncio
import shutil

from .errors import VoiceError

NAMES = {"google", "openai", "livekit_key", "livekit_secret", "server_token", "anthropic", "hermes_api"}


class Credentials:
    async def _run(self, args, secret=None):
        binary = shutil.which("secret-tool")
        if not binary:
            raise VoiceError("KEYRING_UNAVAILABLE", "The desktop keyring is unavailable. Unlock or repair it to connect an account.")
        process = await asyncio.create_subprocess_exec(binary, *args, stdin=asyncio.subprocess.PIPE,
                                                       stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            output, _ = await asyncio.wait_for(process.communicate(secret.encode() if secret is not None else None), 30)
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        except TimeoutError:
            process.kill()
            await process.wait()
            raise VoiceError("KEYRING_LOCKED", "Unlock the desktop keyring and try again.") from None
        return process.returncode, output.decode().rstrip("\n")

    @staticmethod
    def _attributes(name):
        if name not in NAMES:
            raise VoiceError("INVALID_CREDENTIAL", "That credential is not used by Voice.")
        return ["application", "maslow-voice", "account", name]

    async def get(self, name):
        _, value = await self._run(["lookup", *self._attributes(name)])
        return value

    @staticmethod
    def validate_value(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 16384 or "\x00" in value:
            raise VoiceError("INVALID_CREDENTIAL", "Enter a non-empty account credential.")

    async def set(self, name, value):
        self.validate_value(value)
        code, _ = await self._run(["store", "--label=Maslow Voice " + name, *self._attributes(name)], value)
        if code:
            raise VoiceError("KEYRING_LOCKED", "The account could not be saved. Unlock the desktop keyring and try again.")

    async def delete(self, name):
        await self._run(["clear", *self._attributes(name)])
