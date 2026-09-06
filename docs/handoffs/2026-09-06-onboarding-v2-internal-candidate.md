# Maslow AI onboarding v2 — internal x86_64 candidate

The native Welcome → Connect → Open implementation is committed on isolated `codex/ai-onboarding-v2` branches. It supports Maslow light/dark themes and preserves Omarchy runtime identity, update sequencing, shortcuts, credits, and the temporary runtime package hold. The earlier September 5 laptop-tested ISO is unchanged. This is an internal candidate, not a stable channel release.

## Build identity

| Input | Exact built commit |
| --- | --- |
| Runtime | `de97121f2b798d50a4aed8173839ef48e40f0e54` |
| Packages | `b9f64d1994385fc84c275c7da4646f76f4689741` |
| ISO | `2e1b37d6bc3aa658905e043a95f0355de7e52548` |
| archiso submodule | `424e78130db2af6c1ceb55b442d7914b1109ff2b` |

All three explicit build checkouts were clean. Builder and host wrapper both exited 0. The runtime package is `4.0.0.r2068.gde97121-1`. Direct extraction confirmed that the packaged panel, launcher, adapter, and runtime helper match the built source byte-for-byte.

Artifact: `maslow-os-2026.09.06-x86_64-onboarding-v2-internal-r2.iso`, **6,696,497,152 bytes** (approximately 6.24 GiB).

SHA-256: `f691c4cd94624074cc1126565e639813d813dff583c30dcca3085c9d34270aa4`.

The image, adjacent `.sha256`, and `onboarding-v2-r2-manifest.json` are in the local build-artifacts `onboarding-v2/release/` directory. Revision 1 is preserved but superseded because native acceptance exposed a false first-login acknowledgement timeout. No old image was overwritten. Later documentation commits are not part of the built runtime.

## Implemented behavior

- Native Quickshell presentation reuses shared controls, fonts, and theme state. It includes live theme switching, keyboard operation, compact/scaled layouts, a finite transition, and reduced-motion support. No browser runtime or new dependency was introduced.
- ChatGPT via Codex and Claude Code have equal account choices and official sign-in handoffs. One account is sufficient when Hermes is deferred. Provider-reported authentication is distinct from successful inference.
- Hermes is optional. Built-in memory is the default; Honcho and Hindsight open guided setup and remain user-confirmed without machine proof. No questionnaires, personal context transfer, SOUL.md creation, dictation, plugins, or universal MCP manager were added.
- Optional desktop installation, package presence, runtime ownership, and readiness have separate states. ChatGPT Desktop has separate account/memory behavior. Incomplete Hermes Desktop bootstrap shows Needs attention and Open setup rather than indefinite Preparing; the fixed packaged launcher remains usable for recovery.
- Progress-only resume choices preserve schema compatibility and unknown fields. Historical user-confirmed ready values are not promoted to verified account or inference status. Finish for now remains available.
- Read-only probes are bounded, sanitized, and cancelled as process groups. Detached login windows and package transactions are not killed by closing onboarding. No credential files are read and no raw provider output is exposed.
- First-login launch makes one summon with a bounded 60-second acknowledgement budget after the completed/deferred skip gate. It does not retry or mask failures. Manual launch keeps the existing timeout behavior.
- ISO output cleanup now owns only new regular files in the invocation's private output directory and refuses destination collisions; previous artifacts are not recursively modified.

See [adapter contract](../ai-onboarding-adapter.md) and [progress-state contract](../ai-onboarding-state.md).

## Changed source areas and commits

Runtime commits: `28903077` progress choices; `9ef3fba4` runtime adapter and fixtures; `003cc320` native panel; `89d75053` incomplete desktop recovery; `de97121f` first-login acknowledgement fix and regression tests. Primary files are `shell/plugins/maslow-ai-setup/Panel.qml`, `bin/omarchy-setup-ai{,-state,-tool}`, `install/helpers/agent.sh`, the native panel opacity rule, focused tests, and contract documentation.

ISO commits: `2572326` output ownership; `41b3917` onboarding flow acceptance; `b402a34` signed-out core acceptance; `5c61796` graphical session display; `21a34f1` actual desktop window/process lifecycle; `2e1b37d` automatic-only first-login acceptance. Package recipes are unchanged.

## Verification and evidence boundaries

### Automated source checks

Focused authentication/parser, missing binary, PATH override, timeout, cancellation, orphan process, ownership, interrupted bootstrap, memory fallback/defer, progress-state, panel, first-run, and QML plain-text checks passed. Fixtures cover signed-in/out and error states; fixtures do not establish real subscription access. The final CLI aggregate passed. Relevant shell syntax, diff checks, brand checks, package metadata and core recipe checks passed.

The broader Linux runtime shell run exercised 240 test files. One new QML plain-text declaration issue was corrected and the full focused scan passed. The other 26 failures reproduce on unchanged baseline `ae1041b4` in the same environment. Missing platform tools and existing test assumptions prevent calling the aggregate green. ISO Python tests: 74 passed. ISO shell coverage excluding its existing PTY dashboard fixture passed in an x86_64 guest, including output cleanup. That existing PTY assertion remains failing, so the full ISO aggregate is not claimed green.

### Directly observed native source/UI tests

A disposable development guest, with candidate runtime source copied in, was used to inspect Welcome, Connect, memory options, Open, errors, recovery, and resume in light/dark themes. Live theme switching, 125% scaling, a narrow tiled layout, keyboard scrolling, reduced motion, and opening/closing frames were checked. This is native Quickshell evidence, not an HTML simulation; it is separate from fresh-image acceptance.

