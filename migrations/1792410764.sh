echo "Enable weekly periodic TRIM (fstrim.timer)"

as_root() {
  if (( EUID == 0 )); then
    "$@"
  else
    sudo "$@"
  fi
}

# Safe on any filesystem: fstrim skips mountpoints that don't support
# discard, so this is a no-op on spinning disks and a real long-term SSD
# write-performance benefit everywhere else. Stock systemd ships this unit
# disabled by default; nothing in this install ever opted in before now.
if systemctl is-enabled --quiet fstrim.timer 2>/dev/null; then
  exit 0
fi

as_root systemctl enable --now fstrim.timer
