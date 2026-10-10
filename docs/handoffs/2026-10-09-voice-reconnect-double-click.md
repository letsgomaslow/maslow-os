# Voice reconnect, internet wait, double-click to end, hideable badges and orb contrast

Date: 2026-10-05 to 2026-10-09. Goal: find out from the installed Voice logs why conversations fail, check whether the failures are Google's or Maslow's (including whether the Gemini free tier is to blame), fix the Maslow side, and let the person end a conversation with a double-click on the orb.

**Status (2026-10-10): closed and merged.** All four changes are on `maslow-os` `main`, installed on the Lenovo as `maslow-voice 0.1.5-37` and confirmed by the person (reconnect and double-click: "that worked"; badges and contrast were asked to be merged after review). The `maslow-os-pkgs` recipe is `0.1.5-37` on branch `voice-orb-moods`; it is not merged into `maslow` and nothing is published.

## Resume here

- **Installed:** `maslow-voice 0.1.5-37` from `maslow-os` `ce18c669` (`main` has only documentation after it). Rollback packages for `0.1.5-33` to `0.1.5-36` are under `voice-mvp-build/` (`voice-good-enough-33`, `voice-reconnect-34`, `voice-badge-35`, `voice-contrast-36`, `voice-contrast-37`).
- **Code:** reconnect and retry in `voice/maslow_voice/daemon.py` (`RECONNECT_DELAYS`, `RETRYABLE_CODES`, `start_voice`/`_start_voice_attempt`, `wait_for_internet`, `reconnect_voice`); 1007 classification in `providers/livekit_gemini.py` (`_public_error`); `acknowledge` task action in `tasks.py`; orb double-click, badge hiding and contrast in `voice/ui/Panel.qml` (`endFromOrb`, `badgeForTasks`, `dismissBadge`, `chromeShadowColor`, `statusQuiet`).
- **Build and install a new candidate:** `git archive` the commit into `voice-mvp-build/<name>/runtime`, copy `maslow-os-pkgs/pkgbuilds/maslow-voice/PKGBUILD` with the next `pkgrel`, run `docker run --rm -v <dir>:/work -w /work/recipe -e OMARCHY_SRC=/work/runtime maslow-voice-builder:preferences makepkg -d -f`, then `pkexec pacman -U --noconfirm <package>`. Restart `maslow-voice` for Python changes. For UI changes, `touch "$XDG_RUNTIME_DIR/maslow-voice-refresh-pending"`, run `/usr/lib/maslow-voice/launch talk` and close the panel with `omarchy-shell shell hide maslow.voice`; check `/usr/share/maslow/plugins/maslow.voice/manifest.json` names the new revision.
- **Test:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=voice /usr/lib/maslow-voice/venv/bin/python -m unittest discover -s voice/tests -p 'test_*.py'` (440 OK, two expected skips at `0.1.5-35`; `0.1.5-36`/`-37` changed only QML and its contract test), then `node voice/tests/ui-contract-test.mjs`, `ui-controller-test.mjs` and `orb-contract-test.mjs`.
- **Field evidence:** `journalctl --user -u maslow-voice` lines `Voice reconnecting`, `Voice connection attempt` and `Gemini server indicates disconnection soon`; `~/.local/state/maslow-voice/voice-audit.jsonl` (`session_started`, `session_ended`, `error` with `code`). Compare with the baseline under Iteration summary.
- **Working with the person:** they use the Lenovo while agents work. Do not move the pointer or change their theme for visual checks; take passive `grim` screenshots instead. Ask before merging, pushing or publishing; they have approved fast-forward merges of `main` for each checkpoint so far.
- **Open items:** see Remaining gates at the end and backlog rows V5 to V7 in [the development index](../maslow-development.md).

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

## Follow-up: finished-work badges can be hidden (0.1.5-35)

The person reported a "! Work failed" badge that never went away; clicking it opened the Voice panel. It came from the 2026-10-05 Codex calculator task, which stayed un-dismissed because Dismiss existed only on the selected task card in Work.

- `tasks.py`/`store.py`: new `acknowledge` task action for finished tasks (`acknowledged=True`, not `dismissed`); refused with `TASK_ACTIVE` for work that still needs the person. `continue` clears it. The daemon does not start a Gemini task relay for it.
- `Panel.qml`: outcome badges hide when seen (opened from the badge or the Work list), when the new × beside the badge is clicked, or an hour after the work finished (`badgeClock`, refreshed each minute). Approval, input and proposal badges never hide and have no ×. The × is in the layer input mask. Work says "Finished work stays here for review until you dismiss it."
- Commit `e5b88676` on branch `voice/badge-acknowledge` from `main` at `3263e778`. Built as `0.1.5-35` (package SHA-256 `da6b88f81bb4b798a99ffba3bdbdec3037ae16aac84eedcd0ea96bc69f900c1e`, logs in `voice-mvp-build/voice-badge-35/`) and installed; the service was restarted and the plugin points at `0.1.5-35/Panel.qml`.
- Tests: 440 Python tests OK (two expected skips); UI contract, controller and orb contract tests passed with new badge, hide, age-out and acknowledge assertions. A desktop screenshot before install showed "! Work failed"; after install the badge was gone (the task finished on 2026-10-05) and the task remained listed. The × on a fresh outcome was not observed on screen yet.

## Follow-up: the orb stands out from matching windows (0.1.5-37)

The person showed the "Ready · click to talk" pill disappearing into a terminal with the same theme background: the pill was filled with the theme's popup background and had no border unless focused, and its fixed 280 px width hid the text behind it.

- `Panel.qml`: the status pill, task badge and × button have a 1.5 px accent outline and a `MultiEffect` shadow (`chromeShadowColor`: an accent glow when the surface luminance is below 0.18, otherwise a dark shadow). The orb glows from a plain accent circle at 60% of its size behind it; an earlier build (`0.1.5-36`) put the effect on a layer over the orb's shader and was replaced. The pill fits its text. The idle "Ready · click to talk" label shows only while the orb or pill is hovered or focused (700 ms hide delay); hidden, it leaves the input mask.
- Commit `ce18c669` on branch `voice/orb-contrast` from `main` at `536f36be`. Built as `0.1.5-37` (package SHA-256 `9d7847e731003c3797204e16c66ed66c61e83bd013b823186eb07b31eec369a9`, logs in `voice-mvp-build/voice-contrast-37/`) and installed; the plugin points at `0.1.5-37/Panel.qml`.
- Tests: UI contract (new outline, shadow, glow, fit and idle-label assertions), controller and orb contract tests passed; `qmllint` reports no new errors. Screenshots over the dark terminal show the glowing orb with the idle label hidden.
- Not verified: a light theme or light window behind the orb (not changed on the person's desktop), the hover reveal on screen (the pointer was not moved again after one test moved it while the person was working), and touch. During one plugin reload a teal square showed behind the orb for about a second while the panel opened; it was not caused by the new layers and may be the orb shader's first frame. Whether it predates this change is unconfirmed.

## Remaining gates and next action

- Recipe: `maslow-os-pkgs` branch `voice-orb-moods` advanced from `0.1.5-33` to `0.1.5-37` in `3814c81` (pushed; identical to the recipe that built the installed package). Merging it into `maslow` and publishing need the person's separate approval.
- Unverified on screen: the orb and labels over a light theme or light window, the hover reveal of the idle label, the badge × on a fresh outcome, and touch double-tap.
- Unexplained: a teal square behind the orb for about a second while the panel opened during one plugin reload (see the contrast follow-up above). Reproduce on a reload with `0.1.5-35` (no contrast layers) to learn whether it predates the change.
- Not done (backlog V5 to V7): buffering microphone audio during a reconnect, the same retry policy for the OpenAI Realtime provider, provider failover for BYOK users with more than one key, a free-key notice in setup, and keeping the reason when a Codex task fails (the 2026-10-05 calculator task stored only `EXECUTION_FAILED`).
- **Next action:** after a few days of normal use, compare the audit log's drops and recoveries with the 2026-09-19 to 2026-10-05 baseline above.
