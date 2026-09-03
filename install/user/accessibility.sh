system_config=/etc/maslow-os/accessibility.conf
user_config="$HOME/.config/maslow-os/accessibility.conf"
orca_link="$HOME/.config/systemd/user/graphical-session.target.wants/maslow-orca.service"
reduced_motion_source="$OMARCHY_PATH/default/hypr/toggles/reduced-motion.lua"
reduced_motion_target="$HOME/.local/state/omarchy/toggles/hypr/reduced-motion.lua"

if [[ -r $system_config && ! -e $user_config ]]; then
  install -Dm644 "$system_config" "$user_config"
fi

if grep -qx 'speech=true' "$user_config" 2>/dev/null; then
  mkdir -p "$(dirname "$orca_link")"
  ln -sfn /usr/lib/systemd/user/maslow-orca.service "$orca_link"
else
  rm -f "$orca_link"
fi

# This state file is sourced by Hyprland while the first session is assembled,
# so reduced motion is active before the first desktop frame instead of being
# toggled after the compositor has already animated into view.
if grep -qx 'reduced_motion=true' "$user_config" 2>/dev/null; then
  install -Dm644 "$reduced_motion_source" "$reduced_motion_target"
fi

if grep -qx 'large_text=true' "$user_config" 2>/dev/null; then
  omarchy-display-text-size 16
fi
