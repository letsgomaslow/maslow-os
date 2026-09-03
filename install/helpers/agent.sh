# Shared agent metadata and installation behavior for Maslow-managed entry points.

omarchy_agent_resolve() {
  case "${1:-}" in
  pi) OMARCHY_AGENT_ID="pi"; OMARCHY_AGENT_NAME="Pi"; OMARCHY_AGENT_PACKAGE="pi" ;;
  omp | oh-my-pi) OMARCHY_AGENT_ID="omp"; OMARCHY_AGENT_NAME="Oh My Pi"; OMARCHY_AGENT_PACKAGE="github:can1357/oh-my-pi" ;;
  opencode | open-code) OMARCHY_AGENT_ID="opencode"; OMARCHY_AGENT_NAME="OpenCode"; OMARCHY_AGENT_PACKAGE="opencode" ;;
  ori | openrouter) OMARCHY_AGENT_ID="ori"; OMARCHY_AGENT_NAME="Ori"; OMARCHY_AGENT_PACKAGE="github:OpenRouterLabs/ori-releases" ;;
  claude | claude-code) OMARCHY_AGENT_ID="claude"; OMARCHY_AGENT_NAME="Claude Code"; OMARCHY_AGENT_PACKAGE="claude" ;;
  codex) OMARCHY_AGENT_ID="codex"; OMARCHY_AGENT_NAME="Codex"; OMARCHY_AGENT_PACKAGE="codex" ;;
  crush) OMARCHY_AGENT_ID="crush"; OMARCHY_AGENT_NAME="Crush"; OMARCHY_AGENT_PACKAGE="crush" ;;
  grok) OMARCHY_AGENT_ID="grok"; OMARCHY_AGENT_NAME="Grok"; OMARCHY_AGENT_PACKAGE="npm:@xai-official/grok" ;;
  agy | antigravity | antigravity-cli | gemini | gemini-cli) OMARCHY_AGENT_ID="agy"; OMARCHY_AGENT_NAME="Antigravity"; OMARCHY_AGENT_PACKAGE="antigravity-cli" ;;
  hermes) OMARCHY_AGENT_ID="hermes"; OMARCHY_AGENT_NAME="Hermes"; OMARCHY_AGENT_PACKAGE="hermes" ;;
  copilot | github-copilot) OMARCHY_AGENT_ID="copilot"; OMARCHY_AGENT_NAME="GitHub Copilot"; OMARCHY_AGENT_PACKAGE="copilot" ;;
  *) return 1 ;;
  esac
}

omarchy_agent_launch_mode() {
  case "$1" in
  opencode) printf '%s' "opencode:--auto" ;;
  agy) printf '%s' "agy:--dangerously-skip-permissions" ;;
  copilot) printf '%s' "copilot:--allow-all" ;;
  crush) printf '%s' "crush:--yolo" ;;
  claude) printf '%s' "claude:--permission-mode=auto" ;;
  grok) printf '%s' "grok:--permission-mode=bypassPermissions" ;;
  codex) printf '%s' "codex:--approve-for-me" ;;
  hermes) printf '%s' "hermes:--yolo" ;;
  omp) printf '%s' "omp:--auto-approve" ;;
  ori) printf '%s' "ori:code" ;;
  pi) printf '%s' "pi:interactive" ;;
  *) return 1 ;;
  esac
}

omarchy_agent_is_installed() {
  if [[ $OMARCHY_AGENT_ID == "hermes" ]]; then
    omarchy-install-hermes-cli --check
  else
    mise where "$OMARCHY_AGENT_PACKAGE" &>/dev/null
  fi
}

omarchy_agent_install_only() {
  if [[ $OMARCHY_AGENT_ID == "hermes" ]]; then
    omarchy-install-hermes-cli --now
  else
    mise use -g "$OMARCHY_AGENT_PACKAGE"
  fi
}
