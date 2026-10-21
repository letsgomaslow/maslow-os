import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Ui

// One full-screen overlay per real output while the screensaver is showing.
// It only draws and listens: any key, button, wheel or deliberate pointer
// movement asks the service to dismiss, and the service decides what that
// means (ignored while arming, handed off when a lock is on its way).
PanelWindow {
  id: window

  required property var modelData
  property var service: null
  property int screenIndex: 0
  property int screenCount: 1

  screen: modelData
  visible: true
  color: "#121D35"

  WlrLayershell.namespace: "maslow-screensaver"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
  exclusionMode: ExclusionMode.Ignore
  anchors { top: true; bottom: true; left: true; right: true }

  function dismiss(reason) {
    if (window.service) window.service.dismiss(reason)
  }

  FocusScope {
    anchors.fill: parent
    focus: true

    Keys.onPressed: function(event) {
      event.accepted = true
      window.dismiss("key")
    }

    ScreensaverScene {
      anchors.fill: parent
      omarchyPath: window.service ? window.service.omarchyPath : ""
      elapsedMs: window.service ? window.service.elapsedMs : 0
      screenIndex: window.screenIndex
      screenCount: window.screenCount
      reducedMotion: window.service ? window.service.reducedMotion : false
      repositionCycle: window.service ? window.service.reducedCycle : 0
      clockText: window.service ? window.service.clockText : ""
    }

    // A screensaver that wakes on a nudged desk is a nuisance, so the
    // pointer has to travel past the threshold from where it was first seen.
    PointerMoveGate {
      id: pointerGate
      referenceItem: pointerArea
      threshold: window.service ? window.service.dismissThreshold : 12
    }

    MouseArea {
      id: pointerArea
      anchors.fill: parent
      hoverEnabled: true
      acceptedButtons: Qt.AllButtons
      cursorShape: Qt.BlankCursor
      onPressed: function(mouse) {
        mouse.accepted = true
        window.dismiss("button")
      }
      onWheel: function(wheel) {
        wheel.accepted = true
        window.dismiss("wheel")
      }
      onPositionChanged: function(mouse) {
        if (pointerGate.moved(pointerArea, mouse)) window.dismiss("pointer")
      }
    }
  }
}
