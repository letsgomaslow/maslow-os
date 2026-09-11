# Hub recovery release after Lenovo feedback

## Scope and evidence

The user reported successful one-time internet trust enrollment, then confusing update discovery and repeated Observability installation failures. Screenshots show the 0.2.0 Observability command family is present, but do not independently establish the installed package version, completed OTA transaction, preserved state or rollback. The first diagnostic confirmed Docker active with socket permission denied; `id -nG` showed `maslow wheel`, and the Docker group had no listed member. Memory passed and Docker storage could not be measured. The user followed advice to add Docker access and reported a subsequent failure; its cause is unknown. Do not assume the later failure is another permission problem or that repeated button presses corrupted data.

Review of the exact accepted runtime source `dca4d9c` confirms Docker group exclusion is intentional. `install/config/docker.sh` records the security rationale and the existing `omarchy-setup-security-sudoless-docker` consent flow. The earlier raw `usermod` troubleshooting advice bypassed that supported experience and was not a product-level solution. No default permission grant, socket chmod, root Hub process or security-hold bypass is authorized by this repair.

## Root causes in the product experience

- Terminal installation was detached and returned `terminalLaunched` immediately. QML cleared its busy state when the launcher helper exited, not when setup completed. Backend locks do not make this understandable or prevent multiple terminal launch requests by themselves.
- The installer computed failed requirements but returned only `PREFLIGHT_FAILED` with a generic message. The GUI install button did not require a passing preflight.
- Docker permissions assumed by the adapter conflicted with fresh-install security defaults. Installed Docker was incorrectly treated as a sufficiently prepared infrastructure dependency.
- Real QML screenshots used fixture data. The 0.2.0 installed package smoke preserved state but its QMP display was inactive and shell IPC timed out. Real backend startup/traces had not passed on native x86. These gaps were documented but not resolved by the experiential staging release.
- Historical resume documents retained conflicting current/next-action statements. Use the newest dated handoff and explicitly separate source, artifact, public channel and hardware evidence.

## Authorized repair

Prepare Hub 0.2.1 as a recovery-focused package without an ISO rebuild. Track installation across terminal handoff and Hub reopening; expose bounded stages and safe errors; prevent conflicting actions; check requirements automatically; make updates visible from the opening screen; provide an allowlisted diagnostic report with no automatic upload. Docker access remains an explicit runtime-managed security choice, not an automatic permission grant. Rootless Docker or a narrow privileged backend adapter would require a separate reviewed implementation; this release does not pretend to provide either.

Keep the signed 0.2.0 and exact 0.1.3 packages immutable and available for recovery. Preserve onboarding, launchers, provider configuration, backend credentials and trace volumes. No backend image/database upgrade is part of this repair. Source is private; public staging requires a reviewed artifact, protected operator signing, and anonymous verification. Do not tell the user to update until that release is actually published and verified.

## Verification and next action

Implementation is committed in the private Hub checkout at `02caa562c626a4bae7a16e86187bd6d80b73e3ef`, following `1d12d8a5ad9b6c9111d59dc49489671c740c3e44`. Runtime/package behavior and ISO are unchanged. Public staging was checked anonymously and remains sequence 2 / Hub 0.2.0. The Lenovo should remain unchanged until signing, explicit staging publication and anonymous verification complete. Native backend startup/real trace acceptance is still a distinct gate, not established by simulated progress or permission checks.

The repaired Hub can be delivered through its existing package-owned update paths. New system dependencies, runtime privilege interfaces and fresh-install trust defaults remain separate package/runtime/ISO concerns. Rebuild media after the existing-install migration works, not as a substitute for proving it.

## Completed recovery evidence

