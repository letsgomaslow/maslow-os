# Maslow OS brand assets

This directory contains the approved Maslow Gradient Bridge mark, canonical design tokens, licensed Manrope source, and deterministic asset-generation script used by Maslow OS.

The generator also converts the official Gradient Bridge lockup into the
80-column block-art `logo.txt` used by first-boot setup and the screensaver.

The canonical colors and logo files are copied from the consolidated Maslow Brand System. Do not redraw the mark, substitute legacy fonts, or introduce raw palette values without updating `design-tokens.json` and the brand validation test.

Run `branding/scripts/generate-assets` on an Omarchy/Arch development machine with ImageMagick installed to regenerate wallpapers, previews, unlock images, and boot/login artwork. Generated application color files continue to come from each theme's `colors.toml` through the normal Omarchy theme pipeline.
