echo "Refresh Maslow OS theme artwork"

theme_name_path="$HOME/.local/state/omarchy/current/theme.name"

[[ -s $theme_name_path ]] || exit 0

theme_name=$(<"$theme_name_path")

case "$theme_name" in
  maslow-dark | maslow-light) omarchy-theme-refresh ;;
esac
