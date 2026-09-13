"""Bounded JSON HTTP; no environment proxies or credential-bearing redirects."""

import asyncio
import json
from urllib import request, error

from .errors import VoiceError


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def json_request(url, method="GET", body=None, token="", headers=None, timeout=20):
    all_headers = {"Accept": "application/json", **(headers or {})}
    if token:
        all_headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        all_headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request.Request(url, data=data, headers=all_headers, method=method), timeout=timeout) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise VoiceError("RESPONSE_TOO_LARGE", "The service returned too much data.")
            return json.loads(raw)
    except error.HTTPError as exc:
        codes = {401: "AUTH_REQUIRED", 403: "ACCESS_DENIED", 404: "NOT_FOUND", 409: "REQUEST_CONFLICT", 429: "RATE_LIMITED"}
        raise VoiceError(codes.get(exc.code, "SERVICE_ERROR"), "The service rejected this request. Check its connection and account settings.") from None
    except (error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise VoiceError("SERVICE_UNAVAILABLE", "The service could not be reached or returned an invalid response.") from None


async def request_json(*args, **kwargs):
    return await asyncio.to_thread(json_request, *args, **kwargs)
