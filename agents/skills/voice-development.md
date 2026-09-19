# Voice development and verification

Read this guide before editing `voice/`, Voice launch/install integration, the `maslow.voice` plugin, or Voice acceptance helpers. Start with [the development index](../../docs/maslow-development.md) and its current Voice checkpoint. The index owns current status; this guide owns procedure.

For direct Lenovo development, use [the portable repository map](../../docs/lenovo-development.md) and [the September 19 integration handoff](../../docs/handoffs/2026-09-19-gemini-voice-orb-integration.md). The September 16 failure report remains historical evidence for the older installed package.

## Locate and scope the work

1. Read the owning repository's `AGENTS.md`, inspect status/log/worktrees and locate the active Voice integration branch named in the index. Do not reimplement features missing from the saved `main` or older Hub checkout. Runtime, Hub source, package recipes and ISO harness are separate repositories.
2. Preserve the separation between conversation, validated task brief and execution. Keep original words, selected project, task/run identities, approvals and cancellation observable. Provider readiness is not coding-agent authentication or permission consent. Do not silently fall back to a different provider.
3. Inspect the production provider factory and installed source hashes. A private browser/Mac tester or a factory override may use a different transport from the packaged Linux service. Record that distinction before claiming a provider pass.
4. Read [Voice architecture](../../docs/maslow-voice.md), [execution](../../voice/docs/execution.md) and [offline isolation](../../voice/docs/offline.md) for the affected boundary. For visual changes also read [shell development](shell-dev.md) and [visual verification](visual-verification.md); for install/launcher changes use the matching guides in AGENTS.md.

## Dependencies and focused checks

- Use the pinned environment specified by `voice/requirements.txt` and `voice/requirements.lock`; local speech also has `voice/local-requirements.txt` and `voice/local-requirements.lock`. Inspect actual pinned SDK code before attributing behavior to it. Do not install or upgrade packages merely because an experiment failed.
- The owning package repository defines system dependencies, Python runtime, packaged files and install hooks. If an authorized source change requires a dependency change, update direct requirements/locks and owning recipes together, then verify the installed package resolves dependencies normally.
- Run the relevant tests through `bash test/shell.d/voice-test.sh` with the required environment, or focused tests documented in the current handoff. State pass/fail/skip counts and revision; missing SDK or namespace support is not acceptance. See [testing](../../docs/testing.md).
- Documentation-only edits require relative-link/path, revision, scope and whitespace checks, not a new build, cloud session, model download or ISO.

## Verify in stages

1. Source and protocol regressions: use real SDK/socket/process contracts where the defect depends on lifecycle or backpressure. Do not infer a live account result from mocks or structural assertions.
2. Fast visual iteration: Docker, headless Weston, real Quickshell/software rendering, inspected PNGs. Cover the single Orb at 56 and 88 pixels in idle, connecting, listening, thinking/working, speaking, muted, error and disabled states. Exercise the GPU shader and software fallback, reduced motion, manual drag bounds, reset, automatic placement, microphone indicator, settings, keyboard control and task state. Record whether evidence includes a display resize or scale change. Fixtures prove rendering, not accounts, physical pointer interaction or real task state changes.
3. Installed-system proof: reuse the ISO repository's headless QEMU/TCG harness with CIDATA, SSH and QMP screenshots/OCR. No UTM keyboard/clipboard. Reuse the installed overlay for package changes; rebuild media only when the installation baseline changes or a release checkpoint requires it.
4. Physical acceptance: Lenovo microphone, speaker, echo, perceived responsiveness and actual desktop interactions remain separate. Never present TCG timing, synthetic WAV input or virtual speaker samples as hardware proof.

On this development host, run package builds and installed audio acceptance sequentially. Do not collect QMP screenshots, perform unrelated guest work or start another build during audio timing windows. Record CPU/memory/rendering/affinity changes and whether the coordinator was warm or cold. Stop or restore only the controls/processes owned by the test.

## Define acceptance before a paid or long-running test

- Freeze the helper, input fixtures, criteria and output location. Compile/import-check the helper and validate its positive/negative controls before starting a provider. Keep each diagnostic bounded, tied to one hypothesis and separate from final acceptance.
- Check conversation quality, speech-detail accuracy and task delivery separately. For a spoken task inspect original input, complete captured text, optimized brief, authenticated handoff/run ID, final filename/path and requested content. A provider response, delegation notice or `completed` state alone is insufficient.
- For audible interruption, observe real rendered output before injecting the interruption, then verify output completion, the full follow-up and an audible response while work remains active. Merely queued TTS does not prove interruption. Include continued listening and clean stop.
- For cold-start scenarios, record that no coordinator was prepared before audio. A warm-start pass cannot close the first-use gate. Record capture drops and event-loop delays alongside connection errors.
- Keep deterministic audio/task/artifact gates distinct from semantic review of free-form answers. Use a fixed rubric and complete persisted answer, bound to the unchanged result/script/transcript hashes. Both stages must pass; do not grow a substring list after every answer or accept unrelated text as success.
- When execution completes with the wrong or missing artifact, report that mismatch directly. Do not wait for Voice idle shutdown and then diagnose only a generic audio timeout. Never normalize the fixture filename or silently rewrite a transcription to make the test pass.
- Preserve failed runs. Distinguish product defect, SDK behavior, emulator/resource limitation, helper defect and unknown cause. A passing diagnostic or factory override is not acceptance of a packaged fix. Rerun only when a change or new evidence addresses the failure.

## Credentials, status and closeout

Use the existing private credential-entry/transfer workflow. Never request keys in chat or retain them in source, arguments, logs or artifacts. Do not restart RAM-only Mac testers casually. In credentialed guest tests preserve RAM-only storage/swap controls and perform the recorded scoped cleanup; report oversized files or failed cleanup honestly.

At each checkpoint record exact source/recipe/archive identities, evidence locations, test outcomes and exclusions, confirmed causes versus hypotheses, scoped fixes and remaining gates. Name one next action. When the user marks a provider pending, leave its implementation/evidence intact and stop treating its old next experiment as an active instruction. Do not claim publication, Lenovo acceptance or a completed overall feature from partial tests. Keep the current index concise and detailed evidence in the dated handoff.