- Sol handled bounded adapter/operation work and Terra handled QML. Coordinator reviewed trust boundaries, corrected the fast-child launch-lock race, added regression coverage and inspected rendered output. No new dependencies, root grant, source publication or backend database upgrade.
- `bash release/check.sh`: 87 Python tests plus UI contract, guided navigation/preservation and recovery fixture checks passed. `git diff --check` passed. Tests include reservation coalescing, read-only interrupted-operation reporting, safe failures and diagnostic redaction. These do not prove every possible subprocess interruption on hardware.
- Final package: `../hub-evidence/ota-recovery-021/final-packages/maslow-hub-0.2.1-1-any.pkg.tar.zst`, 67,817 bytes, SHA-256 `e581f7f3cb1a1d2f23b88139c6fea545e8f866e7bb655e17119ef7023fffe946`. Linux package ownership/identity checks passed using package recipe revision `e4fab06`. The earlier local 0.2.1 archive with hash `0e00e70b533b74bb8fcb9f62c675f28d45e8ca381ca48f97e67e2275fe2e2d5f` is superseded and must not be published.
- Disposable existing-system QEMU/TCG overlay: 2 vCPU, 4 GiB RAM. Normal test-key-signed HTTPS channel, normal privilege prompt and package manager completed 0.2.0 to initial 0.2.1, rollback to 0.2.0, then final 0.2.1. Test channel sequences 100/101 are isolated from public staging. One final-apply prompt lost its controlling tool session; it was cancelled before package installation and retried successfully. History correctly records that failure. Do not interpret it as a backend installation failure.
- Final onboarding SHA-256 stayed `0137ad32685954b7d629c869eab6bb08a41da37a0de80c31e2e6cbf14fb02157`; seeded test web-app launcher stayed `3d058a137da972337caae13f3c30d8d12f4e470732a91fb4b04d0ff216b25991`. No credentials or trace volumes were copied into Hub backups. Existing shell PID 796 survived package update/rescan.
- Real Quickshell/software-rendered Weston PNGs inspected: permission block, waiting for terminal, active installation, failure, narrow window, light theme, diagnostics, updates and rollback. Fixture directory is `/Users/r.david/.codex/visualizations/2026/09/08/01a081a3-6a4a-71f3-8892-635bde4bb7d3/hub-ui-qa2/recovery-021`. Fixture states are not backend proof; full keyboard/screen-reader acceptance remains open.
- Actual guest QMP image `../hub-evidence/ota-recovery-021/installed/final-021.png` confirms installed 0.2.1 UI and update history. Idle display initially reported inactive; waking revealed a crashed-lockscreen failsafe. Authenticated SSH recovery in the disposable guest restored the display. This is a separate harness/runtime issue, not evidence of an observability failure. The same-version local rebuild retained the earlier status-label QML in the live process even though the final file on disk was correct; do not reuse version numbers for public artifacts. Final source status-label regression passes, but that last label change was not independently confirmed in a fresh-process installed render.
- Installed diagnostic command ran and reported actual 4 GiB safeguard and Docker permission failures without granting access. This constrained guest is not a supported Langfuse hardware benchmark. Real backend startup, Hermes trace receipt and Lenovo recovery are still unverified.

## Immediate next action: protected signing, then staging publication

Unsigned public-only bundle is `../hub-evidence/ota-recovery-021/public-sequence-3/bundle`. It retains the exact signed 0.1.3 and 0.2.0 rollback packages and existing signed catalog. Proposed staging sequence 3 expires September 24, 2026; re-check current public sequence and expiry before promotion. Manifest SHA-256 is `4369f9688ed45ef0dc43d549133d920252a8640760ccdb4df3d31dae0c3db882`.

The operator runs `bash /Users/r.david/.codex/worktrees/43ab/hub-evidence/ota-recovery-021/sign-recovery.sh` directly on the Mac. It checks exact source revision, package/manifest hashes and pinned public fingerprint, asks through OpenSSL twice, and verifies the resulting public delivery bundle. It never loads `.env`, publishes assets or changes Lenovo. Script syntax checked; protected signing has not been performed by the coordinator.

After operator completion, inspect the new signed-run directory, run existing delivery verification, explicitly publish immutable artifacts before Pages sequence 3, and independently fetch/verify public signatures and package hashes. Only then tell the user to install Hub 0.2.1. Existing 0.2.0 UI may still require its Updates tab for this one transition; the improved entry point arrives with 0.2.1. Do not re-enroll trust, ask for another ISO install or promise the later unknown backend failure is fixed without fresh evidence.
