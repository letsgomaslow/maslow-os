"""Connect existing model managers and prepare a pinned, resumable speech pack."""

import asyncio
import hashlib
import json
import os
import shutil
from pathlib import Path
from urllib import request
from urllib.parse import urlsplit

from .config import private_directory
from .errors import VoiceError
from .http import request_json


def speech_manifest():
    return json.loads((Path(__file__).resolve().parent.parent / "assets/english-base-1.json").read_text())


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_speech(directory, manifest=None):
    directory = Path(directory)
    for item in (manifest or speech_manifest())["files"]:
        target = directory / item["path"]
        if target.is_symlink() or not target.is_file() or target.stat().st_size != item["size"] or file_digest(target) != item["sha256"]:
            return False
    return True


class DownloadRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination = urlsplit(newurl)
        host = destination.hostname or ""
        if destination.scheme != "https" or not any(host == root or host.endswith("." + root) for root in ("huggingface.co", "hf.co", "xethub.hf.co")):
            raise VoiceError("DOWNLOAD_REDIRECT_REJECTED", "The model download redirected to an unapproved location.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_speech(directory, progress=None, manifest=None):
    import fcntl
    root = private_directory(Path(directory))
    pack = manifest or speech_manifest()
    opener = request.build_opener(request.ProxyHandler({}), DownloadRedirect())
    total = sum(item["size"] for item in pack["files"])
    completed = 0
    with (root / ".download.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise VoiceError("DOWNLOAD_RUNNING", "The English speech pack is already downloading.") from None
        for item in pack["files"]:
            target = root / item["path"]
            if target.is_symlink() or root.resolve() not in target.resolve().parents:
                raise VoiceError("UNSAFE_DOWNLOAD", "The speech destination is not a private local file.")
            private_directory(target.parent)
            if target.is_file() and target.stat().st_size == item["size"] and file_digest(target) == item["sha256"]:
                completed += item["size"]
                continue
            partial = target.with_name(target.name + ".part")
            if partial.is_symlink():
                raise VoiceError("UNSAFE_DOWNLOAD", "The speech download staging file is not safe.")
            offset = partial.stat().st_size if partial.exists() else 0
            if offset >= item["size"]:
                partial.unlink()
                offset = 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            try:
                with opener.open(request.Request(item["url"], headers=headers), timeout=60) as response:
                    if offset and response.status != 206:
                        offset = 0
                    if response.status == 206 and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                        raise VoiceError("INVALID_DOWNLOAD_RANGE", "The server could not resume the speech download safely.")
                    with partial.open("ab" if offset else "wb") as stream:
                        partial.chmod(0o600)
                        received = offset
                        while chunk := response.read(256 * 1024):
                            received += len(chunk)
                            if received > item["size"]:
                                raise VoiceError("DOWNLOAD_TOO_LARGE", "The speech download exceeded its recorded size.")
                            stream.write(chunk)
                            if progress:
                                progress(completed + received, total)
                        stream.flush()
                        os.fsync(stream.fileno())
                if partial.stat().st_size != item["size"] or file_digest(partial) != item["sha256"]:
                    partial.unlink(missing_ok=True)
                    raise VoiceError("MODEL_CHECKSUM_FAILED", "A speech asset did not match its published checksum. Download it again.")
                os.replace(partial, target)
            except VoiceError:
                raise
            except OSError:
                raise VoiceError("DOWNLOAD_INTERRUPTED", "The speech download was interrupted. Retry to resume it.") from None
            completed += item["size"]
        return {"pack": pack["id"], "verified": verify_speech(root, pack), "bytes": total}


def discover_downloaded_ollama(directory):
    """List existing model manifests without opening a network connection."""
    from .offline import validate_model_tree
    if not directory:
        raise VoiceError("OFFLINE_MODELS_REQUIRED", "Choose your existing Ollama model folder.")
    root = Path(directory)
    try:
        validate_model_tree(root)
        result = []
        manifests = root / "manifests"
        for file in sorted(manifests.glob("*/*/*/*")):
            if not file.is_file():
                continue
            registry, namespace, name, tag = file.relative_to(manifests).parts
            prefix = "" if registry == "registry.ollama.ai" else registry + "/"
            namespace = "" if namespace == "library" else namespace + "/"
            model = prefix + namespace + name + ":" + tag
            result.append({"id": model, "label": model})
        return result
    except OSError:
        raise VoiceError("OFFLINE_MODELS_REQUIRED", "The Ollama model folder could not be read.") from None


async def discover_models(config, token=""):
    endpoint = config["server_url"].rstrip("/")
    if config["server_kind"] == "ollama":
        response = await request_json(endpoint.removesuffix("/v1") + "/api/tags", token=token)
        items = response.get("models", [])
        return [{"id": str(item.get("name", "")), "name": str(item.get("name", "")), "size": item.get("size"),
                 "fit": "Managed by Ollama", "local": not str(item.get("name", "")).endswith("-cloud")} for item in items]
    response = await request_json(endpoint.removesuffix("/v1") + "/v1/models", token=token)
    return [{"id": str(item.get("id", "")), "name": str(item.get("id", "")), "fit": "Check fit in LM Studio", "local": None}
            for item in response.get("data", [])]


async def test_model(config, token=""):
    model = config["model"]
    if not model:
        raise VoiceError("MODEL_REQUIRED", "Choose a language model from your model manager.")
    endpoint = config["server_url"].rstrip("/").removesuffix("/v1") + "/v1/chat/completions"
    probe = {"model": model, "messages": [{"role": "user", "content": "Reply with the word READY."}], "max_tokens": 16, "stream": False}
    response = await request_json(endpoint, "POST", probe, token, timeout=60)
    try:
        content = response["choices"][0]["message"]["content"]
        if not isinstance(content, str) or "READY" not in content:
            raise ValueError()
    except (KeyError, IndexError, TypeError, ValueError):
        raise VoiceError("MODEL_TEST_FAILED", "The selected model did not complete the readiness test.") from None
    return True


def offline_requirements(config):
    checks = []
    for executable, label in (("bwrap", "Offline isolation"), ("weston", "Offline workspace"), ("ollama", "Local model engine"), ("hermes", "Task coordinator"), ("piper", "Local speech voice")):
        ok = bool(shutil.which(executable))
        checks.append({"name": executable, "ok": ok, "message": label + (" is installed." if ok else " needs installation.")})
    speech = config.get("speech_directory", "")
    verified = bool(speech) and verify_speech(speech)
    checks.append({"name": "speech", "ok": verified, "message": "English speech pack verified." if verified else "Download and verify the English speech pack."})
    configured = bool(config.get("model")) and not config["model"].endswith("-cloud")
    checks.append({"name": "model", "ok": configured, "message": "Local model selected." if configured else "Choose a downloaded local model."})
    return checks
