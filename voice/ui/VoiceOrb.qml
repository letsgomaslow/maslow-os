import QtQuick

Item {
  id: root
  property real audioLevel: 0
  property string voiceState: "idle"
  property bool reducedMotion: false
  property bool disabled: false
  property bool interactive: false
  property bool gpuShaderAvailable: true
  property real phase: 0
  readonly property bool moving: !reducedMotion && !interactive && !disabled && ["connecting", "thinking", "listening", "speaking", "talking", "working", "conversation"].indexOf(voiceState) >= 0
  readonly property real normalizedLevel: Math.max(0, Math.min(1, Number(audioLevel || 0)))
  implicitWidth: voiceState === "conversation" ? 88 : 56
  implicitHeight: implicitWidth

  Timer { interval: 40; running: root.moving; repeat: true; onTriggered: root.phase += 0.04 + root.normalizedLevel * 0.06 }
  Rectangle {
    anchors.fill: parent
    radius: width / 2
    gradient: Gradient {
      GradientStop { position: 0; color: root.disabled ? "#D1D5DB" : "#9DDDCB" }
      GradientStop { position: 0.42 + Math.sin(root.phase) * 0.1; color: root.disabled ? "#8D95A3" : "#6DC4AD" }
      GradientStop { position: 0.74; color: root.disabled ? "#6B7280" : "#A070A6" }
      GradientStop { position: 1; color: root.disabled ? "#454D5B" : "#401877" }
    }
  }
  Rectangle {
    visible: root.disabled
    width: parent.width * 0.44
    height: parent.height * 0.17
    x: parent.width * 0.18
    y: parent.height * 0.14
    radius: height / 2
    color: "#FFFFFF"
    opacity: 0.11
  }
  Loader {
    id: gpuOrb
    anchors.fill: parent
    active: root.gpuShaderAvailable && root.GraphicsInfo.api !== GraphicsInfo.Software
    sourceComponent: Component {
      ShaderEffect {
        anchors.fill: parent
        property real level: root.normalizedLevel
        property real phase: root.phase
        property real disabled: root.disabled ? 1 : 0
        fragmentShader: "VoiceOrb.frag.qsb"
      }
    }
  }
  Rectangle {
    anchors.fill: parent; anchors.margins: -3
    radius: width / 2; color: "transparent"
    border.width: root.interactive ? 2 : 0; border.color: "#FFFFFF"
  }
}
