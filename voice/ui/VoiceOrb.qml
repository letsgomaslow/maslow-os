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

  // This deep blue base remains visible if a graphics pipeline cannot load.
  Rectangle {
    anchors.fill: parent
    radius: width / 2
    gradient: Gradient {
      GradientStop { position: 0; color: "#2875E5" }
      GradientStop { position: 0.45; color: "#154BA8" }
      GradientStop { position: 1; color: "#154BA8" }
    }
  }

  // Software rendering uses three broad curved sheets and glass reflections.
  // Keep it beneath the shader so a failed graphics pipeline is still visible.
  Canvas {
    id: glassFallback
    anchors.fill: parent
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
    Connections {
      target: root
      function onPhaseChanged() { if (!gpuOrb.active) glassFallback.requestPaint() }
      function onResponseLevelChanged() { if (!gpuOrb.active) glassFallback.requestPaint() }
      function onStateModeChanged() { glassFallback.requestPaint() }
    }
    onPaint: {
      const ctx = getContext("2d")
      ctx.reset()
      ctx.clearRect(0, 0, width, height)
      ctx.save()
      ctx.translate(width / 2, height / 2)
      ctx.scale(width / 2, height / 2)
      ctx.beginPath()
      ctx.arc(0, 0, 0.985, 0, Math.PI * 2)
      ctx.clip()
      const body = ctx.createRadialGradient(-0.3, -0.4, 0.05, 0, 0, 1)
      body.addColorStop(0, "#2875E5")
      body.addColorStop(0.68, "#154BA8")
      body.addColorStop(1, "#154BA8")
      ctx.fillStyle = body
      ctx.fillRect(-1, -1, 2, 2)
      const travel = root.phase * (root.stateMode === 3 ? 0.52 : 0.31)
      for (let i = 0; i < 3; i++) {
        ctx.save()
        ctx.rotate(i * 1.9 + travel * (i === 1 ? -0.62 : 0.77))
        ctx.translate((i - 1) * 0.09, Math.sin(travel + i * 2.1) * 0.07)
        ctx.scale(1, 0.8 + Math.sin(travel + i) * 0.12 + root.responseLevel * 0.12)
        const sheet = ctx.createLinearGradient(-0.6, -0.55, 0.4, 0.5)
        sheet.addColorStop(0, i === 0 ? "rgba(115,193,174,0.12)" : i === 2 ? "rgba(101,76,143,0.10)" : "rgba(147,201,255,0.12)")
        sheet.addColorStop(0.43, i === 0 ? "rgba(115,193,174,0.54)" : i === 2 ? "rgba(101,76,143,0.38)" : "rgba(147,201,255,0.65)")
        sheet.addColorStop(0.5, "rgba(239,248,255,0.75)")
        sheet.addColorStop(0.59, "rgba(40,117,229,0.48)")
        sheet.addColorStop(1, "rgba(21,75,168,0.08)")
        ctx.fillStyle = sheet
        ctx.beginPath()
        ctx.moveTo(-1.15, -0.2)
        ctx.bezierCurveTo(-0.5, -1, 0.45, 0.85, 1.15, -0.45)
        ctx.bezierCurveTo(0.72, 1.05, -0.42, -0.08, -1.15, 0.35)
        ctx.closePath()
        ctx.fill()
        ctx.restore()
      }
      // Broad asymmetric reflection stays anchored while the interior turns.
      const rim = ctx.createLinearGradient(-0.8, -0.9, 0.7, 0.9)
      rim.addColorStop(0, "rgba(239,248,255,0.85)")
      rim.addColorStop(0.4, "rgba(147,201,255,0.12)")
      rim.addColorStop(0.7, "rgba(147,201,255,0)")
      rim.addColorStop(1, "rgba(147,201,255,0.52)")
      ctx.strokeStyle = rim
      ctx.lineWidth = 0.045
      ctx.beginPath()
      ctx.arc(0, 0, 0.96, 0, Math.PI * 2)
      ctx.stroke()
      if (root.stateMode === 1) {
        ctx.save()
        ctx.rotate(root.phase * 1.8)
        const connection = ctx.createLinearGradient(0.55, -0.65, 1, 0.1)
        connection.addColorStop(0, "rgba(239,248,255,0)")
        connection.addColorStop(0.5, "rgba(239,248,255,0.6)")
        connection.addColorStop(1, "rgba(239,248,255,0)")
        ctx.strokeStyle = connection
        ctx.lineWidth = 0.065
        ctx.beginPath()
        ctx.arc(0, 0, 0.95, -0.9, 0.15)
        ctx.stroke()
        ctx.restore()
      }
      ctx.save()
      ctx.translate(-0.34, -0.56)
      ctx.scale(0.38, 0.12)
      const reflection = ctx.createRadialGradient(0, 0, 0, 0, 0, 1)
      reflection.addColorStop(0, "rgba(239,248,255,0.9)")
      reflection.addColorStop(1, "rgba(239,248,255,0)")
      ctx.fillStyle = reflection
      ctx.fillRect(-1, -1, 2, 2)
      ctx.restore()
      ctx.restore()
    }
  }

  Loader {
    id: gpuOrb
    anchors.fill: parent
    active: root.gpuShaderAvailable && root.GraphicsInfo.api !== GraphicsInfo.Software
    onActiveChanged: glassFallback.requestPaint()
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

  // Muted/error/disabled states keep their calm tint and explicit glyphs.
  Rectangle {
    visible: root.stateMode >= 5
    anchors.fill: parent
    radius: width / 2
    color: "#93C9FF"
    opacity: 0.32
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
