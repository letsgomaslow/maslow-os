# Hub alpha closeout: delivery works; support readiness remains open

## Resume here

Hub 0.2.1 is published on internal staging and the tester's latest Lenovo screenshot displays current 0.2.1 / Up to date. Do not ask for signing, trust enrollment, another 0.2.1 install or an ISO rebuild. The next engineering recommendation is a scoped support-readiness design, not more features or another blind installation attempt. This closeout authorizes documentation/commits only; no support service, upload, device access or new release was implemented.

## Evidence and exact revisions

- Private Hub source: `02caa562c626a4bae7a16e86187bd6d80b73e3ef`, including recovery implementation `1d12d8a5ad9b6c9111d59dc49489671c740c3e44`.
- Public distribution: `8791c37972525af0edcbe6ee980d70b7f97d4577`. Staging sequence 3, catalog sequence 1, versions 0.1.3 / 0.2.0 / 0.2.1. Publication and anonymous signature/hash verification completed September 11; not repeated for this documentation-only closeout. Metadata expires September 24, 2026 at 23:56:41 UTC. Renew before expiry through protected signing and explicit promotion; never bypass expiry.
- Released 0.2.1 archive: 67,817 bytes; SHA-256 `e581f7f3cb1a1d2f23b88139c6fea545e8f866e7bb655e17119ef7023fffe946`. Preserve immutable bytes and both prior recovery packages.
- Package checkout: `e4fab062dc6631f1a14aadeb57f0f88b2ee05fff`; ISO checkout: `d96a3ee563df5a1eb76a711c7b408c0d1d0137cb`. These are current source pointers, not replacements for the accepted ISO build inputs recorded in the development index.
- Previous runtime documentation checkpoint: `6facfab2`. The [September 11 recovery handoff](2026-09-11-hub-recovery.md) retains test commands, archive provenance, local evidence paths and limitations.
- Latest user-supplied image: `/Users/r.david/Downloads/PXL_20260911_094426751.MP.jpg`. Keep the personal photo outside Git. It shows 0.2.1 / Up to date, Observability skipped, no running operation, failed requirements, and a message that configured Docker access has not reached the current session. The user reports continuing errors and rejects screenshot-driven troubleshooting as impractical.

## What is confirmed, inferred and still unknown

Confirmed from earlier terminal images: Docker was active but the user could not access its socket; the session groups were `maslow wheel` and Docker membership was absent. Confirmed from reviewed runtime code: restricted Docker access is an intentional security default, not a reason to silently grant root-equivalent access.

The latest screenshot confirms what the Hub reports, not a fresh independent inspection of group membership or process credentials. A stale login session is the current diagnostic classification. Whether the laptop was fully restarted, whether the session subsequently refreshed, and whether a later backend attempt has another cause remain unknown. Do not claim every reported error is Docker or that repeated clicking corrupted anything.

User report plus visible 0.2.1 establishes tester-reported OTA arrival and running UI. It does not establish Lenovo rollback, full state preservation, backend readiness, real Hermes trace receipt or hardware resource support. Previous 87-test and emulated update/rollback evidence remains useful but is not a substitute for those gates.

## Root-cause analysis

| Finding | Evidence / confidence | Corrective direction |
| --- | --- | --- |
| Installer expected usable Docker, while fresh OS access is deliberately restricted | Confirmed source and initial terminal output | Treat installed, authorized and active-in-session as separate conditions; preserve explicit consent. |
| Terminal launch was treated as completion | Confirmed prior QML/helper behavior; addressed in 0.2.1 | Persist operation stages and verify outcomes rather than launch acknowledgements. |
| Generic requirements failures left users guessing | Confirmed initial PREFLIGHT_FAILED and source behavior; partially addressed in 0.2.1 | Show one blocker and its next action; retain useful safe details. |
| Independent status messages contradict each other | Latest image combines skipped, check requirements and Action completed | Define authoritative operation/setup states; action completion must not imply feature success. Test realistic sequences, not only isolated fixtures. |
| Engineers lack remote failure evidence | Reviewed diagnostics only returns a local report with uploaded=false; no transport was built | Add a reviewed support-report workflow with consent and receipt tracking. |
| Diagnostic snapshot lacks a complete causal timeline | Current report provides allowlisted health/status, not a durable correlated support history | Record bounded structured events across restart, permissions, retries and updates. Avoid raw configuration/log dumps. |
| Test coverage missed the whole user journey | Native backend/real-trace gates were open; emulated smoke and visual fixtures passed narrower checks | Deliberately test blocked access, stale session, reboot/resume, service failure and recovery on representative x86 systems. |
| Release handoffs retained stale next actions | Conflicting current/scaffold/signing instructions in index | Keep one current checkpoint; clearly mark historical sections and link forward. |

