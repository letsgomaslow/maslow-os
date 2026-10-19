echo "Install the AC/battery nouveau pstate switch udev rule on the MacBookPro10,1"

omarchy-hw-macbookpro10-1 || exit 0

rules_dir=/etc/udev/rules.d
rule_path="$rules_dir/90-omarchy-macbookpro10-1-pstate.rules"
packaged_rule="$OMARCHY_PATH/default/udev/macbookpro10-1-pstate.rules"
udev_control=/run/udev/control
install_command=/usr/bin/install
udevadm_command=/usr/bin/udevadm

as_root() {
  if (( EUID == 0 )); then
    "$@"
  else
    sudo "$@"
  fi
}

# Already installed with the exact content this version ships: nothing to do,
# and no privileged call needed to notice that.
if [[ -f $rule_path ]] && cmp -s "$packaged_rule" "$rule_path"; then
  exit 0
fi

if ! as_root "$install_command" -Dm644 "$packaged_rule" "$rule_path"; then
  echo "Administrator privileges are required to install the MacBookPro10,1 pstate udev rule. Ask an administrator to run omarchy-migrate." >&2
  exit 1
fi

# With no control socket there is no running udevd to refresh; the next daemon
# start reads the rules directory from disk on its own.
if [[ -e $udev_control ]] && ! as_root "$udevadm_command" control --reload 2>/dev/null; then
  echo "Could not reload udev after installing the MacBookPro10,1 pstate rule. Ask an administrator to run omarchy-migrate." >&2
  exit 1
fi
