run_logged "$OMARCHY_INSTALL/user/theme.sh"
run_logged "$OMARCHY_INSTALL/user/maslow-login-branding.sh"
run_logged "$OMARCHY_INSTALL/user/accessibility.sh"
run_logged "$OMARCHY_INSTALL/user/chromium.sh"
run_logged "$OMARCHY_INSTALL/user/git.sh"
run_logged "$OMARCHY_INSTALL/user/xcompose.sh"
run_logged "$OMARCHY_INSTALL/user/mise-work.sh"

run_optional_logged() {
  local script="$1" marker state_dir

  if run_logged "$script"; then
    return 0
  fi

  marker="${MASLOW_OPTIONAL_FAILURE_FILE:-$HOME/.local/state/maslow-os/optional-failures}"
  state_dir=$(dirname "$marker")
  mkdir -p "$state_dir" 2>/dev/null || return 0
  chmod 0700 "$state_dir" 2>/dev/null || true
  printf '%s\n' "$script" >>"$marker" 2>/dev/null || true
  chmod 0600 "$marker" 2>/dev/null || true
  return 0
}

run_optional_logged "$OMARCHY_INSTALL/user/hardware/asus/fix-audio-mixer.sh"
run_optional_logged "$OMARCHY_INSTALL/user/hardware/asus/fix-mic.sh"
run_optional_logged "$OMARCHY_INSTALL/user/hardware/framework/fix-f13-amd-audio-input.sh"
run_optional_logged "$OMARCHY_INSTALL/user/hardware/dell/xps13-text-scaling.sh"
run_optional_logged "$OMARCHY_INSTALL/user/hardware/fix-nouveau-cursor.sh"

run_logged "$OMARCHY_INSTALL/user/default-keyring.sh"
run_optional_logged "$OMARCHY_INSTALL/user/mise.sh"
