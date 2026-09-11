# Hub redesign: internal experiential OTA candidate

## Decision and scope

The user explicitly chose learning through an internal Lenovo staging test rather than waiting for full observability acceptance. Restore the prior Welcome → Connect → Open design direction, deliver a recognizable Hub UI update, preserve state, and test update/rollback from an end-user perspective. Backend benchmarks and real trace acceptance remain separate; they are not grounds to describe experimental observability as production-ready. Signature, replay, ownership, dependency, privilege, and recovery checks remain mandatory. Connect is parked. No ISO rebuild, runtime change, or Lenovo mutation was performed.

## Exact candidate

- Hub source: `6ea55deaed52e1a0dbd65b947d1fa913777cfeee` (`Restore guided Hub workspace for staging OTA test`), local main, clean after commit; not pushed.
- Recipe: `e4fab062dc6631f1a14aadeb57f0f88b2ee05fff`, unchanged. Runtime integration remains `4feda72d`; later documentation changes do not alter the tested runtime or ISO.
- Package: `maslow-hub-0.2.0-1-any.pkg.tar.zst`, 58,332 bytes, SHA-256 `498dc7883ecd8bd11ae3539d549554b1dd423b41d02b12facc83a43b388dc992`.
- Package evidence: sibling `hub-evidence/ota-ui-020/packages/`. This supersedes the earlier unsigned 0.2.0 development payload for the internal UI test; the older artifact remains preserved separately under `ota-020` and must not be promoted accidentally.
- Exact 0.1.3 rollback baseline remains SHA-256 `3baa23be234a5a9754d755f61d4da1ba9eda81a9ef16a2ebd99dc6e469d7f20b`. Do not rebuild it or use the 0.1.4 fixture.

## Implemented experience

- Native sidebar navigation and editorial Welcome / Connect / Open stages. Stage navigation is UI-local and does not reset or rewrite saved onboarding state.
- Completed users see a workspace overview and selected tools, not the setup guide. Tool readiness remains user confirmation, not inferred provider authentication.
- Customize setup retains existing supported tool actions. Explore observability exposes the existing optional controls without installing or starting anything; experimental status and full-trace consent remain explicit.
- Updates includes a visible 0.2.0 staging What's new panel. Current/available versions still come from the helper; the panel is not proof of installation or release availability.
- No helper API, state schema, runtime package, backend template, provider configuration, or signing implementation changed. Hub source includes `docs/staging-ui-test.md` with the end-user update / rollback walkthrough and feedback questions.

## Verification and limits

- `bash release/check.sh`: 71 Python tests passed, plus QML/helper contract, actual guided-stage function tests, version consistency, and whitespace checks. Added tests assert status invokes only read-only runtime calls and no observability methods, preserves completed setup, preserves optional-state backups, and keeps stage navigation bounded and UI-only with heading focus.
- Real Quickshell + existing Docker/Weston software renderer inspected: dark Connect stage, light returning-user overview, light Updates at 680×520, failed-download/rollback controls, Featured and web-app form, and expanded observability controls. Source renders use synthetic state; they are not provider or backend acceptance. Full physical keyboard/screen-reader acceptance remains for the tester.
- Screenshot evidence is in the existing `hub-ui-qa2` visualization directory: `wayland-screenshot-2026-09-10_23-53-49.png` (dark Connect), `23-54-02.png` (light overview), `23-54-20.png` (narrow Updates), `23-54-35.png` (failure/recovery fixture), `23-54-48.png` (Featured), `23-55-04.png` (web apps), `23-55-55.png` (observability controls); the latter filenames share the full `wayland-screenshot-2026-09-10_` prefix.
- Native Arch package build passed. Archive ownership validation passed in the Linux build container; extracted packaged Panel.qml hash exactly matches reviewed source (`49be5c1b3014bfd9df8d70e8d931367738607fbd4b8c05595bd5bc0b18abd392`). macOS archive inspection first failed because its bsdtar lacked a usable zstd decoder; use the existing Linux container, not weakened validation or a new dependency install.
- Installed-system smoke: new 4 GiB, 2-vCPU QEMU/TCG overlay of the accepted 0.1.3 installed guest, CIDATA/SSH harness, port 2622, QMP socket `/tmp/maslow-ota-ui-020-qmp.sock`. Installed only the new Hub package with ordinary pacman checks; this direct transfer was confined to the disposable engineering guest and is not the Lenovo OTA delivery path.
- Setup was completed with synthetic Hermes confirmation and an `OTA Smoke` launcher was created before upgrade. Before/after hashes matched: onboarding `0137ad32685954b7d629c869eab6bb08a41da37a0de80c31e2e6cbf14fb02157`; launcher `3d058a137da972337caae13f3c30d8d12f4e470732a91fb4b04d0ff216b25991`. Quickshell remained PID 788. Installed version reports 0.2.0; Langfuse stayed inactive and no stack.env was created.
- QMP screenshot still reports inactive display, so this run does not establish installed graphical acceptance. The initial boot script's immediate pgrep raced shell startup; later SSH checks confirmed the shell. SSH diagnostic commands needed the observed session's `OMARCHY_PATH=/usr/share/omarchy` to read the runtime tool catalog and request reload. This is test-session environment, not a runtime fallback or product patch.
- The final installed-guest `omarchy-shell shell listPlugins` request timed out (`omarchy-shell is not responding`). The original shell PID remained present, but scheduled reload and plugin activation were not confirmed; late pgrep also saw transient Quickshell IPC clients. Do not equate the matched earlier PID/hash check or `reloadScheduled:true` with successful installed UI reload. The guest was asked to power off after the diagnostic; preserve the overlay for follow-up. Real Lenovo update/reload remains an explicit test risk, not a passing result.
- No real trace, internet A→B→rollback, physical Lenovo, or production support claim follows from these results. Do not repeat the known failing ARM-host backend emulation attempt. The user will report the installed UX after signed delivery.

