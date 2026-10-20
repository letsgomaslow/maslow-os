# Retro wallpaper selection — October 20, 2026

## Scope and source

Runtime source baseline: `aeb84427` on `main`. This change adds only selected static artwork, matching theme-picker previews and these documentation updates to `letsgomaslow/maslow-os`. Theme palettes, Hyprland settings, shell code, Voice, Hub, packages and ISO are unchanged. No push, merge, package publication or ISO release is part of this checkpoint.

| Theme | Selected artwork / first default background | SHA-256 of background and matching preview |
| --- | --- | --- |
| `maslow-1984` | `themes/maslow-1984/backgrounds/00-intelligence-portal.png` | `758cdf22121c8385c67f0c8517db60a81581890eb5e8290c81cf6a3d57862672` |
| `maslow-platinum` | `themes/maslow-platinum/backgrounds/00-silver-relief.png` | `08d6ea506fe71cc820725e962639ee919c360ddf02735df061354e6f955f9f5a` |

Both PNGs are 1586 × 992 RGB images generated with the built-in image-generation tool. Intelligence Portal depicts a futuristic AI gateway in monochrome bitmap/dither artwork; Silver Relief uses matte platinum folds and a restrained teal inset. The user explicitly selected these images from generated alternatives. No discarded alternatives are committed. Existing `01-flat-white.png` and `01-silver-gradient.png` remain as selectable alternatives. The `00-` filenames put the selected images first for a fresh theme selection; existing remembered wallpaper choices remain governed by the normal theme workflow.

## Local application and evidence

The selected images were added through supported user background directories, with per-theme remembered selections. The picker continued showing placeholder artwork because it reads the theme's `preview.png`, rather than the selected user wallpaper. Local preview overrides were updated and the picker cache rebuilt/preloaded; both picker paths resolve to previews whose SHA-256 matches the selected artwork. Original local preview images and selection state were backed up outside Git. The user confirmed both wallpapers look great, then confirmed the picker correction looks great. These are user-observed native visual results, not an automated graphical acceptance pass.

An initial screenshot showed the terminal covering the desktop. Later screenshot capture stalled and was stopped; no successful coordinator-inspected screenshot of the full wallpaper/picker is claimed. The native report is retained as the visual acceptance evidence. Existing video-intro disable and reduced-motion mitigations were preserved; no video assets were introduced.

## Validation and next action

- `bash test/shell.d/menu-images-test.sh`: all five checks pass.
- PNG decoding/metadata and exact background/preview hash equality checked for both themes.
- Documentation links, baseline revision, staged file scope and `git diff --check` checked before commit.
- No new tests added for static image replacement. No unchanged full build, VM acceptance, package or ISO suites rerun.

Next action: review this scoped runtime asset commit for downstream delivery. Package/release publication remains separate; this source checkpoint does not claim that another installed machine has received the artwork.
