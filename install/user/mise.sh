source "$OMARCHY_PATH/install/helpers/agent.sh"
omarchy_agent_prepare_packaged codex || true
omarchy_agent_prepare_packaged claude || true
omarchy_agent_prepare_packaged hermes || true
omarchy-mise-install crush
omarchy-mise-install antigravity-cli agy
omarchy-mise-install gh
omarchy-mise-install copilot
omarchy-mise-install opencode
omarchy-mise-install npm:playwright playwright
omarchy-mise-install pi
omarchy-mise-install github:can1357/oh-my-pi omp
omarchy-mise-install npm:@xai-official/grok grok
omarchy-mise-install npm:@kitlangton/ghui ghui
omarchy-mise-install aqua:modem-dev/hunk hunk
omarchy-mise-install github:basecamp/hey-cli hey
omarchy-mise-install github:OpenRouterLabs/ori-releases ori
