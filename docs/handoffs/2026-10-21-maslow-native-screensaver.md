# Maslow native screensaver and round brand mark — October 20-21, 2026

## Outcome

Maslow AI-OS now has its own screensaver instead of Omarchy's terminal text effects. Branch `feature/maslow-screensaver` adds `maslow.screensaver`, a first-party shell plugin that draws one full-screen overlay per monitor on the Wayland Overlay layer: a navy field with five slowly orbiting brand-colour aurora fields, the Gradient Bridge mark with a breathing halo, light particles travelling along both bridges, ripples leaving the two standalone circles, and a centred wordmark, large clock and "PRESS ANY KEY" hint that drift together for burn-in protection. Omarchy's terminal screensaver stays available as the `classic` style and is the automatic fallback whenever the shell cannot answer.

The same branch fixes the brand mark itself: the traced `branding/logos/maslow-mark-*.svg` sources clipped both left circles flat. They are restored from the intact lower-right circle (fit error about 0.3 viewBox units) and the viewBox now starts at `-1` so the restored edge is not clipped again.

The user reviewed the design live in several rounds, asked for it to be "mesmerizing" rather than subtle, approved the aurora version, and is now living with it on the 2012 MacBook Pro as the default.

Commits on `feature/maslow-screensaver` (base `f3361795`): `ce857f05` restores the mark, `f04c9c69` adds the plugin, `4f53634d` makes it the default with the classic fallback, and the documentation commit carrying this handoff follows them.

## Design and boundaries

- Rendering is a single `Timer` in `shell/plugins/screensaver/Service.qml` at 20 fps on AC, 10 on battery, 0 when still; every visual is a pure function of elapsed time in `ScreensaverModel.js`. No `NumberAnimation`, `Behavior`, `ShaderEffect`, `MultiEffect`, `layer.enabled`, `Canvas` or video; all light is pre-blurred PNGs that only move, scale and fade. A static test guards this.
- Integration is additive: the plugin reports itself to `omarchy.idle` as one pseudo window (`NativeScreensaver.js`), so the existing launch grace, dismiss-cancels-lock and lock-deadline logic cover both renderers. `omarchy-launch-screensaver` asks the shell first and falls through to the terminal path on any answer other than `ok`/`locked`. `omarchy-system-lock` also asks the overlay to hide; the plugin itself freezes and unmaps 1.5 s after the lock service reports `locked` so the desktop does not flash before the lock surface.
- Settings live in `~/.config/omarchy/shell.json` under `screensaver`: `style` (`maslow` default, `classic`) set with `omarchy screensaver style`, and `motion` (`auto` follows the system Reduced Motion toggle, `full` always animates, `reduced` always still).
- Nothing on the screensaver reads notifications, agents, Voice or Hub state.

## Evidence

- Source tests: see the PR for the exact commands and results of `./test/cli`, `./test/shell`, `test/maslow-brand` and the screensaver model/render/style/launcher/idle/lock tests. Known unrelated failures: three tests need a `maslow-os-pkgs` checkout that is absent on this machine, `network-captive-portal-test.sh` fails identically on `main`, and `test/maslow-visible-brand` fails on `main` because the "Maslow OS Support" menu route is missing.
- Visual: offscreen software-rendered galleries at 1280x800, 1440x900 and 1920x1080 plus Reduced Motion were inspected, and the user inspected repeated live previews on the MacBook (overlay layer, 2880x1800 at scale 3).
- Performance (MacBook Pro 10,1, nouveau, AC, preview harness of the same scene at 20 fps, not the installed idle path): `top` over 15 s showed about 7% of one core for the quickshell preview process and about 3.7% for Hyprland, with no nouveau kernel faults. The old terminal path had been sampled near 98% busy in a TCG VM (`docs/performance-baseline.md`), which is not a like-for-like native comparison.
- Installed trial: `omarchy-launch-screensaver force` on the installed shell reported `{"active":true,"style":"maslow","motion":"full","fps":20}`, idle status `nativeScreensaver:true`, and no `ttfx` process.

## Device-local state on the MacBook (not in Git)

- `omarchy dev link` is disabled on this build and the installed tree is a divergent candidate, so the screensaver change was applied as narrow patches on copies of the installed files (the idle `Service.qml` import and the `omarchy-shell.lua` layer rule needed hand placement) and installed with a user-run sudo script. 22 files were installed; replaced files are backed up with a `restore.sh` in `~/.local/share/maslow-screensaver-trial/backup-20261020-234927/`. A later update replaced only the plugin's `Service.qml` and `ScreensaverModel.js`.
- The installed plugin mark is already the round version. The installed login, boot-splash and unlock images and the `omarchy.ttf` glyph `U+E90B` still use the old outline until a package release.
- The user's `shell.json` has `"screensaver": {"motion": "full"}` and the `screensaver-off` toggle was removed so the idle screensaver runs. Reduced Motion and `background-intros-off` remain on as the GPU-hang mitigation from October 19-20; the screensaver override does not re-enable any OWE video path.
- `omarchy update` would overwrite the trial files with the packaged ones and silently return the classic screensaver.
- During the session the machine once stayed dark after an idle lock and needed a power-button restart. Logs show the installed (pre-trial) lock at 22:09, user activity at 22:42:12 and a power key two seconds later with no GPU faults; this looks like the existing lock/DPMS wake issue, not the screensaver, and is not diagnosed.

## Remaining gates

- Native checks on the installed trial: pointer dismissal, multi-monitor keyboard focus, cursor hiding, lock handoff without a desktop flash, and a measured idle-path CPU/GPU budget.
- Package delivery through `maslow-os-pkgs` (new plugin directory with `assets/`, `bin/omarchy-screensaver-style`), then removal of the trial files.
- Rebuild the `U+E90B` icon glyph from the fixed monochrome mark (the font tool can only append glyphs).
- Check Hub, Connect, packages and ISO repositories for their own copies of the old mark.

## Next action

Review and merge the screensaver PR when the user approves, after a few days of living with the installed trial.
