# Hub USB and user follow-up

This supplements [the engineering handoff](2026-09-08-maslow-hub.md). See [development status and backlog](../maslow-development.md) for next work. It does not change the ISO or imply production release readiness.

## Verified USB preparation

- Source: corrected internal Hub 0.1.3 ISO, `maslow-os-2026.09.08-x86_64-hub-0.1.3-sizing-local-internal.iso`, 6,485,413,888 bytes.
- Source and full ISO-length USB readback SHA-256: `c3ee08889eaa50bf2843ae6d0bdc45f8549569f956159421b1e67b98a31b363a`.
- Target was explicitly approved by the user, then re-enumerated: external physical USB 2.0 FD, 8,021,606,400 bytes. `/dev/disk4` was its identifier for this operation only; it is not a reusable target instruction.
- Initial administrator-authorized app write failed opening the raw device with `Operation not permitted`, before writing any bytes. The approved Terminal route rechecked source size/hash and target identity, unmounted it, wrote exactly 6,485,413,888 bytes, synced, and hashed the same byte length from the raw USB.
- Write completed in approximately 22 minutes. Full readback matched; safe eject succeeded; external physical disk enumeration was empty afterward. The previous USB installer was overwritten; the source ISO and Mac internal disk were not modified. This was installer replacement, not secure erasure of all USB capacity.
- Local evidence: sibling `hub-evidence/usb-0EXiy4-verified.log`. The machine-specific evidence root is `/Users/r.david/.codex/worktrees/43ab/hub-evidence/`. Large artifacts and operational logs remain outside Git.

## User report and remaining hardware checks

After the USB/Lenovo testing handoff, the user said “That worked” and requested this documentation/commit checkpoint. On clarification, the user explicitly confirmed “Lenovo installation reached desktop.” Record fresh installation reaching the desktop as passed, tester-reported hardware evidence, not a remotely observed full acceptance suite. The following remaining results must not be inferred from that confirmation.

- [x] User confirmed fresh Lenovo installation reached desktop.
- [ ] Record installation/encryption mode.
- [ ] Reboot from the internal disk with USB removed; record login, Hub, and branding behavior.
- [ ] Confirm normal fresh app installation before the first `omarchy update`; no manual database repair to hide failures.
- [ ] Open Bitwarden and test locking/unlocking with test data. Its package is retained; personal-vault isolation from agents is not implemented or verified.
- [ ] Record onboarding complete/defer/reopen behavior, offline Observability skip, and provider readiness separately from sign-in.
- [ ] Create/open/remove a web app; retain existing browser data. Earlier VM opening reached Chrome terms only, not loaded page-content acceptance.
- [ ] After approved production trust/channel bootstrap, test a real Hub update, preserved state, rollback, and terminal recovery on Lenovo. The shipped internal ISO currently has no production update trust.
- [ ] Record supported OS/plugin updates, reboot survival, basic performance, and any error screenshots without credentials.

Production signing, anonymous immutable artifact hosting, source/artifact publication, Chrome redistribution, and detailed native acceptance remain separate gates.
