# Voice source integration closeout

Date: 2026-10-03. The user authorized committing and merging the complete Voice iteration, then deferring the next iteration. Runtime targets `main`; the package repository targets its product branch `maslow`. This includes the earlier Voice preferences, previews and normal/extended shortcuts already on `codex/voice-preferences`, plus the [orb-first redesign](2026-10-03-voice-ux-redesign.md), [live theme integration](2026-10-03-voice-theme.md) and original [expressiveness review](2026-10-03-voice-orb-expressiveness.md).

## Reviewed source

Runtime implementation commit: `eba87bc5`. Independent backend and UI/package reviewers checked disjoint scopes. Backend review found and reproduced an OpenAI race: pausing before a typed response's delayed `response.created` event could leave its caller waiting until timeout, which ended the retained session. The implementation now completes the retired caller normally, cancels the exact stale response ID, and tolerates only correlated `response_cancel_not_active` errors. Regression coverage also verifies that a newer active response is preserved and unrelated cancellation errors still fail. Root reviewed the correction and reran the complete pinned Voice suite.

The reviewed source preserves the existing three supported provider routes, experimental Advanced controls, exact approval identities, task context, saved position and original session maximum. No dependencies, persistent schema, credentials, publication configuration or public provider fallback changed.

## Final checks and evidence boundaries

- Final pinned Voice suite: 364 tests run, 362 passed, two expected Mac sandbox skips. UI and orb contract checks also passed. The focused OpenAI lifecycle suite passed all 22 tests.
- Controller checks, all 19 launcher scenario groups, launcher syntax, CLI tests, brand validation and whitespace checks passed. Package recipe syntax and Maslow packaging invariants passed.
- Native rendering, live palettes and installed package evidence remain the exact artifacts recorded in the redesign/theme handoffs. No new physical or native acceptance is inferred from this merge. The theme fixture's synthetic Shift+F10 reopening failure remains recorded; it was not counted as passing.
- Local final test logs are retained outside Git at workspace-relative `voice-mvp-build/voice-theme/merge-*-tests*.log`. Raw logs, captures and package archives are not committed.

Installed Lenovo remains `maslow-voice 0.1.5-18`, archive SHA-256 `0648557399e9258f1a36b628559d5c3ef8ad3b66a1d8d3c316c317e1888edef7`. The new source-only OpenAI correction is not installed by this merge. The coordinated recipe advances to `0.1.5-19` to distinguish the reviewed source from that installed artifact. Package installation, signing, publication, channel promotion and ISO assembly remain separate actions.

## Next iteration

Resume with physical listening, playback, interruption and pause/resume separately for Google Live, native LiveKit Expressive and OpenAI Realtime. LiveKit Expressive remains acceptance-pending. Physical right-click/long-press/drag, shortcut activation and actual display resize/scale changes remain gates. Review the recorded synthetic keyboard failure before claiming complete keyboard acceptance. A separately authorized local rollout of the final correction can precede those tests. Do not restart old credentialed experiments or promote these sources as a release.
