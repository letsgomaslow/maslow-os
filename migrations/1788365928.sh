echo "Register and apply Maslow OS login branding repair"

hook="$OMARCHY_PATH/install/user/first-run/maslow-login-branding.hook"
if [[ -f $hook ]]; then
  omarchy-hook-install post-update "$hook"
  bash "$hook"
else
  echo "Maslow OS login-branding hook is missing: $hook" >&2
  exit 1
fi

# These older one-purpose invitations are consolidated into Maslow AI Setup.
# Remove only the package-installed copies; source files remain available for
# upstream compatibility and user-authored hooks are untouched.
rm -f \
  "$HOME/.config/omarchy/hooks/post-update.d/setup-agent.hook" \
  "$HOME/.config/omarchy/hooks/post-update.d/setup-fingerprint.hook" \
  "$HOME/.config/omarchy/hooks/post-update.d/install-voxtype.hook"