The core gap is supportability and setup lifecycle management. Signed delivery is working, but that alone is not a mature operating-system support foundation. Another ISO does not supply remote visibility or resolve an unknown backend cause.

## Recommended next steps, ranked by dependency and lift

These are proposals, not authorized deployment or data collection. S = bounded work, M = coordinated implementation/testing, L = security-sensitive multi-component work; not calendar estimates.

| Priority | Work | Lift | Acceptance / decision |
| --- | --- | --- | --- |
| P0 | Define support-report schema, consent, storage lifetime and access policy | S | Explicit list of allowed fields, excluded data, recipient, retention/deletion and operator access. Choose hosting only after user approval. |
| P0 | Durable local event timeline and coherent restart/resume UI | M | Correlate operation/version/stage/time/safe error; bounded storage; persists across closing/reboot; distinguish restart required, failure, cancellation and success. No misleading Action completed. |
| P0 | Preview and send support report, returning a support reference | M | Private authenticated serverless intake; size/rate limits; no embedded shared administrator secret; retry/offline states and duplicate protection; operator can retrieve by reference. Verify expiration/deletion and failure recovery. |
| P0 | Fault-driven acceptance using an installed guest and real x86 backend | M | Reproduce denied access, stale session, interrupted download, service failure, low disk and reboot; report alone identifies the failed stage without screenshots. Prove real Hermes trace before calling Observability working. |
| P1 | Renew signed metadata before September 24 expiry | S / operator signature | Increasing signed sequence, anonymous verification, immutable old packages; no ISO rebuild. |
| P1 | Optional time-limited diagnostic session | L | Separate approval and threat model; fixed read-only checks, visible consent, expiry/revocation and audit. No arbitrary shell, filesystem browsing, vault access or automatic repairs. Defer until reports prove insufficient. |
| P2 | Resume broader features, Connect and marketplace | Separate scopes | Support loop and native observability acceptance first; Connect remains parked and separate. |

The user prefers serverless and no hosted customer AI workloads. A private report receiver/storage would be a small separate hosted support dependency, not zero infrastructure or guaranteed zero cost. Provider, region, retention duration, identity/device authorization, spending controls and access mechanism remain undecided. Do not use public GitHub issues/releases for device reports. No need to couple this work to Connect, Clerk or Composio without a reviewed reason.

Reports exclude provider credentials, vault contents, conversations, file contents and trace payloads by default. Redaction alone is not a security guarantee: prefer an allowlist of structured fields, test sensitive-data fixtures, and require a separate explicit review for any expanded diagnostic attachment. Nothing uploads automatically. Remote diagnostics must not become a hidden remote administration channel.

## Lessons and execution discipline

- Treat support readiness as alpha acceptance, not optional polish after shipping a feature.
- A working package delivery path and an operational backend are independent results; name them separately.
- The tester should reproduce and report an outcome, not repeatedly translate terminal output for engineering.
- Consent that changes access may require a new session; setup must guide and verify that transition instead of repeatedly recommending installation.
- Existing local Langfuse records AI activity; it cannot replace platform setup/support diagnostics, particularly when Langfuse itself cannot start.
- Keep exact immutable release identities. Same-version local rebuilds can retain cached QML, so do not extrapolate their render behavior to a clean public update.
- Separate emulation/idle-lockscreen problems from backend defects. No UTM; keep Docker/Weston/real Quickshell and QEMU/TCG evidence explicit.
- Use at most two disjoint implementation workers where useful. A documentation closeout is cheaper and clearer to coordinate directly. Do not report unperformed model routing or new test runs.

## Closeout scope and next context

Runtime index and handoffs are the status authority; Hub AGENTS.md points here. Source fixes were already committed. This closeout changes documentation only and requires link/revision checks, staged-scope inspection and git diff --check, not an ISO rebuild or repeated unchanged application tests. No new package, upload endpoint, remote session, secrets access or Lenovo modification.

Unrelated untracked concepts, extras, an orbit test and .DS_Store files in the saved runtime main checkout remain untouched. Local evidence scripts, packages, personal photos and signing material remain outside source commits. Documentation commits are local unless separately pushed; public release publication is already recorded above. Next context should start with this document and propose the smallest consent-based report workflow before implementing infrastructure.
