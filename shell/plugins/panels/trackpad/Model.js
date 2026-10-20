// Nerd Font touchpad glyph (U+F07F8), written as a surrogate pair so editors
// cannot strip the codepoint.
var ICON = "󰟸"

var BOOLEAN_KEYS = [
  "present",
  "enabled",
  "tap_to_click",
  "natural_scroll",
  "clickfinger_behavior",
  "disable_while_typing",
  "workspace_swipe",
  "drag_3fg",
  "window_gestures"
]

function parseStatus(raw) {
  var status = { present: false }
  var lines = String(raw || "").split("\n")
  for (var i = 0; i < lines.length; i++) {
    var idx = lines[i].indexOf("\t")
    if (idx <= 0) continue
    status[lines[i].substring(0, idx)] = lines[i].substring(idx + 1).trim()
  }

  for (var k = 0; k < BOOLEAN_KEYS.length; k++) {
    var key = BOOLEAN_KEYS[k]
    status[key] = status[key] === "true"
  }

  var speed = Number(status.speed)
  status.speed = isFinite(speed) ? Math.max(-1, Math.min(1, speed)) : 0
  return status
}

// Rows for the switch list, in display order. `command` is the
// omarchy-trackpad-set setting name.
function settingRows(status) {
  var s = status || {}
  return [
    {
      command: "tap-to-click",
      label: "Tap to click",
      description: "Tap lightly instead of pressing the pad down.",
      checked: !!s.tap_to_click
    },
    {
      command: "two-finger-right-click",
      label: "Two-finger right click",
      description: s.clickfinger_behavior
        ? "Press with two fingers to right click."
        : "Off: press the bottom-right corner to right click.",
      checked: !!s.clickfinger_behavior
    },
    {
      command: "natural-scroll",
      label: "Natural scrolling",
      description: "Content follows your fingers, like on a Mac.",
      checked: !!s.natural_scroll
    },
    {
      command: "three-finger-drag",
      label: "Three-finger drag",
      description: "Rest three fingers and slide to drag, without pressing the pad down.",
      checked: !!s.drag_3fg
    },
    {
      command: "workspace-swipe",
      label: s.drag_3fg ? "Four-finger workspace swipe" : "Three-finger workspace swipe",
      description: s.drag_3fg
        ? "Swipe left or right with four fingers to switch workspaces. Four, because three fingers drag."
        : "Swipe left or right with three fingers to switch workspaces.",
      checked: !!s.workspace_swipe
    },
    {
      command: "window-gestures",
      label: "Window gestures",
      description: s.drag_3fg
        ? "Hold Super and drag with three fingers to move a window. Hold Super and swipe with four fingers to resize it."
        : "Hold Super and swipe with three fingers to move a window, or four fingers to resize it.",
      checked: !!s.window_gestures
    },
    {
      command: "ignore-while-typing",
      label: "Ignore trackpad while typing",
      description: "Stops a resting palm from moving the pointer.",
      checked: !!s.disable_while_typing
    }
  ]
}

// How-to rows that describe what each gesture does with the current settings.
function guideRows(status) {
  var s = status || {}
  var rows = [
    { fingers: "1", gesture: "Press down", action: "Left click" }
  ]

  if (s.clickfinger_behavior) {
    rows.push({ fingers: "2", gesture: "Press down", action: "Right click" })
    rows.push({ fingers: "3", gesture: "Press down", action: "Middle click" })
  } else {
    rows.push({ fingers: "1", gesture: "Press bottom-right corner", action: "Right click" })
  }

  if (s.tap_to_click) {
    rows.push({ fingers: "1", gesture: "Tap", action: "Left click" })
    rows.push({ fingers: "2", gesture: "Tap", action: "Right click" })
    rows.push({ fingers: "1", gesture: "Tap, then touch and slide", action: "Drag" })
  }

  if (s.drag_3fg) {
    rows.push({ fingers: "3", gesture: "Rest and slide", action: "Drag" })
  }

  rows.push({
    fingers: "2",
    gesture: "Slide up or down",
    action: s.natural_scroll ? "Scroll (natural)" : "Scroll"
  })

  if (s.window_gestures) {
    rows.push({ fingers: "3", gesture: s.drag_3fg ? "Hold Super, drag" : "Hold Super, swipe", action: "Move window" })
    rows.push({ fingers: "4", gesture: "Hold Super, swipe", action: "Resize window" })
  }

  if (s.workspace_swipe) {
    rows.push({ fingers: s.drag_3fg ? "4" : "3", gesture: "Swipe left or right", action: "Switch workspace" })
  }

  return rows
}

function speedLabel(speed) {
  var value = Number(speed) || 0
  if (Math.abs(value) < 0.05) return "Default"
  return (value > 0 ? "+" : "") + Math.round(value * 100) + "%"
}

if (typeof module !== "undefined") {
  module.exports = {
    ICON: ICON,
    parseStatus: parseStatus,
    settingRows: settingRows,
    guideRows: guideRows,
    speedLabel: speedLabel
  }
}
