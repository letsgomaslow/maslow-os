# Voice reconnect, internet wait and double-click to end

Date: 2026-10-05 to 2026-10-09. Goal: find out from the installed Voice logs why conversations fail, check whether the failures are Google's or Maslow's (including whether the Gemini free tier is to blame), fix the Maslow side, and let the person end a conversation with a double-click on the orb.

**Status: implemented, installed locally as `maslow-voice 0.1.5-34`, tested by the person ("that worked") and merged to `main`.** The package recipe change (`pkgrel=34`) was made only in the local build copy; `maslow-os-pkgs` was not changed and nothing was published.

## Iteration summary

- **Log review (2026-09-19 to 2026-10-05):** 105 Gemini Live sessions with a median connect of 352 ms (90th percentile 630 ms). Desktop actions, approvals and Obsidian notes worked. Failures were almost all connection failures: Gemini 1011 "internal error" drops on nine days, 24 handshake timeouts after the 2026-10-05 reboot while the network was still coming up, and 21 rejections on 2026-10-03 from an empty enum value in the `tell_agent` tool schema (already fixed by the `"none"` placeholder in `providers/gemini_tools.py`). One Codex task ("Build a calculator app HTML page", 2026-10-05) failed with no stored reason; that is not addressed here.
- **Research:** 1011 drops on the Gemini Live API are widely reported, including by paid users, and are worse on preview models; Google acknowledged them in July 2026. `gemini-3.8-live` has been generally available since 2026-09-15. The free tier is not the cause of 1011, but it allows Google to use conversations for training with human review, shares capacity and limits concurrent Live sessions. Recommendation for BYOK: tell users this when they add a free key and recommend enabling billing.
- **Correction to the first research summary:** the summary said Maslow does not use Gemini session resumption. The pinned `livekit-plugins-google 1.8.2` always requests it and reconnects through Gemini's roughly ten-minute GoAway on its own (nine GoAway warnings in the journal, none followed by a drop). The real gap: after a 1011 the plugin retries at once with the old resumption handle, that retry failed at connect in every journal case, and connect failures are fatal in the plugin. Maslow's own fresh-session reconnect then succeeded (2026-10-05 10:59:50, back in about a second), but it was limited to two attempts per 180 seconds and never ran for failures at start.

## What changed

- `voice/maslow_voice/daemon.py`:
  - `GEMINI_CONNECTION_FAILED` reconnects up to four times per 300 seconds, waiting 0, 1, 3 and 6 seconds (`RECONNECT_DELAYS`, `RETRYABLE_CODES`). The old rule that skipped retries in the first 3 seconds of a session is gone: the plugin connects after `start` returns, so an early failure is as momentary as a later one.
  - `start_voice` wraps the old start (now `_start_voice_attempt`) and retries the same error up to four times, showing "Connecting…". An error event that arrives while connecting is left to that retry instead of ending Voice.
  - Before each retry, while `generativelanguage.googleapis.com` cannot be resolved, Voice shows "Waiting for internet…" for up to 120 seconds (`wait_for_internet`, `internet_ready`).
  - During a reconnect pause the state is `connecting`, so a click ends Voice; `end_voice` also cancels the pending `reconnect_task`. Captions are cleared on every exit path.
- `voice/maslow_voice/providers/livekit_gemini.py`: Google's 1007 rejection of the session setup, found anywhere in the exception chain, becomes `GEMINI_SETUP_REJECTED` ("Gemini rejected Maslow's voice setup. Update Maslow Voice through Hub, then try again.") and is never retried.
- `voice/ui/Panel.qml`: the orb's `onDoubleClicked` ends the conversation through `endFromOrb`. The first click still pauses or resumes at once (no added delay); the second sends `end_voice` only if a conversation was running before the first click, so a double-click on an idle orb only starts Voice. The orb's accessible description mentions it.
- Documentation: `voice/docs/execution.md` (reconnect policy and the resumption finding), `voice/ui/README.md` and `docs/maslow-voice-product.md` (double-click).

## Commits and artifacts

- `maslow-os` branch `voice/reconnect-and-double-click` from `main` at `450637e6`: `820aedcf` (reconnect, retry and internet wait), `58233ab8` (double-click to end), plus a documentation commit recording this handoff.
- Build: `git archive` of `58233ab8` with the `0.1.5-33` recipe (`maslow-os-pkgs` `6c3e0b82`) copied and changed locally to `pkgrel=34`, built in `maslow-voice-builder:preferences` with `OMARCHY_SRC` and `makepkg -d -f`; `check()` passed. Package SHA-256 `2e1fc18266b7a45d20987bd6e004e87c352cc9a9e0f77cfcd3291d4ee9f6c96f`. Packaged `daemon.py`, `livekit_gemini.py` and `Panel.qml` match the commit. Inputs, build and install logs: `voice-mvp-build/voice-reconnect-34/`.
- Installed with `pkexec pacman -U`; the service was restarted and the plugin rescanned through the packaged launcher; the manifest points at `0.1.5-34/Panel.qml`. Rollback: `voice-mvp-build/voice-good-enough-33/recipe/maslow-voice-0.1.5-33-x86_64.pkg.tar.zst`.

## Evidence

- Full Python suite: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=voice python -m unittest discover -s voice/tests -p 'test_*.py'` ran 439 tests OK (two expected skips). New and updated tests cover: four reconnects per window then the reported error, a drop right after start being retried, setup and audio errors not retried, start retried until it connects, the error reported after the last attempt, the internet wait caption, and ending Voice during a reconnect pause. `test_gemini_live.py` covers 1007 (direct and chained) versus 1011 and timeouts.
- `node voice/tests/ui-contract-test.mjs` (with new `endFromOrb` and double-click assertions), `orb-contract-test.mjs` and `ui-controller-test.mjs` passed. `qmllint` reports no new errors in `Panel.qml`.
- A real Gemini text session from the source checkout (temporary state directory) connected and answered. A cold start took about 14 s from both the source checkout and the installed 0.1.5-33 code, so the time is not from this change.
- The person tested the installed 0.1.5-34 and confirmed it worked.
- Not reproduced on demand: a real 1011 drop, a real network outage and touch double-tap. The reconnect paths are covered by unit tests; field evidence will come from the journal (`Voice reconnecting`, `Voice connection attempt`) and `~/.local/state/maslow-voice/voice-audit.jsonl`.

## Remaining gates and next action

- Advance the recipe in `maslow-os-pkgs` to `0.1.5-34` before any package publication.
- Not done: buffering microphone audio during a reconnect, the same retry policy for the OpenAI Realtime provider, provider failover for BYOK users with more than one key, a free-key notice in setup, and keeping the reason when a Codex task fails.
- **Next action:** after a few days of normal use, compare the audit log's drops and recoveries with the 2026-09-19 to 2026-10-05 baseline above.
