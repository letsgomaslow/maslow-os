# 2026-10-10: Qt 6.12 black screens, Internet health and the Twingate startup outage

## Resume here

- **Shell fix:** installed and accepted on the Lenovo as a local runtime package. The source is in `maslow-os` PR #17 (`codex/qt612-theme-color`), not yet merged.
- **Hub 0.3.6:** installed locally from the exact release candidate and accepted on the Lenovo. It is **not published**; the staging channel is still sequence 9 with 0.3.5 the newest.
- **Next action:** the operator merges the open PRs listed below, then decides whether to publish Hub 0.3.6. The operator runs the publish in their own terminal, because OpenSSL asks for the passphrase.
- **Twingate:** still enabled on the Lenovo. Use Hub → Connections → "Stop Twingate starting automatically", then reboot and confirm the internet is up about 19 s after login.

## 1. Black Hub and menu after Qt 6.12

**Symptom (user report):** the menu shortcut and Hub opened as black screens.

**Root cause:** Qt 6.12 and quickshell 0.3.2 were installed on 2026-10-10 at 12:19.
- Qt 6.12 exports a QtQuick `Color` type (QQuickColor). In QML, a bare `Color.foreground` now resolves to that type instead of the shell's `qs.Commons` theme singleton, and evaluates to `undefined`.
- Every colour read that way failed: buttons, text fields, notification cards, panels, the bar, `Style` theme loading, Hub and Voice.
- Logs: "Unable to assign [undefined] to QColor" and "Cannot read property … of undefined".

