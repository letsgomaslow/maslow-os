# Verified USB and pending native acceptance checkpoint

## Scope

The internal x86_64 candidate has been built, checksum-verified, written to USB, read back, and safely ejected. The user subsequently completed a fresh Lenovo ThinkPad installation and reported the native results below. Detailed remaining acceptance gates are still open. Do not restart implementation, add features or plugins, resume dictation troubleshooting, or rebuild unless acceptance reveals a blocker.

This documentation-only checkpoint follows the exact source commits used for the ISO; it does not change that artifact. The earlier `2026-09-05-native-lenovo-next-iso.md` remains historical evidence, not the current candidate status. Implementation was committed locally in all three repositories. After native testing, the user authorized pushing coordinated source and documentation to the downstream product branches; this does not authorize binary publication or a stable release claim.

## Exact build inputs

| Repository | Branch | Built commit |
| --- | --- | --- |
| Runtime, `maslow-os` | `main` | `62a817dab551f13f391191582ab3329d9f421d28` |
| Packages, `maslow-os-pkgs` | `maslow` | `2f1d53ceff7478ec515b2cd1db49c63277a6471d` |
| Installer, `maslow-os-iso` | `maslow` | `efc2d1fe768df593ec41c93e558e6af021ac9efc` |

These commits include Chrome fresh-install packaging/defaults, curated Dock and App Launcher defaults, Super+A, approved Maslow menu/dock branding, bounded AI setup readiness changes, and package-database handoff coverage. Preserve Omarchy package names, commands, plugin IDs, credits, themes, and update compatibility. Chrome packaging is for internal testing; public redistribution is not approved.

## Artifact and verification boundaries

- ISO: `/Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow OS - ISO/release/maslow-os-2026.09.05-x86_64-local.iso`.
- Size: 6,696,497,152 bytes.
- SHA-256: `ed1ab09f02daea1d28613f8089ebfd02b56e84f2f3ffdbbaa69afd8971490e6d`.
- Evidence directory: `/Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow OS Build Artifacts/2026-09-05-next-x86_64/`.
- Focused source checks passed for changed runtime defaults, plugins, onboarding, branding, package recipes, and ISO package/database handoff behavior. This is not a claim that a full repository aggregate suite passed.
- ISO assembly produced the image. Artifact inspection found the eight expected package archives and database entries, Chrome defaults, two curated plugins, keybinding/branding configuration, and nonempty staged online package databases. These checks do not prove a fresh installed desktop works.
- Some systemd setup commands crashed during emulated assembly. Native live boot is the first acceptance gate.
- The build wrapper exited 1 after image creation because of the ownership cleanup defect below. Do not describe the entire wrapper as successful.

## USB evidence

Fresh device enumeration identified PNY USB 2.0 FD, 8,021,606,400 bytes, external physical removable USB, at `/dev/disk4`. The user explicitly confirmed erasing that exact device; identity and ISO checksum were rechecked before writing. This identifier is historical: enumerate again and obtain exact-target confirmation before any future erase.

Initial macOS privilege attempts failed before writing. The authenticated Terminal write then wrote all 6,696,497,152 bytes, starting 2026-09-05 20:25:31 UTC and finishing at 20:48:24 UTC. The first slow read-only verification was stopped; no second write occurred. A new readback hashed exactly the ISO length and matched the SHA-256 above. Safe eject succeeded at 20:54:06 UTC, and subsequent external physical disk enumeration was empty. The user was told the USB was ready to unplug.

Evidence files outside Git: `usb-write.log`, `usb-verification.log`, `usb-readback.sha256`, and `native-acceptance.md` in the evidence directory. Keep the ISO and large logs outside the source repositories.

## Tester-reported native results

Evidence is the user's reports in this task on September 5, 2026, not a remotely executed acceptance suite. The boot-menu photo showed `USB HDD: pny USB 2.0 FD` and a separate internal Limine entry. The user subsequently reported installation complete; the earlier photo of the installed snapshot menu was not evidence of an ISO boot defect.

