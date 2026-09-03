# Shared Maslow OS console presentation and accessibility behavior. This file is
# sourced by the live ISO configurator and deferred first-boot owner setup.

maslow_product_manifest="${MASLOW_PRODUCT_FILE:-/usr/share/maslow-os/product.json}"
[[ -r $maslow_product_manifest ]] || maslow_product_manifest="${OMARCHY_PATH:-/usr/share/omarchy}/branding/product.json"
if [[ ! -r $maslow_product_manifest ]]; then
  echo "Maslow OS product manifest is unavailable." >&2
  return 1
fi
MASLOW_PRODUCT_NAME=$(jq -er '.product.name' "$maslow_product_manifest")
MASLOW_PRODUCT_TAGLINE=$(jq -er '.product.tagline' "$maslow_product_manifest")
MASLOW_GUM_PROMPT_FOREGROUND="2"
MASLOW_ACCESSIBILITY_CONFIG="${MASLOW_ACCESSIBILITY_CONFIG:-/etc/maslow-os/accessibility.conf}"

MASLOW_SPEECH=false
MASLOW_LARGE_TEXT=false
MASLOW_HIGH_CONTRAST=false
MASLOW_REDUCED_MOTION=false

maslow_console_apply_palette() {
  [[ $(tty 2>/dev/null) == /dev/tty* ]] || return 0
  echo -en "\e]P0121d35"; echo -en "\e]P1ff7a90"; echo -en "\e]P26dc4ad"
  echo -en "\e]P3f6c85f"; echo -en "\e]P48fb4ff"; echo -en "\e]P5ee7bb3"
  echo -en "\e]P679d4c3"; echo -en "\e]P7d9dee8"; echo -en "\e]P88c95a8"
  echo -en "\e]P9ff9bad"; echo -en "\e]PA8ad7c1"; echo -en "\e]PBffd982"
  echo -en "\e]PCadc8ff"; echo -en "\e]PDf5a1cb"; echo -en "\e]PE9be4d5"
  echo -en "\e]PFffffff"
  echo -en "\033[0m"
  clear
}

maslow_accessibility_read_value() {
  local key="$1" value=""
  if [[ -r $MASLOW_ACCESSIBILITY_CONFIG ]]; then
    value=$(sed -n "s/^${key}=//p" "$MASLOW_ACCESSIBILITY_CONFIG" | tail -1)
  fi
  printf '%s' "$value"
}

maslow_accessibility_load() {
  [[ $(maslow_accessibility_read_value speech) == "true" ]] && MASLOW_SPEECH=true
  [[ $(maslow_accessibility_read_value large_text) == "true" ]] && MASLOW_LARGE_TEXT=true
  [[ $(maslow_accessibility_read_value high_contrast) == "true" ]] && MASLOW_HIGH_CONTRAST=true
  [[ $(maslow_accessibility_read_value reduced_motion) == "true" ]] && MASLOW_REDUCED_MOTION=true

  if grep -qw 'accessibility=on' /proc/cmdline 2>/dev/null; then
    MASLOW_SPEECH=true
    MASLOW_REDUCED_MOTION=true
  fi
  export MASLOW_SPEECH MASLOW_LARGE_TEXT MASLOW_HIGH_CONTRAST MASLOW_REDUCED_MOTION
}

maslow_accessibility_save() {
  local directory tmp
  directory=$(dirname "$MASLOW_ACCESSIBILITY_CONFIG")
  mkdir -p "$directory"
  tmp=$(mktemp "$directory/.accessibility.XXXXXX")
  chmod 0644 "$tmp"
  printf 'speech=%s\nlarge_text=%s\nhigh_contrast=%s\nreduced_motion=%s\n' \
    "$MASLOW_SPEECH" "$MASLOW_LARGE_TEXT" "$MASLOW_HIGH_CONTRAST" "$MASLOW_REDUCED_MOTION" >"$tmp"
  mv "$tmp" "$MASLOW_ACCESSIBILITY_CONFIG"
}

maslow_console_start_speech() {
  [[ $MASLOW_SPEECH == "true" ]] || return 0
  modprobe speakup_soft 2>/dev/null || true
  systemctl start espeakup.service 2>/dev/null || true
}

maslow_console_speak() {
  [[ $MASLOW_SPEECH == "true" ]] || return 0
  local message="$*"
  [[ $message == *"Password"* || $message == *"password"* ]] && return 0
  if command -v espeak-ng >/dev/null 2>&1; then
    espeak-ng -- "$message" >/dev/null 2>&1 || true
  fi
}

maslow_console_accessibility_menu() {
  local selected status=0
  maslow_console_speak "Accessibility. Use Space to select options, then press Enter."
  selected=$(printf '%s\n' \
    "Spoken setup" \
    "Larger text" \
    "High contrast" \
    "Reduce motion" |
    gum choose --no-limit --height 8 --header "Accessibility — Space selects, Enter applies") || status=$?
  (( status == 0 )) || return "$status"

  MASLOW_SPEECH=false
  MASLOW_LARGE_TEXT=false
  MASLOW_HIGH_CONTRAST=false
  MASLOW_REDUCED_MOTION=false
  grep -Fxq "Spoken setup" <<<"$selected" && MASLOW_SPEECH=true
  grep -Fxq "Larger text" <<<"$selected" && MASLOW_LARGE_TEXT=true
  grep -Fxq "High contrast" <<<"$selected" && MASLOW_HIGH_CONTRAST=true
  grep -Fxq "Reduce motion" <<<"$selected" && MASLOW_REDUCED_MOTION=true
  export MASLOW_SPEECH MASLOW_LARGE_TEXT MASLOW_HIGH_CONTRAST MASLOW_REDUCED_MOTION
  maslow_accessibility_save
  maslow_console_start_speech
  maslow_console_speak "Accessibility preferences applied."
}

maslow_console_key_is_f5() {
  local first="$1" rest=""
  [[ $first == $'\e' ]] || return 1
  IFS= read -rsn4 -t 0.15 rest </dev/tty || true
  [[ $first$rest == $'\e[15~' ]]
}

maslow_accessibility_load
