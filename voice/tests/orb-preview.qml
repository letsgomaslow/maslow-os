import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import "../ui" as Voice
ShellRoot {
  // Apply an optional test palette after the shared Color startup read.
  Timer { interval: 250; running: Quickshell.env("THEME_COLORS") !== ""; onTriggered: Color.loadColors(Quickshell.env("THEME_COLORS")) }
  // Isolated, output-only rendering fixture. It never creates a Voice controller.
  FloatingWindow {
    id: window
    visible: true
    color: Color.background
    implicitWidth: 640
    implicitHeight: 580
    Rectangle {
      color: Color.background
      id: gallery
      // Keep the captured scene complete even when a tiling compositor gives
      // the preview window less space than its requested dimensions.
      width: 640
      height: 580
      Text { x: 16; y: 16; text: "UI preview · " + (Quickshell.env("THEME_NAME") || "current theme"); color: Color.foreground }
      Column {
        anchors.centerIn: parent
        spacing: 20
        Repeater {
          model: [56, 88]
          Grid {
            columns: 5
            rowSpacing: 12
            id: row
            required property int modelData
            spacing: 16
            Repeater {
              model: ["idle", "connecting", "listening", "thinking", "working", "speaking", "paused", "error", "disabled", "completed"]
              Column {
                required property string modelData
                spacing: 8
                width: 112
                Voice.VoiceOrb {
                  anchors.horizontalCenter: parent.horizontalCenter
                  width: row.modelData
                  height: width
                  voiceState: parent.modelData === "completed" ? "idle" : parent.modelData
                  disabled: parent.modelData === "disabled"
                  reducedMotion: Quickshell.env("REDUCED") === "1"
                  audioLevel: 0.14
                  playbackLevel: parent.modelData === "speaking" ? 0.18 : 0
                  microphoneActive: ["listening", "thinking", "speaking"].indexOf(parent.modelData) >= 0
                  accentColor: Color.accent
                  backgroundColor: Color.background
                  gpuShaderAvailable: Quickshell.env("MASLOW_VOICE_GPU_SHADER") !== "0"
                  // The completion reaction plays once from the start of the capture.
                  Component.onCompleted: if (parent.modelData === "completed") completionSequence = 1
                }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: parent.modelData + " " + row.modelData; color: Color.foreground; font.pixelSize: 12 }
              }
            }
          }
        }
      }
    }
    // GALLERY_FRAMES=n saves n numbered captures 400 ms apart for checking motion.
    property int frames: Math.max(1, Number(Quickshell.env("GALLERY_FRAMES") || 1))
    property int captured: 0
    Timer {
      interval: window.frames > 1 ? 400 : 1500
      repeat: true
      running: Quickshell.env("GALLERY_OUTPUT") !== ""
      onTriggered: {
        const index = window.captured++
        const path = window.frames > 1 ? Quickshell.env("GALLERY_OUTPUT").replace(/\.png$/, "-" + String(index).padStart(2, "0") + ".png") : Quickshell.env("GALLERY_OUTPUT")
        gallery.grabToImage(function(result) {
          result.saveToFile(path)
          console.log("Gallery saved " + path)
          if (index + 1 >= window.frames) Qt.quit()
        })
        if (index + 1 >= window.frames) stop()
      }
    }
  }
}
