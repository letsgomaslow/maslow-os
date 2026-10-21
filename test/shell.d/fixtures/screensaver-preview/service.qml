import QtQuick
import Quickshell
import "screensaver/ScreensaverModel.js" as Model

// Drives the real screensaver Service through every refusal path: no shell,
// classic style and a pending lock, and through the screensaver.motion
// setting while locked. None of them may map an overlay, which is what makes
// this safe to run against a live compositor. The test seeds the Reduced
// Motion toggle in its temporary HOME.
ShellRoot {
  id: root

  readonly property string resultPath: Quickshell.env("OMARCHY_QML_TEST_RESULT")
  readonly property string rootPath: Quickshell.env("OMARCHY_PATH")
  property var failures: []
  property var service: null
  property int waits: 0

  function fail(message) {
    failures.push(String(message))
  }

  function assertTrue(condition, message) {
    if (!condition) fail(message)
  }

  function shellQuote(value) {
    return "'" + String(value).replace(/'/g, "'\\''") + "'"
  }

  function writeResult() {
    var payload = JSON.stringify({
      ok: failures.length === 0,
      failures: failures,
      idleCalls: idle.calls
    })

    if (resultPath) {
      Quickshell.execDetached(["bash", "-lc", "printf '%s' " + shellQuote(payload) + " > " + shellQuote(resultPath)])
    }
  }

  QtObject {
    id: idle
    property var calls: []
    function setNativeScreensaverVisible(visible) {
      var next = calls.slice()
      next.push(visible)
      calls = next
    }
  }

  QtObject {
    id: lock
    property bool locked: false
  }

  QtObject {
    id: mockShell
    property var shellConfig: ({ screensaver: { style: "classic" } })
    function serviceFor(id) {
      if (id === "omarchy.idle") return idle
      if (id === "omarchy.lock") return lock
      return null
    }
  }

  Item { id: host }

  function create(shell) {
    var component = Qt.createComponent("file://" + root.rootPath + "/shell/plugins/screensaver/Service.qml", Component.PreferSynchronous)
    if (component.status !== Component.Ready) {
      root.fail("screensaver Service failed to load: " + component.errorString())
      return null
    }
    var item = component.createObject(host, { omarchyPath: root.rootPath })
    if (!item) {
      root.fail("screensaver Service failed to instantiate: " + component.errorString())
      return null
    }
    item.shell = shell
    return item
  }

  function checkInert() {
    var inert = create(null)
    if (!inert) return
    assertTrue(inert.active === false, "service without a shell is inactive")
    assertTrue(inert.effectiveStyle === "maslow", "service without a shell reports the maslow style, got " + inert.effectiveStyle)
    assertTrue(inert.motion === "auto", "service without a shell follows the system motion setting, got " + inert.motion)
    assertTrue(inert.hide() === "ok", "hide is idempotent while inactive")
    var status = JSON.parse(inert.statusJson())
    var keys = ["active", "style", "reducedMotion", "motion", "onBattery", "fps", "screens", "shownAt", "lastEvent", "lastEventAt"]
    for (var i = 0; i < keys.length; i++) assertTrue(keys[i] in status, "status reports " + keys[i])
    assertTrue(status.active === false && status.fps === 0, "inactive status reports no frames")
    inert.destroy()
  }

  function checkRefusals() {
    var s = root.service
    assertTrue(s.effectiveStyle === "classic", "service reads the classic style from shell config")
    assertTrue(s.show() === "classic", "show defers to the classic style")
    assertTrue(s.active === false, "classic show maps nothing")

    lock.locked = true
    // Everything below would map overlays if the lock were not seen, so stop
    // here rather than risk drawing over the session running the test.
    if (s.locked !== true) {
      root.fail("service follows the lock service")
      return
    }
    assertTrue(s.preview() === "locked", "preview refuses while locked")
    mockShell.shellConfig = { screensaver: { style: "maslow" } }
    assertTrue(s.effectiveStyle === "maslow", "service follows shell config changes")
    assertTrue(s.show() === "locked", "show refuses while locked")
    assertTrue(s.active === false, "locked show maps nothing")
    assertTrue(s.hide() === "ok", "hide answers ok while inactive")
    assertTrue(idle.calls.length === 0, "refused shows never report a visible screensaver, got " + JSON.stringify(idle.calls))

    assertTrue(s.systemReducedMotion === true, "Reduced Motion toggle is read from the state file")
    assertTrue(s.motion === "auto" && s.reducedMotion === true, "auto motion follows the system Reduced Motion toggle")
    assertTrue(s.fps === 0, "Reduced Motion runs no frames, got " + s.fps)
    var status = JSON.parse(s.statusJson())
    assertTrue(status.style === "maslow" && status.reducedMotion === true && status.motion === "auto", "status reports style, motion and Reduced Motion")

    mockShell.shellConfig = { screensaver: { style: "maslow", motion: "full" } }
    assertTrue(s.motion === "full", "service reads full motion from shell config, got " + s.motion)
    assertTrue(s.systemReducedMotion === true && s.reducedMotion === false, "full motion overrides the system Reduced Motion toggle")
    assertTrue(s.fps === Model.fpsFor(false, s.onBattery) && s.fps > 0, "full motion runs frames, got " + s.fps)
    status = JSON.parse(s.statusJson())
    assertTrue(status.motion === "full" && status.reducedMotion === false, "status reports full motion")
    assertTrue(status.active === false && status.fps === 0, "status reports no frames while nothing is showing")
    assertTrue(s.show() === "locked", "show still refuses while locked with full motion")

    mockShell.shellConfig = { screensaver: { style: "maslow", motion: "reduced" } }
    assertTrue(s.motion === "reduced" && s.reducedMotion === true && s.fps === 0, "reduced motion always holds still")

    mockShell.shellConfig = { screensaver: { style: "maslow", motion: "sideways" } }
    assertTrue(s.motion === "auto" && s.reducedMotion === true, "an unknown motion value falls back to auto")

    assertTrue(s.active === false, "motion changes map nothing")
    assertTrue(idle.calls.length === 0, "refused shows never report a visible screensaver, got " + JSON.stringify(idle.calls))
  }

  Timer {
    interval: 50
    repeat: true
    running: true
    onTriggered: {
      try {
        if (!root.service) {
          root.checkInert()
          root.service = root.create(mockShell)
          if (!root.service) {
            stop()
            root.writeResult()
          }
          return
        }
        // The Reduced Motion FileView loads asynchronously.
        if (!root.service.systemReducedMotion && root.waits++ < 40) return
        stop()
        root.checkRefusals()
      } catch (error) {
        stop()
        root.fail("screensaver service fixture threw: " + error)
      }
      if (!running) {
        if (root.service) root.service.destroy()
        root.writeResult()
      }
    }
  }
}
