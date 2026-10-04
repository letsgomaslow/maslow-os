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
    implicitWidth: 520
    implicitHeight: 580
    Rectangle {
      color: Color.background
      id: gallery
      // Keep the captured scene complete even when a tiling compositor gives
      // the preview window less space than its requested dimensions.
      width: 520
      height: 580
      Text { x: 16; y: 16; text: "UI preview · " + (Quickshell.env("THEME_NAME") || "current theme"); color: Color.foreground }
      Column {
        anchors.centerIn: parent
        spacing: 20
        Repeater {
          model: [56, 88]
          Grid {
            columns: 4
            rowSpacing: 12
            id: row
            required property int modelData
            spacing: 16
            Repeater {
              model: ["idle", "connecting", "listening", "thinking", "speaking", "paused", "error", "disabled"]
              Column {
                required property string modelData
                spacing: 8
                width: 112
                Voice.VoiceOrb {
                  anchors.horizontalCenter: parent.horizontalCenter
                  width: row.modelData
                  height: width
                  voiceState: parent.modelData
                  disabled: parent.modelData === "disabled"
                  reducedMotion: Quickshell.env("REDUCED") === "1"
                  audioLevel: 0.14
                  playbackLevel: parent.modelData === "speaking" ? 0.18 : 0
                  microphoneActive: ["listening", "thinking", "speaking"].indexOf(parent.modelData) >= 0
                  accentColor: Color.accent
                  backgroundColor: Color.background
                  gpuShaderAvailable: Quickshell.env("MASLOW_VOICE_GPU_SHADER") !== "0"
                }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: parent.modelData + " " + row.modelData; color: Color.foreground; font.pixelSize: 12 }
              }
            }
          }
        }
      }
    }
    Timer { interval: 1500; running: Quickshell.env("GALLERY_OUTPUT") !== ""; onTriggered: gallery.grabToImage(function(result) { result.saveToFile(Quickshell.env("GALLERY_OUTPUT")); console.log("Gallery saved"); Qt.quit() }) }
  }
}
