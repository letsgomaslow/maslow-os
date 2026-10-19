# Continue development on the 2012 Retina MacBook Pro

Updated October 18, 2026. The user reports successful Maslow installation on the 15-inch Retina 2012 MacBook Pro and several remaining problems. No itemized native test results, installed package inventory or reproducible symptoms have been collected yet. Start with [the native handoff](handoffs/2026-10-18-macbook-native-development.md), [current progress](maslow-development.md), [repository ownership](lenovo-development.md), and each repository's AGENTS.md. The historical Lenovo branch examples are not instructions for this candidate.

## Obtain the exact source from GitHub

The user requested GitHub delivery so development can continue on the installed 2012 MacBook Pro, with shared instructions for Claude and Codex. The user clarified that there is no Mac mini setup. Runtime main receives this documentation and the evidence handoffs only. Experimental runtime/Qt/installer/Hub code stays on named candidate branches because startup gates still fail. This is source backup and development continuity, not package/ISO publication or production-code promotion.

Start with runtime `main` to read the handoff. For development of this installed candidate, create fresh sibling clones outside installed paths. Product branches remain runtime/Hub `main` and packages/ISO `maslow`; the branches below are deliberate experimental checkouts. GitHub access to these private repositories must already work; use your own normal GitHub authentication if needed, without copying tokens or release keys from the build Mac.

```bash
bash <<'BASH'
set -euo pipefail
maslow_workspace="$HOME/Projects/Maslow-Candidate-20261018"
if [[ -e $maslow_workspace || -L $maslow_workspace ]]; then
  echo "Workspace exists; inspect and reuse it rather than overwriting it."
  exit 1
fi
mkdir -p "$maslow_workspace"
cd "$maslow_workspace"
git clone --branch codex/omarchy-quattro-20261017 https://github.com/letsgomaslow/maslow-os.git maslow-os
git clone --branch codex/hub-private-state-20261017 https://github.com/letsgomaslow/maslow-hub.git maslow-hub
git clone --branch codex/iso-blockers-20261017 https://github.com/letsgomaslow/maslow-os-pkgs.git maslow-os-pkgs
git clone --branch codex/iso-blockers-20261017 https://github.com/letsgomaslow/maslow-os-iso.git maslow-os-iso
for maslow_repository in maslow-os maslow-hub maslow-os-pkgs maslow-os-iso; do
  git -C "$maslow_repository" status --short --branch
  git -C "$maslow_repository" log -1 --oneline
done
BASH
```

Compare each clone's commit with [the candidate source manifest](https://github.com/letsgomaslow/maslow-os/blob/main/docs/macbook-candidate-sources.json) on runtime main. Branch heads may later advance; do not reset an existing working tree to force a match. In a fresh clone, the manifest's exact commit can be selected with `git switch --detach COMMIT`, then a dedicated issue branch created after baseline inventory. The runtime candidate contains later documentation commits separately from shipped production payload `1056a7552c6bff751f2c27f79835cc8953862ee6` and the ISO's frozen runtime source `fdce071ee92cb07d5c00a75e2e84dff5f10a6df2`.

Cloning does not install or activate source code. Do not change `OMARCHY_PATH`, package-owned files, services, credentials or update settings while preparing a workspace. The ISO's archiso dependency is pinned to `424e78130db2af6c1ceb55b442d7914b1109ff2b`; follow its repository instructions before a future build. Clones are source continuity, not a complete offline build cache. The ISO, package binaries, VM disks, build logs and private test fixtures were not uploaded as part of this handoff.

## Claude and Codex entry points