- Fresh installation completed and the desktop was usable.
- Before any Omarchy update, figlet, VS Code, Tailscale, and Zen Browser installed successfully through the normal app-install flow. This supplies native behavioral acceptance evidence for the package-database handoff fix.
- Chrome was confirmed as the fresh-install default browser.
- The Maslow dock icon and App Launcher were confirmed; Super+A opened App Launcher. The user also reported seeing the core logo changes.
- The user gave a general "everything works" report, then reported performing the supported update after being directed to `omarchy update`. No error was reported, but no update log or itemized post-update/reboot results were supplied.

## Remaining native acceptance checklist

The explicit fresh-install results above are accepted as tester reports. The following items need specific observations before complete acceptance is claimed:

1. After the update, reboot from the internal disk with the installer USB removed and confirm login/desktop, Chrome default, Dock, Super+A, and Maslow branding persist. Capture any update or boot errors and check failed services; emulated assembly had systemd command crashes.
2. Specifically verify both menu/dock logos, dock tooltip `Maslow OS`, no duplicate controls, and Super+Space, Super+Alt+Space, and Super+Shift+A. A broad smoke-test report is recorded but does not supply individual results.
3. Exercise the supported plugin update path and confirm Dock/App Launcher configuration and downstream display branding survive. An OS update alone does not establish plugin update behavior.
4. Exercise Codex, Claude Code, and Hermes configuration, readiness, failures, and provider sign-in with elevated permissions kept separate. Record completion/reopen behavior after reboot; never collect credentials.
5. Record settled idle CPU/memory, conditions, duration, and basic responsiveness. No matched Omarchy comparison has been performed.

Broader release gates remain separate: encrypted and unencrypted install coverage, recovery/rollback, reproducibility, and approved Maslow-owned signing/publication infrastructure. The encryption mode of this native run was not recorded.

## Original native test sequence

Retained as the repeatable sequence for the next fresh candidate; use the results above for this candidate's current status.

1. Boot the Lenovo from USB. Confirm the live installer responds before installation; capture boot errors or failed services. Confirm the internal installation target before destructive disk operations.
2. After a fresh installation, before any Omarchy update, install figlet and VS Code (a previously failing app) through the normal app-install menu. Do not manually refresh databases to hide a failure.
3. Confirm Chrome is the default browser; Dock and App Launcher work without setup; Super+A opens App Launcher; Super+Space, Super+Alt+Space, and Super+Shift+A remain intact.
4. Check both Maslow logos, dock tooltip `Maslow OS`, and absence of duplicate controls in the running desktop.
5. Exercise Codex, Claude Code, and Hermes readiness, configuration, and failure flows. Keep sign-in and elevated permissions separate; never record credentials.
6. Reboot and verify defaults persist, then test the supported OS and plugin update paths.
7. Record settled idle CPU/memory, measurement conditions and duration, and basic responsiveness. Do not claim Omarchy performance parity without a matched comparison.

## Deferred narrowly scoped build cleanup fix

`builder/build-iso.sh:406` runs `chown -R "$HOST_UID:$HOST_GID" /out/`. In `build-actual-2.log`, line 9014 records successful ISO writing; permission errors begin at line 9018 against older protected files under `/out/internal-ai-rebuild/`. This caused wrapper exit 1 and prevented its normal `-local` rename. The finished ISO was subsequently renamed and independently checksum-verified.

Before the next build, restrict ownership changes to exact outputs from the current invocation, excluding old output directories and unrelated artifacts. Test with protected prior artifacts and preserve genuine failures affecting new outputs. This fix is recorded, not implemented. Do not rebuild the verified ISO solely for this cleanup defect.

## Local work preservation

For the native-results documentation push, `git diff --check` passed in all three repositories. Runtime `test/maslow-brand`, packages `test/maslow-packaging`, and ISO `test/maslow-branding` passed in the cached Linux x86_64 preflight container. No feature code changed, no full aggregate suite was rerun, and no ISO was rebuilt. README and AGENTS updates describe the native results and preserve the remaining release gates.

At this checkpoint the package and ISO working trees were clean. Runtime contained an untracked `concepts/` directory unrelated to the built candidate; it was left untouched and excluded from this acceptance-record commit. Inspect any new work before staging future commits. Local commits are not an off-machine backup.
