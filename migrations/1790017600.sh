echo "Preserve Maslow's packaged Hermes ownership"

# Upstream moves Hermes to a self-updating desktop checkout. Maslow Voice
# consumes its reviewed package; do not retire or bootstrap a replacement.
if omarchy-pkg-present hermes-agent; then
  source "$OMARCHY_PATH/install/helpers/agent.sh"
  omarchy_agent_prepare_packaged hermes
fi