Open the runtime source clone as the project. `AGENTS.md` is the shared entry point; root `CLAUDE.md` imports it using `@AGENTS.md` and points to this handoff, so Claude reads the same project rules. Keep one canonical rule set instead of duplicating it into a new `AGENT.md`. Each sibling repository has its own instructions; read them before editing that owner. See [Claude's documented import mechanism](https://code.claude.com/docs/en/memory#import-additional-files).

## Native development target

The continuation target is the 2012 15-inch Retina MacBook Pro running the reported Maslow installation. There is no Mac mini setup. The Linux package/service/hardware inventory below runs on that MacBook. The earlier ARM-hosted x86 TCG builds and VM checks were performed on a separate build Mac; those historical results are not native MacBook performance or hardware acceptance. Source preparation does not require an OS update, another ISO build or replacement of the installed runtime.

## Establish the installed baseline before changing anything

Run these on the MacBook itself. Keep output in a private local note; do not commit machine inventories, provider state, raw logs or credentials to source. A missing package or unavailable command is a finding to record, not a reason to repair the machine before capturing the failure.

```bash
uname -r
cat /sys/class/dmi/id/product_name
printf 'Session type: %s\n' "$XDG_SESSION_TYPE"
pacman -Q omarchy-dev omarchy-settings-dev maslow-hub maslow-voice hermes-agent qt6-base qt6-declarative quickshell broadcom-wl-dkms linux-omarchy linux-omarchy-headers linux-omarchy-bore linux-omarchy-bore-headers
systemctl --failed --no-pager
systemctl --user --failed --no-pager
dkms status
modinfo -F vermagic wl
lspci -nnk
nmcli -f DEVICE,TYPE,STATE device status
```

Kernel package names may be provider packages such as `linux-omarchy-bore` rather than the virtual `linux-omarchy` name. Record both present and missing query results. Compare with the candidate package table in the dated handoff; do not assume the user's install has exactly those versions. Record the actual installation target, encryption choice, whether updates were run, cold/reboot/wake trigger, approximate time to desktop and whether Wi-Fi reconnects. The earlier Mac-host promise to preserve macOS describes our automated build/write actions, not the user's later manual disk choice; the current native disk layout and macOS retention are unknown until checked.

For each problem, record one expected behavior, the observed behavior, exact reproduction steps, whether it happens every time, and a screenshot if useful. Identify the affected layer before changes: boot/graphics, keyboard/trackpad, network, shell IPC, Hub view, Voice UI, provider authentication, microphone/speaker audio, or agent delivery. “Installed successfully” does not itemize any of those checks.

Capture only a short redacted log excerpt around a reproduced failure. Avoid exporting full journals, core dumps, conversation/task contents or tokens. Keep installed package source and development source separate. A clone alone does not activate source code; read the relevant source-development guide before a reversible runtime override, and establish one daemon owner and a restore procedure first.

## Known hardware facts (this specific 2012 15" Retina MacBookPro10,1)

Durable, directly confirmed facts about this exact machine, kept separate from the dated handoff narrative so a future session does not have to re-derive or re-discover them. See the cited handoffs for full evidence and reproduction steps.

- **No internal-panel GPU mux.** This model hardwires its internal Retina panel to the discrete NVIDIA GT650M (`nouveau`) only. Intel's `i915` has zero eDP connectors on this hardware — unlike later dual-GPU MacBooks, there is no software-switchable path to Intel for the internal display. Confirmed by live-testing the standard nouveau-disable fix: it left the panel on an unaccelerated `simple-framebuffer` fallback with broken brightness control, not a working Intel-driven display. Do not re-attempt that fix; see [the revert handoff, October 18](handoffs/2026-10-18-macbook-intel-igpu-fix-reverted.md).
- **Nouveau is the only viable display driver, and it is clock-limited by default.** Nouveau parks this GPU at roughly 13% of its available memory bandwidth (`AC` pstate) against its own maximum (`0f` pstate), which is the dominant, confirmed cause of desktop sluggishness. A live pstate override to maximum confirms this immediately but costs real fan noise, heat and battery, so it is a diagnostic/stopgap, not a shipped fix. See [the native inventory handoff, October 18](handoffs/2026-10-18-macbook-native-inventory.md).
- **Battery is at roughly 49.5% of original design capacity** (1187 charge cycles as of October 18, 2026) — hardware wear on a 14-year-old original battery, not something software fixes.
- Audio, trackpad (`bcm5974`), FaceTime camera, Thunderbolt, Wi-Fi (`wl`/Broadcom DKMS), and a short suspend/resume cycle all passed with no defect found as of October 18, 2026.

## Ownership and tests

| Area | Source owner | Start here |
| --- | --- | --- |
| Desktop, startup, lock, Wi-Fi defaults, commands, migrations | `maslow-os` | `AGENTS.md`, `agents/skills/shell-dev.md`, `agents/skills/visual-verification.md`, `docs/testing.md` |
| Voice daemon/UI, provider readiness, agent boundaries | `maslow-os/voice` | `agents/skills/voice-development.md`, `voice/docs/execution.md` |
| Hub UI, Apps shared state, bounded update helper | `maslow-hub` | Its `AGENTS.md` and accepted Hub baseline |
| Qt, Hermes/Voice/Hub dependencies, package ownership | `maslow-os-pkgs` | Its `AGENTS.md` and exact recipe at the manifest commit |
| Boot media, installer, offline mirror and VM harness | `maslow-os-iso` | Its `AGENTS.md` and `docs/installer-reference.md` |

Create one issue/fix branch from the matching candidate after inventory. Preserve caller contracts and all existing IPC/readiness/security deadlines. Reproduce the affected source test, implement the smallest owning fix, run its focused checks and inspect visual changes on the actual desktop. Keep main unchanged pending review and the appropriate installed checks. No change is justified solely by the old ARM-hosted TCG timeouts.

For documentation-only work, validate links, revisions, scope and `git diff --check`; do not rebuild Qt or the ISO. For actual desktop fixes use the repository's focused CLI/shell and graphical procedures. Native x86 testing is now possible on the MacBook, but it has not yet been performed or observed in this handoff. Supported update/rollback, encrypted/factory recovery and provider/audio/task delivery remain distinct acceptance gates.

## Prompt for the next development chat

> Read AGENTS.md, docs/maslow-development.md, docs/macbook-development.md and docs/handoffs/2026-10-18-macbook-native-development.md in the runtime source clone. The user reports successful installation on a 2012 15-inch Retina MacBook Pro with unspecified remaining issues. Preserve the installed baseline and main. First collect the actual package/kernel/GPU/Wi-Fi/service inventory and the user's concrete symptoms, then reproduce one issue at unchanged budgets before changing its owning repository. Separate user-reported, source-test, VM, artifact, USB and directly observed native evidence. Do not infer provider/audio/recovery acceptance or replace packaged runtime files merely because source was cloned.
