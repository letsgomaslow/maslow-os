pragma ComponentBehavior: Bound
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
  // Keep state and audio independent: a silent microphone still looks like listening.
  readonly property int stateMode: voiceState === "error" ? 6 : disabled ? 7 : voiceState === "muted" ? 5 : voiceState === "connecting" ? 1 : ["thinking", "working"].indexOf(voiceState) >= 0 ? 3 : ["speaking", "talking"].indexOf(voiceState) >= 0 ? 4 : ["listening", "conversation"].indexOf(voiceState) >= 0 ? 2 : 0
  readonly property bool moving: visible && !reducedMotion && stateMode < 5
  readonly property real normalizedLevel: isFinite(Number(audioLevel)) ? Math.max(0, Math.min(1, Number(audioLevel))) : 0
  // The service currently publishes microphone amplitude only. Speaking uses
  // a gentle state-driven cadence until playback amplitude is available.
  readonly property real responseLevel: reducedMotion ? 0 : stateMode === 2 ? normalizedLevel : stateMode === 4 ? 0.4 + Math.sin(phase * 5) * 0.22 + Math.sin(phase * 9) * 0.08 : 0
  readonly property real motionSpeed: stateMode === 0 ? 0.22 : stateMode === 1 ? 0.8 : stateMode === 3 ? 1.15 : stateMode === 4 ? 0.9 : 0.45
  implicitWidth: voiceState === "conversation" ? 88 : 56
  implicitHeight: implicitWidth

  Timer {
    interval: 40
    running: root.moving
    repeat: true
    onTriggered: root.phase += 0.04 * root.motionSpeed
  }

  // This blue/white base remains visible if a graphics pipeline cannot load.
  Rectangle {
    anchors.fill: parent
    radius: width / 2
    gradient: Gradient {
      GradientStop { position: 0; color: "#EFF8FF" }
      GradientStop { position: 0.32; color: "#93C9FF" }
      GradientStop { position: 0.7; color: "#2875E5" }
      GradientStop { position: 1; color: "#154BA8" }
    }
  }

  // Canvas also works with Qt's software renderer; a few soft cloud lobes keep
  // the same visual identity without a GPU or an external texture asset.
  Canvas {
    id: cloudFallback
    anchors.fill: parent
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
    Connections {
      target: root
      function onPhaseChanged() { if (!gpuOrb.active) cloudFallback.requestPaint() }
      function onResponseLevelChanged() { if (!gpuOrb.active) cloudFallback.requestPaint() }
      function onStateModeChanged() { cloudFallback.requestPaint() }
    }
    onPaint: {
      const ctx = getContext("2d")
      ctx.reset()
      ctx.clearRect(0, 0, width, height)
      ctx.save()
      ctx.beginPath()
      ctx.arc(width / 2, height / 2, Math.min(width, height) / 2, 0, Math.PI * 2)
      ctx.clip()
      const travel = root.phase
      for (let i = 0; i < 7; i++) {
        const angle = i * 2.4 + travel * 0.35
        const x = width * (0.45 + Math.sin(angle) * 0.29)
        const y = height * (0.41 + Math.cos(angle * 0.8) * 0.26)
        const radius = width * (0.25 + Math.sin(i + travel * 0.7) * 0.045 + root.responseLevel * 0.065)
        const cloud = ctx.createRadialGradient(x, y, 0, x, y, radius)
        cloud.addColorStop(0, "rgba(255,255,255,0.88)")
        cloud.addColorStop(0.46, "rgba(239,248,255,0.58)")
        cloud.addColorStop(1, "rgba(239,248,255,0)")
        ctx.fillStyle = cloud
        ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2)
      }
      ctx.restore()
    }
  }

  Loader {
    id: gpuOrb
    anchors.fill: parent
    active: root.gpuShaderAvailable && root.GraphicsInfo.api !== GraphicsInfo.Software
    onActiveChanged: cloudFallback.requestPaint()
    sourceComponent: Component {
      ShaderEffect {
        anchors.fill: parent
        property real level: root.responseLevel
        property real phase: root.phase
        property real stateMode: root.stateMode
        fragmentShader: "VoiceOrb.frag.qsb"
      }
    }
  }

  // Distinct state cues survive reduced motion and software rendering.
  Rectangle {
    anchors.fill: parent
    radius: width / 2
    color: root.stateMode >= 5 ? "#5C9DE7" : "transparent"
    opacity: root.stateMode >= 5 ? 0.22 : 1
    border.width: 1
    border.color: "#80D8EDFF"
  }
  Rectangle {
    visible: root.stateMode === 1 || root.stateMode === 3
    width: parent.width * 0.09
    height: width
    radius: width / 2
    color: "#FFFFFF"
    x: parent.width * (0.5 + Math.sin(root.phase * 1.8) * 0.41) - width / 2
    y: parent.height * (0.5 - Math.cos(root.phase * 1.8) * 0.41) - height / 2
  }
  Rectangle {
    visible: root.stateMode === 2 || root.stateMode === 4
    anchors.fill: parent
    anchors.margins: parent.width * (0.045 + (1 - root.responseLevel) * 0.025)
    radius: width / 2
    color: "transparent"
    border.width: root.stateMode === 4 ? 2 : 1
    border.color: root.stateMode === 4 ? "#CCFFFFFF" : "#99FFFFFF"
  }
  Text {
    anchors.centerIn: parent
    visible: root.stateMode === 5 || root.stateMode === 6
    text: root.stateMode === 6 ? "!" : "Ⅱ"
    color: root.stateMode === 6 ? "#7C341A" : "#17467E"
    font.pixelSize: parent.width * 0.33
    font.bold: true
  }
  Rectangle {
    anchors.fill: parent
    anchors.margins: -3
    radius: width / 2
    color: "transparent"
    border.width: root.interactive ? 2 : 0
    border.color: "#FFFFFF"
  }
}
