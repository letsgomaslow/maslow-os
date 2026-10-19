# On the 2012 15-inch Retina MacBook Pro (MacBookPro10,1), the only viable
# driver for the internal display is nouveau, which has no automatic/dynamic
# reclocking at all for its NVIDIA GK107 (GT650M) Kepler-generation GPU. It
# parks the chip at a conservative default pstate (core 405MHz / memory
# 680MHz) regardless of load, which is the dominant cause of desktop
# sluggishness on this hardware.
#
# Install a udev rule that reacts to the real ACPI AC-adapter power_supply
# event and forces an elevated pstate while on mains power, forcing the
# lowest pstate back on battery to preserve battery life and avoid
# unnecessary heat. See bin/omarchy-hw-macbookpro10-1-pstate-switch for the
# exact pstate values, why 0e/0f are deliberately never used, and why the
# battery target must be an explicit pstate rather than nouveau's own "AC"
# row label or its "auto" keyword -- neither does what the name suggests on
# this hardware. Runs as root with no terminal, so this needs no interactive
# sudo/password at runtime.
if omarchy-hw-macbookpro10-1; then
  sudo mkdir -p /etc/udev/rules.d
  if [[ ! -f /etc/udev/rules.d/90-omarchy-macbookpro10-1-pstate.rules ]]; then
    sudo cp -f "$OMARCHY_PATH/default/udev/macbookpro10-1-pstate.rules" /etc/udev/rules.d/90-omarchy-macbookpro10-1-pstate.rules
  fi
fi
