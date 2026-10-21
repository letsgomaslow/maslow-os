// Maslow AI-OS: the maslow.screensaver plugin reports itself to the idle
// service as one pseudo window under this key. It is deliberately not a hex
// window address, so a Hyprland closewindow event can never match it.
var address = "maslow-native-screensaver"

if (typeof module !== "undefined") {
  module.exports = {
    address: address
  }
}
