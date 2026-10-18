import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import "background" as BackgroundPlugin

ShellRoot {
  id: shell
  function firstPartyServiceFor(id) { return id === "omarchy.background" ? background : null }
  BackgroundPlugin.Background { id: background }

  property bool themeSetupCompleted: false

  // APPLY_THEME_FUNCTION

  Timer {
    interval: 600
    running: true
    onTriggered: {
      console.log("MILESTONE pending-theme-setup-started")
      var oldColors = Qt.btoa('accent = "#ff0000"\nbackground = "#000000"\nforeground = "#ffffff"\n')
      var newColors = Qt.btoa('accent = "#123456"\nbackground = "#000000"\nforeground = "#ffffff"\n')
      background.transitionBackgroundWithTheme("", "/missing-still.png", "/missing-still.png", oldColors, "")
      var result = shell.applyTheme(newColors, "")
      console.log("MILESTONE pending-theme-apply-completed")
      if (result !== "ok" || !Qt.colorEqual(Commons.Color.accent, "#123456")) {
        console.log("RESULT fail the authoritative palette applies immediately: " + Commons.Color.accent)
        Qt.quit()
      } else {
        shell.themeSetupCompleted = true
        retention.start()
      }
    }
  }
  Timer {
    id: retention
    // Preserve the original nominal 600→1300ms retention gap, but measure
    // it from completed setup rather than assume independent timer ordering.
    interval: 700
    running: false
    onTriggered: {
      if (shell.themeSetupCompleted && Qt.colorEqual(Commons.Color.accent, "#123456")) {
        console.log("RESULT pass")
      } else {
        console.log("RESULT fail previous colors returned: " + Commons.Color.accent)
      }
      Qt.quit()
    }
  }
}
