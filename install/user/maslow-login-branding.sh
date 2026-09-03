# Register the comparison-gated Maslow login repair for every fresh user. Fresh
# installs deliberately mark packaged migrations complete, so this cannot live
# only in a migration.
hook="$OMARCHY_INSTALL/user/first-run/maslow-login-branding.hook"

if [[ -f $hook ]]; then
  omarchy-hook-install post-update "$hook"
else
  echo "Maslow OS login-branding hook is missing: $hook" >&2
  return 1
fi
