# Phase 1 Hub fixes: honest updates, detected readiness, no dead Connect link

Date: 2026-10-05. Plan: fix what is broken → redesign onboarding → local hybrid Maslow Connect. This handoff covers Phase 1 source work only. Nothing is committed, pushed, signed, published or installed.

## Defects found on the Lenovo (installed Hub 0.3.2)

- `maslow-hubctl --json status` reported `Check failed (MANIFEST_EXPIRED)`; staging metadata expired 2026-09-24T23:56:41Z (sequence 5). Hub showed "Needs attention".
- Saved setup progress, not detection, drove readiness: Claude Code was signed in (`omarchy-setup-ai-tool status claude` → `signed-in`, `ready`) but showed "Selected"; Hermes showed "Ready — confirmed by you" while its runtime reported `attention` / `installed: false` (`desktop-runtime-attention`).
- `connect.maslow.ai` does not resolve; without `maslow-connect`, Hub's Connect action opened that dead address.
- A hardcoded "What's new · 0.3.2" GPT-Live/LiveKit tester note; Voice `ready: true` with `state: disabled`.
- Hub `main` is 6 commits behind `codex/gpt-live-test-release`, the branch Hub 0.3.2 shipped from.

## Source changes (uncommitted working trees)

`maslow-hub`, branch `codex/phase1-fixes` from `origin/codex/gpt-live-test-release` (`5c412c7`):
- `helper/updater.py`: a check rejected only for `MANIFEST_EXPIRED` reports `updateStatus: "paused"`, `state: "idle"` and a calm message; the next successful check clears it. Other failures still report `failed`.
- `helper/hubctl.py`: `status` adds `setup.detected` (sanitized `omarchy-setup-ai-tool status` for codex, claude, hermes, hermes-desktop, chatgpt-desktop, run in parallel, failing closed to `unknown`) and `setup.effective` (detected state outranks saved progress). `connect` raises `CONNECT_UNAVAILABLE` and launches nothing without the local bridge; the hosted portal constant is removed and `portalUrl` is kept empty for older panels. `voice status` reports `state: "off"` for an installed, ready, switched-off Voice.
- `ui/Panel.qml`: shows effective status with "Ready — signed in (detected)" versus "Ready — confirmed by you"; "Mark ready" only for tools whose sign-in cannot be detected; "Updates paused" label; expired metadata is no longer shown as a red error; Connections shows "Maslow Connect · Coming soon" with no button or URL when the bridge is absent; stale What's-new block removed.
- `release/renew-channel.py` + `release/signing.py`: renew-only signer. Verifies the published manifest and catalog against the trust root, changes only `sequence`, `generatedAt`, `expiresAt` (≤ 31 days), re-verifies the output. Both build scripts now share `signing.py`.
- `catalog/featured.json`: Connect entry is "Coming soon". Version bumped to 0.3.3 (`release/version.json`, `ui/manifest.json`). `docs/helper-contract.md` updated.

`maslow-releases`, branch `codex/ci-staging-renewal` from `main` (`f605c57`):
- `.github/workflows/renew-staging.yml`: weekly and manual. Uses environment `hub-staging-signing` secrets `HUB_RELEASE_SIGNING_KEY` (the existing key, still encrypted) and `HUB_SIGNING_PASSPHRASE` (passed to OpenSSL through `-passin env:`, never argv), renews, verifies against `bootstrap/release.pem`, fails if under 10 days remain, commits only the four `hub/staging` files, requests a Pages build and waits until Pages serves the new sequence.
- `tools/renew/*.py` vendored from the Hub repo (canonical there) so CI needs no token for the private repo. `AGENTS.md` documents renew-only key custody.

`maslow-os`, branch `codex/phase1-docs` from `main` (`450637e6`): README "What makes Maslow different" (Hub, Voice, control); `manual/02-getting-started.md` no longer points at a nonexistent verified release and drops the upstream first-person aside.

## Evidence

- Hub: 137 Python tests ran; the only failures are the same 25 as the untouched baseline (19 failures, 6 errors), all in `test_voice_delivery` / `test_voice` because their fixtures need root-owned files (`VOICE_BUNDLE_INVALID: ... must be root-owned`). New tests: paused/recovery and non-paused failure (`test_updater`), renewal content/tamper/key-mismatch/window/key-mode (`test_release_renewal`), Connect without/with bridge, detected readiness, fail-closed detection, effective rules, Voice off (`test_hubctl`). `node tests/ui-contract-test.mjs` passes with new assertions. Version check and `git diff --check` pass. Root-only Voice tests were not run as root.
- Published staging `manifest.json` and `catalog.json` verify against `bootstrap/release.pem`, which is byte-identical to the Lenovo's installed `/usr/share/maslow-hub/trust/release.pem`.
- Live read-only run of the new helper on the Lenovo: `updateStatus: paused`, `state: idle`; Codex and Claude Code `ready` (detected), Hermes and Hermes Desktop `needs-attention`, Hindsight `action-required`; `connectState: unavailable`, `portalUrl: ""`; Voice `state: off`.
- Rendering: the new Panel was loaded in a separate offscreen Quickshell instance (normal shell untouched) with Commons/Ui copied from `$OMARCHY_PATH/shell` and `maslow-hubctl` shimmed to the source helper. No QML errors. Inspected PNGs of Setup, Customize, Connections, Voice and Updates (flattened onto the theme background) show the expected text. This is a rendered-UI check, not the Docker/Weston harness and not installed acceptance. It caught the red expired-metadata error, which was then fixed and covered by a contract test.

## Remaining gates (need the operator)

1. Operator decision 2026-10-09: move renewal signing to GitHub, replacing the earlier "no signing secrets in GitHub workflows" rule (documented in Hub `docs/github-delivery.md` and `maslow-releases/AGENTS.md`). Write access to `maslow-releases` is now release-signing access. The operator uploads the encrypted key and passphrase from the Mac with `gh secret set --env hub-staging-signing`. A manual dispatch then restores staging updates immediately, replacing the one-time Mac signing step.
2. Approve pushing `maslow-hub` `codex/phase1-fixes` and a PR into `main` (it also carries the 6 shipped-but-unmerged 0.3.2 commits).
3. Build and sign Hub 0.3.3 on the Mac through `docs/github-delivery.md`, publish, then install on the Lenovo and check the items above in the real shell.
4. Push `maslow-os` `codex/phase1-docs` and open a PR.

Next action: operator adds the signing secret and runs the renewal workflow once.