## Signing and next action

Operator signing completed in `hub-evidence/ota-ui-020/signed-run.DR648T`. Coordinator reran the existing publication tool in dry-run mode against that bundle and the independently pinned public fingerprint: both exact package signatures/hashes, signed sequence-1 manifest, and signed catalog validated. The new package remains `498dc788...dc992` (58,332 bytes); baseline remains `3baa23be...20b` (35,138 bytes). Bootstrap script checksum is `7cc4eff684827b5a1e4780ffcc648728b550e58d00f09a386a0bb98b60208055`. GitHub Releases remains empty; Pages still serves the scaffold. Next action is explicit approval to publish these exact public packages and promote staging, followed by anonymous byte/signature verification. Do not ask the operator to sign again unless the payload or metadata changes.

Operator previously created an encrypted private key and reports a separate recovery backup. Public SPKI SHA-256 fingerprint reverified: `daacaa5aac138710a3950097b29a05abd3f69c9a8efad512321c45f3103d1ee4`. No private key/passphrase was read into agent context or copied into a build container or artifact.

Local operator script: sibling `hub-evidence/ota-ui-020/sign-staging.sh`. It verifies clean reviewed source, exact package hashes and public fingerprint, then uses existing release tools and interactive OpenSSL prompts to sign two packages, manifest and catalog. It prepares only allowlisted public output and runs publication in dry-run mode. It never sources the operator's plaintext .env. Shell syntax and JSON descriptor checks passed; the non-interactive guard was exercised and rejected correctly. Actual production-key signing has not been run by the agent.

Prepared staging sequence is 1; validity ends `2026-09-24T23:56:41Z`. Recheck remote channel state and expiry before publication; never reuse this sequence for different metadata after any publication. Each operator run creates a separate `signed-run.*` directory; preserve failed/partial attempts and inspect the successful directory explicitly.

**Resume:** after operator reports the signing command completed, validate that specific signed run, dry-run publication, and obtain exact-artifact promotion approval as required by Hub's delivery guide. Publish immutable signed packages, then signed staging Pages metadata; verify anonymous downloads and signatures before giving Lenovo bootstrap instructions. Do not describe the unsigned package as available over the air. GitHub release inventory was still empty at this checkpoint. Package publication, Lenovo enrollment, actual OTA apply/rollback, and experimental backend acceptance remain pending.

## Routing and lessons

Terra implemented UI-only changes; Luna implemented Python-only regressions; coordinator reviewed and refined completed-state routing, guided focus behavior, empty-state handling, observability access, tests, actual renders, package build and guest preservation. At most two workers ran concurrently; both were closed after integration.

- A stage strip is not a journey: implement real navigation and explicit next actions.
- Repeater visibility does not hide its generated sibling delegates; set delegate visibility explicitly.
- Completed setup must route to an overview, not a new welcome flow or a fresh completion write.
- Keep prototype approval, rendered UI, package installation, public signed delivery and hardware feedback as distinct evidence.
- Protected signing is an operator step. Do not repeat password setup or read the .env just because publication is waiting.
