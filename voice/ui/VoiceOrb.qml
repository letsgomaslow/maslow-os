pragma ComponentBehavior: Bound
import QtQuick
import "OrbFrame.js" as OrbFrame

Item {
  id: root
  property real audioLevel: 0
  property real playbackLevel: 0
  property bool microphoneActive: false
  property int interruptionSequence: 0
  property int completionSequence: 0
  property string voiceState: "idle"
  property bool reducedMotion: false
  property bool disabled: false
  property bool interactive: false
  property bool gpuShaderAvailable: true
  property color accentColor: "#2875E5"
  property color backgroundColor: "#121D35"
  readonly property color topColor: Qt.tint(accentColor, Qt.rgba(1, 1, 1, 0.45))
  readonly property color bottomColor: Qt.tint(accentColor, Qt.rgba(0, 0, 0, 0.35))
  readonly property color eyeColor: contrastInk(Qt.tint(accentColor, Qt.rgba(1, 1, 1, 0.16)))
  readonly property color pupilColor: contrastInk(eyeColor)
  readonly property color focusColor: contrastInk(backgroundColor)
  property real phase: 0
  property string reaction: ""
  property real reactionTime: 0
  readonly property int stateMode: voiceState === "error" ? 6 : disabled ? 7 : ["paused", "muted"].indexOf(voiceState) >= 0 ? 5 : voiceState === "connecting" ? 1 : ["thinking", "working"].indexOf(voiceState) >= 0 ? 3 : ["speaking", "talking"].indexOf(voiceState) >= 0 ? 4 : ["listening", "conversation"].indexOf(voiceState) >= 0 ? 2 : 0
  // A persistent error plays its fall once, then holds the fallen pose.
  readonly property bool moving: visible && !reducedMotion && (stateMode < 5 || (stateMode === 6 && moodTime < failedHold))
  readonly property real normalizedLevel: isFinite(Number(audioLevel)) ? Math.max(0, Math.min(1, Number(audioLevel))) : 0
  readonly property real normalizedPlayback: isFinite(Number(playbackLevel)) ? Math.max(0, Math.min(1, Number(playbackLevel))) : 0
  // Playback is measured at the speaker, never inferred from the network or microphone.
  readonly property real responseLevel: reducedMotion || reaction === "interrupted" ? 0 : stateMode === 2 ? normalizedLevel : stateMode === 4 ? normalizedPlayback : 0
  readonly property real energy: Math.min(1, responseLevel * 4)
  readonly property real stretch: reducedMotion ? 1 : stateMode === 3 ? 0.94 + Math.sin(phase * 0.8) * 0.025 : 1 + energy * 0.09
  readonly property real squash: reducedMotion ? 1 : stateMode === 3 ? 0.96 + Math.cos(phase * 0.8) * 0.012 : 1 - energy * 0.07
  // Eye choreography comes from OrbFrame.js; completion plays "done" once.
  readonly property string mood: reaction === "completed" ? "done" : stateMode === 6 ? "failed" : stateMode === 7 ? "inactive" : stateMode === 5 ? "resting" : stateMode === 3 ? (voiceState === "working" ? "working" : "thinking") : stateMode === 1 ? "observing" : "idle"
  readonly property real failedHold: OrbFrame.FAILED_HOLD * OrbFrame.MOODS.failed.cycle
  readonly property real doneLength: OrbFrame.DONE_END * OrbFrame.MOODS.done.cycle
  property real moodStart: 0
  readonly property real moodTime: Math.max(0, phase - moodStart)
  // Mood changes ease from the previous mood's frame on their own clock, so
  // static states such as paused still complete the transition. The face
  // reads shownMood, which only the change handler sets, to avoid a loop.
  property string shownMood: "idle"
  property var blendFrom: null
  property real blendTime: 1
  readonly property var face: {
    if (reducedMotion) return OrbFrame.stillFrame(shownMood)
    return OrbFrame.blend(blendFrom, OrbFrame.frameAt(shownMood, shownMood === "done" ? reactionTime : moodTime), blendTime / 0.3)
  }
  Component.onCompleted: shownMood = mood
  readonly property real openness: reducedMotion || reaction !== "interrupted" ? 1 : OrbFrame.interruptOpenness(reactionTime)
  onMoodChanged: {
    blendFrom = OrbFrame.frameAt(shownMood, shownMood === "done" ? reactionTime : moodTime)
    shownMood = mood
    moodStart = phase
    blendTime = 0
  }
  property bool shaderFailed: false
  readonly property bool shaderReady: gpuOrb.active && !shaderFailed
  onShaderReadyChanged: fluidFallback.requestPaint()
  implicitWidth: ["conversation", "paused"].indexOf(voiceState) >= 0 ? 88 : 56
  implicitHeight: implicitWidth
  clip: true

  function contrastInk(color) {
    function linear(channel) { return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4) }
    var luminance = 0.2126 * linear(color.r) + 0.7152 * linear(color.g) + 0.0722 * linear(color.b)
    return luminance > 0.179 ? "#000000" : "#FFFFFF"
  }

  function react(kind) {
    // Reset the clock first so a new "done" never starts from an old time.
    reactionTime = 0
    reaction = kind
    reactionTimer.restart()
  }
  onInterruptionSequenceChanged: if (interruptionSequence > 0) react("interrupted")
  onCompletionSequenceChanged: if (completionSequence > 0) react("completed")
  Timer {
    interval: 40
    running: root.moving
    repeat: true
    onTriggered: root.phase += 0.04
  }
  Timer {
    interval: 40
    running: root.visible && !root.reducedMotion && root.blendTime < 0.3
    repeat: true
    onTriggered: root.blendTime += 0.04
  }
  Timer {
    id: reactionTimer
    interval: 40
    repeat: true
    onTriggered: {
      root.reactionTime += 0.04
      if (root.reactionTime >= (root.reaction === "completed" ? root.doneLength : 0.4)) { root.reaction = ""; stop() }
    }
  }

  Item {
    id: body
    width: parent.width
    height: parent.height
    opacity: root.stateMode === 7 ? 0.55 : 1
    transform: Scale { origin.x: body.width / 2; origin.y: body.height / 2; xScale: root.stretch; yScale: root.squash }
    Canvas {
      id: fluidFallback
      anchors.fill: parent
      // Use the same body when the shader is unavailable or fails to compile.
      visible: !root.shaderReady
      onWidthChanged: requestPaint()
      onHeightChanged: requestPaint()
      Component.onCompleted: requestPaint()
      Connections {
        target: root
        function onPhaseChanged() { if (!root.shaderReady) fluidFallback.requestPaint() }
        function onResponseLevelChanged() { if (!root.shaderReady) fluidFallback.requestPaint() }
        function onStateModeChanged() { fluidFallback.requestPaint() }
        function onTopColorChanged() { fluidFallback.requestPaint() }
        function onBottomColorChanged() { fluidFallback.requestPaint() }
        function onReducedMotionChanged() { fluidFallback.requestPaint() }
      }
      onPaint: {
        const ctx = getContext("2d")
        ctx.reset()
        ctx.clearRect(0, 0, width, height)
        ctx.save()
        ctx.translate(width / 2, height / 2)
        ctx.scale(width / 2, height / 2)
        const time = root.reducedMotion ? 0 : root.phase
        ctx.beginPath()
        for (let index = 0; index <= 96; index++) {
          const angle = index / 96 * Math.PI * 2
          const radius = 0.79 + Math.sin(angle * 3 + time * 1.4) * 0.035 + Math.cos(angle * 2 - time) * 0.025
          const x = Math.cos(angle) * radius
          const y = Math.sin(angle) * radius
          if (index === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.closePath()
        const fill = ctx.createLinearGradient(-0.5, -0.7, 0.4, 0.8)
        fill.addColorStop(0, String(root.topColor))
        fill.addColorStop(0.32, String(root.accentColor))
        fill.addColorStop(1, String(root.bottomColor))
        ctx.fillStyle = fill
        ctx.fill()
        ctx.clip()
        const light = ctx.createRadialGradient(-0.3, -0.4, 0, -0.3, -0.4, 0.4)
        light.addColorStop(0, "rgba(255,255,255,0.28)")
        light.addColorStop(1, "rgba(255,255,255,0)")
        ctx.fillStyle = light
        ctx.fillRect(-1, -1, 2, 2)
        ctx.restore()
      }
    }
    Loader {
      id: gpuOrb
      anchors.fill: parent
      active: root.gpuShaderAvailable && root.GraphicsInfo.api !== GraphicsInfo.Software
      onActiveChanged: fluidFallback.requestPaint()
      sourceComponent: Component {
        ShaderEffect {
          id: effect
          anchors.fill: parent
          property real phase: root.reducedMotion ? 0 : root.phase
          property color topColor: root.topColor
          property color accentColor: root.accentColor
          property color bottomColor: root.bottomColor
          fragmentShader: "VoiceOrb.frag.qsb"
          // Cached shader instances may remain Uncompiled despite rendering.
          // Fall back on an actual error, rather than waiting for Compiled.
          Component.onCompleted: root.shaderFailed = effect.status === ShaderEffect.Error
          onStatusChanged: root.shaderFailed = effect.status === ShaderEffect.Error
        }
      }
    }
    // Shared native geometry gives the character the same face on both renderers.
    Item {
      id: face
      readonly property real unit: width * 0.395 / OrbFrame.BODY_RADIUS
      function px(value) { return width / 2 + (value - OrbFrame.CENTER) * unit }
      width: body.width
      height: body.height
      x: root.face.offset[0] * unit
      y: root.face.offset[1] * unit
      rotation: root.face.tilt
      Repeater {
        model: 2
        Rectangle {
          id: eye
          required property int index
          readonly property var pose: root.face.eyes[index]
          readonly property real eyeHeight: pose.h * root.openness * face.unit
          x: face.px(pose.cx) - width / 2
          y: face.px(pose.cy) - height / 2
          width: pose.w * face.unit
          height: eyeHeight
          radius: Math.min(pose.r * face.unit, width / 2, height / 2)
          rotation: pose.rot * 180 / Math.PI
          opacity: pose.alpha
          color: root.eyeColor
          Rectangle {
            // Pupils show only on open, upright eyes, not on dots or slits.
            visible: eye.height > eye.width * 1.25 && eye.opacity > 0.5
            width: eye.width * 0.48
            height: width
            radius: width / 2
            x: (eye.width - width) / 2
            y: eye.height * 0.48
            color: root.pupilColor
          }
        }
      }
      Rectangle {
        // The mouth steps aside while the eyes travel through its space.
        opacity: ["thinking", "working", "failed"].indexOf(root.face.mood) >= 0 ? 0 : 1
        Behavior on opacity { enabled: !root.reducedMotion; NumberAnimation { duration: 150 } }
        width: body.width * 0.10
        height: root.stateMode === 4 ? body.height * (0.025 + root.energy * 0.06) : body.height * 0.025
        x: face.px(OrbFrame.CENTER) - width / 2
        y: face.px(OrbFrame.MOUTH_Y) - height / 2
        radius: height / 2
        color: root.eyeColor
      }
      Canvas {
        id: marks
        // Dizzy swirls and sleep marks; repaints only while either is shown.
        readonly property bool shown: root.face.swirls.length > 0 || root.face.sleep.length > 0
        property bool painted: false
        anchors.fill: parent
        onWidthChanged: requestPaint()
        Connections {
          target: root
          function onFaceChanged() { if (marks.shown || marks.painted) marks.requestPaint() }
          function onEyeColorChanged() { marks.requestPaint() }
        }
        onPaint: {
          const ctx = getContext("2d")
          ctx.reset()
          ctx.clearRect(0, 0, width, height)
          painted = shown
          ctx.strokeStyle = String(root.eyeColor)
          ctx.lineCap = "round"
          ctx.lineJoin = "round"
          for (const swirl of root.face.swirls) {
            const points = OrbFrame.swirlPoints(swirl)
            ctx.globalAlpha = swirl.alpha
            ctx.lineWidth = Math.max(1, face.unit * 1.1)
            ctx.beginPath()
            for (let index = 0; index < points.length; index++) {
              if (index === 0) ctx.moveTo(face.px(points[index][0]), face.px(points[index][1]))
              else ctx.lineTo(face.px(points[index][0]), face.px(points[index][1]))
            }
            ctx.stroke()
          }
          for (const mark of root.face.sleep) {
            const half = mark.size / 2
            ctx.globalAlpha = mark.alpha
            ctx.lineWidth = Math.max(1, mark.size * 0.22 * face.unit)
            ctx.beginPath()
            ctx.moveTo(face.px(mark.x - half), face.px(mark.y - half))
            ctx.lineTo(face.px(mark.x + half), face.px(mark.y - half))
            ctx.lineTo(face.px(mark.x - half), face.px(mark.y + half))
            ctx.lineTo(face.px(mark.x + half), face.px(mark.y + half))
            ctx.stroke()
          }
        }
      }
    }
  }
  // Status symbols remain static and independent of deformation.
  Text {
    anchors.horizontalCenter: parent.horizontalCenter
    y: parent.height * 0.77
    visible: root.stateMode === 5 || root.stateMode === 6 || root.reaction !== ""
    text: root.stateMode === 6 ? "!" : root.stateMode === 5 ? "Ⅱ" : root.reaction === "completed" ? "✓" : "·"
    color: root.eyeColor
    font.pixelSize: parent.width * 0.15
    font.bold: true
    Accessible.ignored: true
  }
  Rectangle {
    visible: root.microphoneActive
    x: parent.width * 0.77
    y: parent.height * 0.17
    width: Math.max(6, parent.width * 0.085)
    height: width
    radius: width / 2
    color: root.eyeColor
    border.color: root.pupilColor
    border.width: 1
    Accessible.ignored: true
  }
  Rectangle {
    anchors.fill: parent
    anchors.margins: 2
    radius: width / 2
    color: "transparent"
    border.width: root.interactive ? 2 : 0
    border.color: root.focusColor
  }
}
