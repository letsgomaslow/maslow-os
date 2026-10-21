# Maslow OS brand assets

This directory contains the approved Maslow Gradient Bridge mark, canonical design tokens, licensed Manrope source, curated wallpaper source, and deterministic asset-generation script used by Maslow OS.

The generator converts the official Gradient Bridge mark and a Manrope wordmark into the 80-column block-art `logo.txt` used by first-boot setup and the screensaver. The terminal artwork is generated separately from the graphical lockup so the product name remains legible at console resolution.

The canonical colors and logo files are copied from the consolidated Maslow Brand System. Do not redraw the mark, substitute legacy fonts, or introduce raw palette values without updating `design-tokens.json` and the brand validation test.

### Mark outline fix

The traced source of the Gradient Bridge mark clipped its two left circles flat against the left edge of the viewBox. Every `logos/maslow-mark-*.svg` file now restores them from the intact lower-right circle: that circle replaces the standalone upper-left one and is repeated over the lower-left one, and the viewBox starts at `-1` (`-1 0 375 249`) so the restored edge is not clipped. Generated PNG lockups and the screensaver copy follow from the fixed files. The `omarchy.ttf` glyph at `U+E90B` still uses the old, clipped outline, because the icon-font tool can add glyphs but not replace existing ones.

Run `branding/scripts/generate-assets` on an Omarchy/Arch development machine with ImageMagick installed to regenerate the approved Maslow OS lockup, console artwork, and boot/login assets. Pass `--wallpapers` only when intentionally regenerating the deferred wallpaper set. Generated application color files continue to come from each theme's `colors.toml` through the normal Omarchy theme pipeline.
