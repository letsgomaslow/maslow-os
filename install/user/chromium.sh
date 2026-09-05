# Chrome ships in the base packages, so it never goes through
# omarchy-install-browser, and fresh installs mark every migration as already
# applied. Reproduce the optional installer's user setup here while keeping the
# Chromium-family native hosts available for every supported browser.
mkdir -p ~/.config
if [[ ! -e $HOME/.config/chrome-flags.conf && ! -L $HOME/.config/chrome-flags.conf ]]; then
  cp "$OMARCHY_PATH/config/chromium-flags.conf" ~/.config/chrome-flags.conf
fi
omarchy-install-chromium-copy-url
omarchy-install-chromium-ytdlp
