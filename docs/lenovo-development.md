# Maslow development on Lenovo

Updated 2026-09-16. Start with [current progress](maslow-development.md) and [the Lenovo failure handoff](handoffs/2026-09-16-lenovo-voice-development-handoff.md). This document maps source ownership and sets up clones; it does not install development code into the running desktop or claim the hardware failure is fixed.

## Repository ownership and branches

All source already has an existing GitHub repository. No new Voice repository is needed: `maslow-voice` is a package, while `voice/` is its source directory inside `maslow-os`. GitHub branch backup preserves work without merging experimental code into product branches.

| Lenovo directory under `~/Projects/Maslow` | GitHub repository | Development checkout | Ownership / instructions |
| --- | --- | --- | --- |
| `maslow-os` | [letsgomaslow/maslow-os](https://github.com/letsgomaslow/maslow-os) | `codex/livekit-setup` | `voice/`, providers, daemon, native UI, commands, Hermes daemon plugin; `AGENTS.md`, `agents/skills/voice-development.md`, `docs/maslow-development.md` |
| `maslow-hub` | [letsgomaslow/maslow-hub](https://github.com/letsgomaslow/maslow-hub) | `codex/gpt-live-test-release` | Hub UI, optional component onboarding, bounded updater; its `AGENTS.md` and `README.md` |
| `maslow-os-pkgs` | [letsgomaslow/maslow-os-pkgs](https://github.com/letsgomaslow/maslow-os-pkgs) | `codex/linux-live-packages` | Voice/Hermes/Hub recipes, dependencies, ownership, package build/release tooling; its `AGENTS.md` |
| `maslow-os-iso` | [letsgomaslow/maslow-os-iso](https://github.com/letsgomaslow/maslow-os-iso) | `codex/maslow-hub` | Installer, offline mirror, QEMU/TCG installed acceptance harness; its `AGENTS.md` |
| `maslow-connect` | [letsgomaslow/maslow-connect](https://github.com/letsgomaslow/maslow-connect) | `codex/maslow-connect-org-control-plane` | Independent portal/gateway/MCP bridge and agent adapters; `README.md`, `docs/serverless-local-roadmap.md`; no repo-root `AGENTS.md` existed in this audit |
| `maslow-releases` | [letsgomaslow/maslow-releases](https://github.com/letsgomaslow/maslow-releases) | `main` | Public signed metadata and status pages; its `AGENTS.md`; binaries belong in immutable Releases, not source history |
| `maslow-os-shipped-voice9` | Worktree of `maslow-os` | Detached `675019e524759f0ab66a2f8b0079e5aea2d4d9bb` | Exact runtime source used by shipped Voice 0.1.4-9; baseline comparison, not an editable replacement installation |

OS product branch remains `main`; package and ISO product branches remain `maslow`. Hub product branch is `main`. Inspect each repository's actual remote default before integration. Hermes is separately packaged upstream software: its pinned package and Maslow integration are owned by the package/runtime repos above; do not create a second Hermes source fork merely to diagnose setup. Codex and Claude remain external tools with their own installation/authentication and permission requirements. Maslow Connect is separate from the current authenticated Voice-to-Hermes Runs API path.

Current Voice integration includes unpublished LiveKit work. The September 14 OTA deliberately contains the older exact Voice 0.1.4-9 archive, SHA-256 `4b465a4cff46e4da6a5bf549d9fefcabd0f70fa312dedd76a1219a29136228ab`, built from runtime `675019e5` and recipe `3fe0daf7`. Hub source used for its outer archive is `82efec30`; `5c412c77` adds a test-only correction. Package integration `652583d9` contains the outer Hub recipe. Do not compare the current integration version label alone with the installed package or rebuild latest LiveKit as a GPT-Live troubleshooting shortcut.

## Verified Mac locations for recovery

These are local discovery paths, not paths to hardcode into runtime/configuration. On Lenovo use the portable sibling layout above.

| Work | Mac path |
| --- | --- |
| Current runtime / Voice docs | `/Users/r.david/.codex/worktrees/maslow-voice/livekit-runtime` |
| Current GPT-Live Hub candidate | `/Users/r.david/.codex/worktrees/maslow-voice/gpt-live-hub` |
| Current package integration | `/Users/r.david/.codex/worktrees/maslow-voice/live-packages` |
| ISO and installed harness | `/Users/r.david/.codex/worktrees/43ab/Maslow OS - ISO` |
| Public distribution | `/Users/r.david/.codex/worktrees/43ab/maslow-releases` |
| Maslow Connect | `/Users/r.david/Documents/Maslow-Propriotory-Repos/Maslow Connect` |
| Earlier coordinated runtime/packages/Hub | `/Users/r.david/.codex/worktrees/43ab/` |
| Earlier Voice runtime/Hub/packages | `/Users/r.david/.codex/worktrees/maslow-voice/` |

Prior evidence roots are recorded in the dated handoffs. They are not in Git and are not present on Lenovo just because source is cloned. Signing remains operator-managed on Mac; do not transfer private release keys, passphrases or Mac tester account values. Metadata expiry is September 24, 2026 at 23:56:41 UTC; renewal is a separate signed maintenance action.

## Copy and paste on Lenovo

Prerequisites: use the Lenovo desktop terminal, Git, and GitHub CLI (`gh`). Sign in using your own GitHub account with access to the private repositories. This creates source clones and a workspace instruction file only. It does not change installed Voice, Hermes, Quickshell, credentials, systemd units, or OS update settings. If `gh` is missing, use the normal Omarchy application/package installation flow before continuing.

First, sign in (skip login if `gh auth status` already confirms the correct account). These commands configure your own GitHub authentication and Git credential helper:

```bash
gh auth status
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

Then paste this block. It stops if an existing destination would be overwritten; reuse and inspect existing clones instead of deleting them.

```bash
bash <<'BASH'
set -euo pipefail
maslow_workspace="$HOME/Projects/Maslow"
mkdir -p "$maslow_workspace"
cd "$maslow_workspace"
for maslow_directory in maslow-os maslow-hub maslow-os-pkgs maslow-os-iso maslow-connect maslow-releases maslow-os-shipped-voice9; do
  if [[ -e $maslow_directory ]]; then
    echo "Already exists: $maslow_workspace/$maslow_directory. Stop and inspect the existing workspace."
    exit 1
  fi
done
if [[ -e AGENTS.md ]]; then
  echo "An existing workspace AGENTS.md needs to be reviewed first."
  exit 1
fi
git clone --branch codex/livekit-setup https://github.com/letsgomaslow/maslow-os.git maslow-os
git clone --branch codex/gpt-live-test-release https://github.com/letsgomaslow/maslow-hub.git maslow-hub
git clone --branch codex/linux-live-packages https://github.com/letsgomaslow/maslow-os-pkgs.git maslow-os-pkgs
git clone --branch codex/maslow-hub https://github.com/letsgomaslow/maslow-os-iso.git maslow-os-iso
git clone --branch codex/maslow-connect-org-control-plane https://github.com/letsgomaslow/maslow-connect.git maslow-connect
git clone https://github.com/letsgomaslow/maslow-releases.git maslow-releases
git -C maslow-os worktree add --detach "$maslow_workspace/maslow-os-shipped-voice9" 675019e524759f0ab66a2f8b0079e5aea2d4d9bb
cp maslow-os/docs/lenovo-workspace-AGENTS.md AGENTS.md
for maslow_directory in maslow-os maslow-hub maslow-os-pkgs maslow-os-iso maslow-connect maslow-releases; do
  git -C "$maslow_directory" status --short --branch
  git -C "$maslow_directory" log -1 --oneline
done
echo "Source workspace ready: $maslow_workspace"
BASH
```

Open `~/Projects/Maslow` as the coding-agent project so its top-level `AGENTS.md` points to every dependency. Start the next task with: “Read AGENTS.md and docs/handoffs/2026-09-16-lenovo-voice-development-handoff.md inside maslow-os. Diagnose the installed GPT-Live failure before changing code; LiveKit remains pending.” No Mac signing step, new ISO or reinstall is required to prepare development source.

## Keep development and installed state separate

Do not edit the installed Omarchy checkout, set `OMARCHY_PATH` to a clone, replace package-owned files, or copy provider credentials into source to start development. Cloning alone does not run the source daemon. Any source-run override must first establish installed versions, pinned virtual-environment compatibility, one daemon owner, safe credential access and a reversible restore procedure. Keep packaged UI and source daemon revisions explicit.

For source changes use the owning tests and locks; for visual changes inspect the actual Lenovo UI and use Docker/headless Weston/real Quickshell as an iteration path. For installed regression proof reuse ISO QEMU/TCG with CIDATA, SSH and QMP; no UTM. Builds, provider account tests and hardware checks remain separate evidence. Refer to [Voice development](../agents/skills/voice-development.md), [Voice architecture](maslow-voice.md) and [execution](../voice/docs/execution.md).