**Fix pattern:** `import qs.Commons as Theme`, then `Theme.Color.x`. Both source-contract tests (Hub's and the Voice UI contract) now reject a bare `Color.`.

### Runtime: `maslow-os`
- **Change:**
  - 55 shell files: `b12ade81`, cherry-picked from `ef26a47a`.
  - Bar drag-overlay source check: `1ef77b98`.
  - Voice panel, orb preview, the captive-portal fixture, and a hermetic `HOME` for the bar-icon geometry test: `23abd8d7`.
  - All on PR #17.
- **Installed on the Lenovo:**
  - Package: `omarchy-dev-4.0.0.r2079.g4c463ed-1`, built from the installed base `dca4d9c` plus the fix (local branch `codex/qt612-theme-color-local`, `ef26a47a` and `4c463edb`).
  - SHA-256: `690d32f9f880d9208f0ac2eba3b88d72d5accb39fd8c073eb7df726569e826be`.
  - Installed with `MASLOW_ALLOW_RUNTIME_UPDATE=1` through the runtime hold at 20:01:21.
- **Rollback:** `omarchy-dev-4.0.0.r2077.gdca4d9c-1`, SHA-256 `ccf60100195dada39c7b35969ad0cb86aeb86a75314739c8125ea8f74a5b4d86`. It is identical to the previously installed package and kept in `~/Downloads`.
- **Tests:** `./test/all` was run on the ported branch, and 241 of 246 test files passed.
  - `config`, `snapper` and `unowned-system-paths` need an `omarchy-pkgs` checkout at the path the tests expect. They fail identically on `main`.
  - `screenshot-sanity` is timing-flaky ("omarchy-shell is not responding"). It fails on `main` too.
  - `bar-icon-geometry` was failing with the fix and now passes with an empty `HOME`; see the second follow-up below.
- **Visual evidence:** a screenshot of the menu ("Go… / Maslow Hub / Apps / …") shows correct colours. Since the restart, no colour warnings come from `/usr/share/omarchy/shell`.

### Hub: `maslow-hub`
- **Change:**
  - `15cd494`: Panel colours through `Theme.Color`, and Hub's own `HubButton` and `TextField` take Hub's resolved colours.
  - `33940d2`: Voice tests made host-independent; all 153 pass on Linux.
  - All on PR #2, which also carries 0.3.2–0.3.5 and supersedes PR #1.
- **Candidate:**
  - Package: `maslow-hub-0.3.6-1-any.pkg.tar.zst`, SHA-256 `558695f3932c3c9bfd95bd0b1e6ee243dc9a4ebb24a47239639bc3a523bcdd89`.
  - Source: `15cd494`.
  - Review: `f98ef4eec77b83d7090f224b995cec2a41537c233efd541e1b7b2898881dd380`.
  - Run: `~/.local/share/maslow-release/runs/20261010T194714Z-prepare`.
  - An earlier candidate (review `e6d0c6a5…`, source `41544d5`) would also have rendered black. It was withdrawn before publication.
- **Accepted on the Lenovo:** installed with `pacman -U` from the candidate directory.
  - Hub Setup and Connections render with full colours.
  - After the restart, no Hub colour warnings appear.

### Not fixed here
- **Third-party plugins** still use bare `Color` and log warnings: omadock (the dock), io.github.mtolhuys.onscreen-keyboard, goktugvatandas.quick-chat, io.github.ellion369.omagent, io.github.juancasanueva.plugin-manager, robzolkos.github and stappmus.activity-monitor.
  - omadock is packaged through `maslow-curated-plugins` in `maslow-os-pkgs`, which already carries a Maslow patch, so a local patch there is possible.
- **Installed Voice panel** (`/usr/share/maslow/plugins/maslow.voice/0.1.5-37`) still logs 84 warnings. The source fix is in PR #17, and it reaches users with the next Voice package build.

## 2. Internet health and the Twingate startup outage

**Symptom:** after each boot the Lenovo's Wi-Fi showed connected, but websites did not load for about 5 minutes.

**Root cause:** a signed-out Twingate client.
- It claimed every DNS lookup (`~.` on its `sdwan0` link) and reset the Wi-Fi link's DNS servers.
- It also switched off NetworkManager's connectivity check, so nothing looked wrong.
- The journal for the 2026-10-10 boot shows DNS returning to `wlp0s20f3` only at 323 s. That is a 305 s outage measured from Wi-Fi connecting.

**Hub 0.3.6 adds an "Internet health" card** on Connections, backed by `helper/network_health.py` and `maslow-hubctl network-health check|fix <unit>`.
- **Read-only checks:**
  - default route;
  - links claiming `~.`;
  - a name lookup;
  - NetworkManager's connectivity check;
  - the measured startup outage from this boot's journal.
- **The only change it offers** is `systemctl disable --now` for an allow-listed VPN unit, through the normal authorization prompt.
  - Allowed: Twingate, Cloudflare WARP, NordVPN, ZeroTier.
  - Tailscale is never blamed or disabled.
- **Tests:** 9 unit tests, using real Lenovo journal lines.
- **Accepted on the Lenovo:** the card reports "websites didn't load for about 305 seconds because Twingate held every lookup" and offers the fix. `twingate.service` is still `enabled`; the operator has not used the button yet.

## 3. Repository state at close (2026-10-10)

| Repository | PR | Base | Contents | Checks run here |
| --- | --- | --- | --- | --- |
| `maslow-hub` | #2 | `main` | Hub 0.3.2–0.3.6 and Linux-safe Voice tests; supersedes #1 | `release/check.sh` passes: 153 tests, UI contract, diff check |
| `maslow-os` | #16 | `main` | `maslow` command and update download retry | Both new shell tests pass |
| `maslow-os` | #17 | `main` | Qt 6.12 `Theme.Color` fix | See section 1 |
| `maslow-os` | this docs PR | `main` | This handoff and the index | Docs only |
| `maslow-releases` | #3, marked ready | `main` | Local release workstation; includes #2's protected-workflow commit | 64 tests pass |
| `maslow-os-pkgs` | #6 | `maslow` | `maslow-voice` recipe `0.1.5-19` → `0.1.5-37` and `tmux` | `test/maslow-packaging` passes |
| `maslow-connect` | #1 | `codex/maslow-connect` (default) | Local MCP servers, bring-your-own Composio "Your accounts", wiring for 8 agents | `pnpm check` passes: 213 tests, 10 DB-backed skips, typecheck, build |

**Merging:** none of these repositories has branch protection or required checks. GitHub Actions is billing-locked, so no CI ran; every check above was run locally on the Lenovo.

The automated merge was blocked by the agent's permission policy (merge without review). The operator merges, or explicitly allows the agent to.

## Follow-ups

1. Merge the PRs above in this order: `maslow-hub` #2, `maslow-releases` #3, `maslow-os` #16, #17 and this docs PR, `maslow-os-pkgs` #6, then `maslow-connect` #1.
2. **Bar indicator centring:** at the Lenovo's theme scale (12 px caption, 19 px canvas), the vertical bar indicator measures 0.59 px off-centre. This is invisible but over the test's 0.5 px limit. It was hidden before because `Style` never loaded the theme.
3. **Third-party plugins** (listed in section 1): patch omadock via `maslow-curated-plugins`, and report the rest upstream.
4. **Runtime delivery:** publish a runtime package from merged `main` through the supported `maslow update` path. The Lenovo's r2079 is a local, hand-installed build.
5. **Hub 0.3.6:** publish only after operator approval of the exact candidate above.
6. **Twingate:** disable it, reboot, and confirm the startup outage is gone.