Actual ChatGPT Desktop and Hermes Desktop setup windows opened. The onboarding Open ChatGPT Desktop button launched its window and the app stayed open after onboarding closed. Hermes Desktop failed upstream Node-dependency bootstrap in the emulated guest; the final recovery state and actual Open setup window were verified. A completed usable Hermes Desktop runtime was not established.

### Fresh revision 2 image

Unattended installation and installed-system reboot passed from the exact R2 ISO. The integration runner exited 0 and all three selected scenarios passed:

| Scenario | Evidence run | Result |
| --- | --- | --- |
| Fresh installation | `20260906-051231-install` | Installed and rebooted successfully |
| Package database handoff | `20260906-053311-package-database-handoff` | Online databases seeded; temporary offline repository removed; `figlet` installed and ran before any OS update |
| Automatic first login | `20260906-053414-onboarding-first-login` | Clean user state; launcher completed without optional-failure warning; native Welcome opened without manual launch; progress recorded without completion |
| Onboarding interactions | `20260906-053603-onboarding-actions` | Return key, account choices, Hermes and memory defer/restore, Open, Finish for now, close/resume, actual Bitwarden window/process lifecycle, and unchanged package inventory passed |
| Reboot persistence and update hold | `20260906-054454-onboarding-reboot` | Saved choices survived; deferred onboarding did not reopen; updater executable and all four runtime exclusions verified after virtual-network recovery |

The reboot assertions passed after a test-environment intervention: the emulated VirtIO Ethernet device had carrier but no IP address and NetworkManager stayed unavailable. A QMP virtual cable disconnect/reconnect restored SSH immediately. No guest network configuration or service was changed, and onboarding state was not modified. Local console screenshots and logs preserve this observation. Networking across this reboot is not a clean pass; a read-only harness comparison found no causal source change. The precise cause is unproven and requires native confirmation.

The automatic first-run log records the launch starting at 05:35:42 UTC and completing at 05:35:46 UTC. The actual captured R2 Welcome window was inspected. Test-only autologin exists only in disposable VM overlays, not in the ISO defaults.

The performance collector completed its 300-second settle and 30-second sample: CPU 98.64%, memory 1,530,060 / 2,960,860 KiB. The captured screen and process snapshot show the animated screensaver active. This TCG sample is **not** an idle-desktop benchmark, minimum hardware requirement, or laptop-performance signoff.

Revision 1 separately passed fresh offline AI runtime checks, including package/command availability for Codex, Claude Code, and Hermes and Hermes built-in memory status. The runtime payload for those tools is unchanged in revision 2; this result is retained as revision 1 evidence, not relabeled as an R2 execution.

### Remaining limits

- No real ChatGPT/Codex or Claude account was signed in, and no subscription-backed inference was performed. Account access and expired-session behavior are not live-account verified.
- The pinned Hermes CLI forces one-shot approval bypass and accepts configured fallback providers. It cannot enforce the requested restricted response check. This candidate intentionally returns **Check unavailable** without invoking Hermes; guided setup and deferral remain available. No automatic response-success path is claimed.
- Hermes Desktop's completed runtime/provider handoff remains unverified because bootstrap failed in the emulated guest. Its honest recovery state is implemented and tested.
- One R2 reboot needed virtual cable reconnection to restore guest networking. State/no-reopen checks subsequently passed, but clean reboot networking remains unverified for that run; check both Wi-Fi/Ethernet and reboot on the laptop.
- Existing critical update/keybinding notifications can overlap the first-login header until dismissed. This remains a first-impression polish item; the false launcher-failure notification was fixed separately.
- TCG emulation with an active screensaver is not idle-desktop or laptop performance acceptance. A full supported OS update and post-update acceptance were not run; read-only hold/exclusion checks are separate evidence.

## Laptop acceptance checklist

1. Verify the R2 SHA-256, then write it to a separate USB. Preserve the earlier tested USB/image. Laptop disk erasure is a separate tester action.
2. Fresh-install on an x86_64 laptop. Before the first OS update, install `figlet` and an ordinary application through the normal helper/menu.
3. Confirm Welcome opens automatically without a setup-failure notice. Check all three steps in both themes, at laptop scaling, using keyboard only and reduced motion. Switch themes while the panel stays open.
4. Sign into ChatGPT/Codex and Claude Code independently. Confirm one connected account suffices with Hermes deferred, and test cancelled/offline/expired sign-in without treating it as success.
5. Try Hermes guided setup and verify its provider access separately. Expect Check unavailable for this pinned release. Confirm Set up Hermes later and the normal coding-tool interface remain usable.
6. Check built-in memory and optional memory wizards; distinguish user confirmation from a verified connection.
7. Install/open each optional desktop separately. Verify its actual window, finish setup, and refresh ownership/readiness. ChatGPT Desktop must not imply inherited Hermes memory or authentication.
8. Close/reopen during external installation; defer, reboot, and resume. Confirm Wi-Fi/Ethernet reconnect automatically. Completed/deferred users should not automatically see onboarding again.
9. Exercise only the supported `omarchy update` path with the runtime hold preserved. Record post-update evidence separately from fresh installation.

## Orchestration and delivery boundary

Sol handled runtime contracts and integration, Terra the native layout, and Luna bounded cleanup/fixture work. The coordinator integrated, reviewed native screens, and built/tested the ISO; Astra performed one targeted first-login defect review. Sol also reviewed the isolated reboot-network harness issue. At most two workers were active together and all were closed. No dollar-cost or unattended completion-time promise is made.

Source commits and internal artifacts are local. No public source push, binary/package publication, laptop erasure, or stable channel promotion was performed.
