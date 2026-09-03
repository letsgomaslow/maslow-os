# Maslow OS brand assets

This directory contains the approved Maslow Gradient Bridge mark, canonical design tokens, licensed Manrope source, curated wallpaper source, and deterministic asset-generation script used by Maslow OS.

The generator converts the official Gradient Bridge mark and a Manrope wordmark into the 80-column block-art `logo.txt` used by first-boot setup and the screensaver. The terminal artwork is generated separately from the graphical lockup so the product name remains legible at console resolution.

The canonical colors and logo files are copied from the consolidated Maslow Brand System. Do not redraw the mark, substitute legacy fonts, or introduce raw palette values without updating `design-tokens.json` and the brand validation test.

Run `branding/scripts/generate-assets` on an Omarchy/Arch development machine with ImageMagick installed to regenerate the approved Maslow OS lockup, console artwork, and boot/login assets. Pass `--wallpapers` only when intentionally regenerating the deferred wallpaper set. Generated application color files continue to come from each theme's `colors.toml` through the normal Omarchy theme pipeline.
