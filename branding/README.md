# Maslow OS brand assets

This directory contains the approved Maslow Gradient Bridge mark, canonical design tokens, licensed Manrope source, curated wallpaper source, and deterministic asset-generation script used by Maslow OS.

The generator converts the official Gradient Bridge mark and a Manrope wordmark into the 80-column block-art `logo.txt` used by first-boot setup and the classic terminal screensaver. The terminal artwork is generated separately from the graphical lockup so the product name remains legible at console resolution.

The canonical colors and logo files are copied from the consolidated Maslow Brand System. Do not redraw the mark, substitute legacy fonts, or introduce raw palette values without updating `design-tokens.json` and the brand validation test.

The generator also writes the native screensaver's assets into `shell/plugins/screensaver/assets/`, because `branding/` is not installed at runtime. The shell never blurs at runtime, so every soft light is a pre-blurred PNG written without timestamps; regenerating leaves the files unchanged, and `test/maslow-brand` checks them:

- `maslow-mark-gradient.svg`, a byte-identical copy of `logos/maslow-mark-gradient.svg`.
- `glow.png`, a 1024x512 halo that runs the Brand OS pink, light purple and teal under an elliptical falloff.
- `aurora-deep.png`, `aurora-violet.png`, `aurora-pink.png`, `aurora-teal.png` and `aurora-amber.png`, 512x512 soft discs of `#401877`, `#A070A6`, `#EE7BB3`, `#6DC4AD` and `#F2A23A` that drift behind the mark.
- `particle.png`, a 128x128 white point of light that travels along the mark's two bridges.
- `ring.png`, a 512x512 white ring that ripples out from the two standalone circles.

### Mark outline fix

The traced source of the Gradient Bridge mark clipped its two left circles flat against the left edge of the viewBox. Every `logos/maslow-mark-*.svg` file now restores them from the intact lower-right circle: that circle replaces the standalone upper-left one and is repeated over the lower-left one, and the viewBox starts at `-1` (`-1 0 375 249`) so the restored edge is not clipped. Generated PNG lockups and the screensaver copy follow from the fixed files. The `omarchy.ttf` glyph at `U+E90B` still uses the old, clipped outline, because the icon-font tool can add glyphs but not replace existing ones.

Run `branding/scripts/generate-assets` on an Omarchy/Arch development machine with ImageMagick installed to regenerate the approved Maslow OS lockup, console artwork, and boot/login assets. Pass `--wallpapers` only when intentionally regenerating the deferred wallpaper set. Generated application color files continue to come from each theme's `colors.toml` through the normal Omarchy theme pipeline.
