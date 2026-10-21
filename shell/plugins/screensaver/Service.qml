import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import "ScreensaverModel.js" as Model

// Maslow screensaver controller. Owns the showing state, the single frame
// Timer and the IPC target; ScreensaverWindow draws one overlay per real
// screen while active and nothing exists while it is not. The terminal
// screensaver stays the classic style and the launcher's fallback.
Item {
  id: root

  // Injected by omarchy-shell (the first-party service loader). With no
  // shell the service stays inert: default style, nothing showing.
  property var shell: null
  property string omarchyPath: ""
  property var manifest: null

  readonly property int dismissThreshold: 12
  readonly property int armDelayMs: 600
  readonly property int lockHandoffMs: 1500

  readonly property string effectiveStyle: Model.resolveStyle(shell ? shell.shellConfig : null)
  readonly property bool active: showing
  readonly property var orderedScreens: Model.orderScreens(Quickshell.screens)
  readonly property var lockService: shell && typeof shell.serviceFor === "function" ? shell.serviceFor("omarchy.lock") : null
  readonly property bool locked: !!(lockService && lockService.locked)
  readonly property bool onBattery: !!(UPower.displayDevice && UPower.displayDevice.isPresent && UPower.onBattery)
  readonly property string motion: Model.resolveMotion(shell ? shell.shellConfig : null)
  readonly property bool reducedMotion: Model.reducedFor(motion, systemReducedMotion)
  readonly property int fps: Model.fpsFor(reducedMotion, onBattery)

  property bool showing: false
  // A lock is coming: the picture freezes now and unmaps once the lock
  // surface has had time to cover it, so the desktop never flashes between.
  property bool handingOff: false
  property bool inputArmed: false
  property bool systemReducedMotion: false
  property real startedAt: 0
  property real elapsedMs: 0
  property int reducedCycle: 0
  property string shownAt: ""
  property string lastEvent: "init"
  property string lastEventAt: ""

  // Hours and minutes only, in the locale's 12- or 24-hour habit; the clock
  // is display type, so the AM/PM suffix is left out.
  readonly property bool twelveHour: /a|AP/i.test(Qt.locale().timeFormat(Locale.ShortFormat))
  readonly property string clockText: Qt.formatTime(clock.date, twelveHour ? "h:mm" : "HH:mm")

  function logEvent(event) {
    lastEvent = event
    lastEventAt = new Date().toISOString()
    console.log("maslow screensaver " + lastEventAt + " " + event)
  }

  // The idle service counts the native screensaver as one window, so its
  // launch grace and dismiss-cancels-lock logic cover both renderers.
  function reportIdle(visible) {
    var idle = shell && typeof shell.serviceFor === "function" ? shell.serviceFor("omarchy.idle") : null
    if (idle && typeof idle.setNativeScreensaverVisible === "function") idle.setNativeScreensaverVisible(visible)
  }

  function present(ignoreStyle) {
    if (!ignoreStyle && effectiveStyle === "classic") return "classic"
    if (locked) return "locked"
    if (orderedScreens.length === 0) return "no-screens"

    if (!showing) {
      startedAt = Date.now()
      elapsedMs = 0
      reducedCycle = 0
      shownAt = new Date(startedAt).toISOString()
      inputArmed = false
      showing = true
      // Variants builds the overlays synchronously. If none came up, say so,
      // so the launcher falls back to the classic screensaver instead of
      // trusting an "ok" with nothing on screen.
      if (windows.instances.length === 0) {
        showing = false
        logEvent("no-windows")
        return "no-screens"
      }
      armTimer.restart()
      logEvent(ignoreStyle ? "preview" : "show")
    }
    reportIdle(true)
    return "ok"
  }

  function show() {
    return present(false)
  }

  function preview() {
    return present(true)
  }

  function hide() {
    if (!showing) return "ok"
    if (locked) beginHandoff()
    else finishHide("hide")
    return "ok"
  }

  function dismiss(reason) {
    if (!showing || handingOff || !inputArmed) return
    if (locked) beginHandoff()
    else finishHide("dismiss: " + reason)
  }

  function beginHandoff() {
    if (!showing || handingOff) return
    handingOff = true
    handoffTimer.restart()
    logEvent("lock-handoff")
  }

  function finishHide(event) {
    if (!showing) return
    handoffTimer.stop()
    armTimer.stop()
    handingOff = false
    inputArmed = false
    showing = false
    logEvent(event)
    reportIdle(false)
  }

  function statusJson() {
    return JSON.stringify({
      active: root.active,
      style: root.effectiveStyle,
      reducedMotion: root.reducedMotion,
      motion: root.motion,
      onBattery: root.onBattery,
      fps: root.active && !root.handingOff ? root.fps : 0,
      screens: root.orderedScreens.length,
      shownAt: root.shownAt,
      lastEvent: root.lastEvent,
      lastEventAt: root.lastEventAt
    })
  }

  onLockedChanged: if (locked && showing) beginHandoff()
  onOrderedScreensChanged: if (showing && orderedScreens.length === 0) finishHide("no-screens")

  Component.onDestruction: {
    if (showing) {
      showing = false
      reportIdle(false)
    }
  }

  // The only clock: every visual is a pure function of elapsedMs.
  Timer {
    id: ticker
    interval: root.fps > 0 ? Math.round(1000 / root.fps) : 1000
    repeat: true
    running: root.active && !root.handingOff && root.fps > 0
    onTriggered: root.elapsedMs = Date.now() - root.startedAt
  }

  // Reduced Motion runs no frames; the composition still moves, instantly.
  Timer {
    interval: Model.REDUCED_REPOSITION_MS
    repeat: true
    running: root.active && !root.handingOff && root.reducedMotion
    onTriggered: root.reducedCycle += 1
  }

  Timer {
    id: armTimer
    interval: root.armDelayMs
    repeat: false
    onTriggered: root.inputArmed = true
  }

  Timer {
    id: handoffTimer
    interval: root.lockHandoffMs
    repeat: false
    onTriggered: root.finishHide("lock-handoff: done")
  }

  SystemClock {
    id: clock
    enabled: root.active
    precision: SystemClock.Minutes
  }

  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/toggles/hypr/reduced-motion.lua"
    watchChanges: true
    printErrors: false
    onLoaded: root.systemReducedMotion = String(text() || "").trim().length > 0
    onFileChanged: reload()
    onLoadFailed: root.systemReducedMotion = false
  }

  Variants {
    id: windows
    model: root.active ? root.orderedScreens : []

    ScreensaverWindow {
      service: root
      screenIndex: Math.max(0, root.orderedScreens.indexOf(modelData))
      screenCount: Math.max(1, root.orderedScreens.length)
    }
  }

  IpcHandler {
    target: "screensaver"

    function show(): string {
      return root.show()
    }

    function preview(): string {
      return root.preview()
    }

    function hide(): string {
      return root.hide()
    }

    function status(): string {
      return root.statusJson()
    }

    function style(): string {
      return root.effectiveStyle
    }
  }
}
