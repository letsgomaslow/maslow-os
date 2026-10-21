import QtQuick
import "ScreensaverModel.js" as Model

// The Gradient Bridge screensaver picture for one screen. Pure presentation:
// every input arrives as a property and every visual is a function of
// elapsedMs, so the gallery fixture renders any instant directly and the
// service's single Timer is the only clock. No animation types, effects or
// layers here: aurora fields, halo, particles and ripples are pre-blurred
// PNGs that only move, scale and fade, and the mark is a vector raster.
Item {
  id: root

  property string omarchyPath: ""
  property real elapsedMs: 0
  property int screenIndex: 0
  property int screenCount: 1
  property bool reducedMotion: false
  property int repositionCycle: 0
  property string clockText: ""
  property string hintText: "PRESS ANY KEY"

  readonly property color navy: "#121D35"
  readonly property string assetDir: omarchyPath + "/shell/plugins/screensaver/assets"
  readonly property string assetUrl: omarchyPath ? "file://" + assetDir + "/" : ""

  // Mark geometry from assets/maslow-mark-gradient.svg, a copy of the brand
  // mark (viewBox -1 0 375 249: it starts one unit left so the restored left
  // circles are not clipped). viewLeft maps model coordinates into it. The visible paths span x -0.75..362, so the mark sits 5.9 units left
  // of its own box and is nudged back to look centred over the wordmark.
  readonly property real viewLeft: -1
  readonly property real markAspect: 375 / 249
  readonly property real opticalShift: 5.9 / 375

  readonly property real shortSide: Math.min(height, width / 1.6)
  readonly property int markHeight: Math.max(64, Math.round(shortSide * 0.30))
  readonly property int markWidth: Math.round(markHeight * markAspect)
  readonly property real unit: markWidth / 375
  // The raster is cut at the top of the breath so breathing only scales down.
  readonly property int rasterHeight: Math.round(markHeight * (1 + Model.BREATH_DEPTH))
  readonly property int rasterWidth: Math.round(rasterHeight * markAspect)
  readonly property int wordSize: Math.max(14, Math.round(markHeight * 0.115))
  readonly property int clockSize: Math.max(28, Math.round(shortSide * 0.085))
  readonly property int hintSize: Math.max(11, Math.round(shortSide * 0.016))

  readonly property real breath: Model.breathScale(elapsedMs, reducedMotion)
  readonly property var driftOffset: Model.drift(elapsedMs, width, height, reducedMotion, repositionCycle, screenIndex)

  readonly property bool markReady: mark.status === Image.Ready
  readonly property bool glowReady: halo.status === Image.Ready
  readonly property alias lockupItem: lockup
  readonly property alias clockItem: clock
  readonly property alias hintItem: hint

  Rectangle {
    anchors.fill: parent
    color: root.navy
  }

  // Aurora: brand light drifting across the whole screen.
  Repeater {
    model: Model.AURORA.length

    Image {
      required property int index
      readonly property var field: Model.auroraField(index, root.elapsedMs, root.width, root.height, root.screenIndex, root.reducedMotion)
      source: root.assetUrl ? root.assetUrl + "aurora-" + field.key + ".png" : ""
      width: Math.round(field.size)
      height: width
      x: Math.round(field.x - width / 2)
      y: Math.round(field.y - height / 2)
      opacity: field.opacity
      sourceSize.width: 512
      sourceSize.height: 512
      smooth: true
      cache: true
    }
  }

  // Mark, wordmark and clock share one vertical axis and drift together.
  Item {
    id: composition
    width: root.width
    height: root.height
    x: root.driftOffset.x
    y: root.driftOffset.y

    Item {
      id: lockup
      width: Math.max(root.markWidth, wordmark.width)
      height: root.markHeight + wordmark.anchors.topMargin + wordmark.height
      x: Math.round((root.width - width) / 2)
      y: Math.round(root.height * 0.44 - root.markHeight / 2)

      Image {
        id: halo
        source: root.assetUrl ? root.assetUrl + "glow.png" : ""
        width: Math.round(root.markWidth * 2.1)
        height: Math.round(root.markHeight * 2.6)
        x: Math.round((lockup.width - width) / 2)
        y: Math.round((root.markHeight - height) / 2)
        opacity: Model.haloOpacity(root.elapsedMs, root.reducedMotion)
        sourceSize.width: 1024
        sourceSize.height: 512
        smooth: true
        cache: true
      }

      Item {
        id: markBox
        width: root.markWidth
        height: root.markHeight
        x: Math.round((lockup.width - width) / 2 + root.markWidth * root.opticalShift)
        scale: root.breath / (1 + Model.BREATH_DEPTH / 2)

        // Ripples leave the two standalone circles in turn.
        Repeater {
          model: 2

          Image {
            required property int index
            readonly property var wave: Model.ripple(index, root.elapsedMs, root.reducedMotion)
            source: root.assetUrl ? root.assetUrl + "ring.png" : ""
            visible: wave.opacity > 0.01
            width: Math.round(wave.radius * root.unit * 2 / 0.9)
            height: width
            x: Math.round((wave.x - root.viewLeft) * root.unit - width / 2)
            y: Math.round(wave.y * root.unit - height / 2)
            opacity: wave.opacity
            sourceSize.width: 512
            sourceSize.height: 512
            smooth: true
            cache: true
          }
        }

        Image {
          id: mark
          source: root.assetUrl ? root.assetUrl + "maslow-mark-gradient.svg" : ""
          anchors.centerIn: parent
          width: root.rasterWidth
          height: root.rasterHeight
          sourceSize.width: root.rasterWidth
          sourceSize.height: root.rasterHeight
          fillMode: Image.PreserveAspectFit
          scale: 1 / (1 + Model.BREATH_DEPTH)
          smooth: true
          cache: true
        }

        // Light crossing each bridge from its lower circle to its upper one.
        Repeater {
          model: Model.PARTICLES_PER_BRIDGE * 2

          Image {
            required property int index
            readonly property var spark: Model.particle(index % Model.PARTICLES_PER_BRIDGE, Math.floor(index / Model.PARTICLES_PER_BRIDGE), root.elapsedMs, root.reducedMotion)
            source: root.assetUrl ? root.assetUrl + "particle.png" : ""
            visible: spark.opacity > 0.01
            width: Math.round(root.markHeight * 0.36 * spark.scale)
            height: width
            x: Math.round((spark.x - root.viewLeft) * root.unit - width / 2)
            y: Math.round(spark.y * root.unit - height / 2)
            opacity: spark.opacity
            sourceSize.width: 128
            sourceSize.height: 128
            smooth: true
            cache: true
          }
        }
      }

      Row {
        id: wordmark
        anchors.top: markBox.bottom
        anchors.topMargin: Math.round(root.markHeight * 0.22)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Math.round(root.wordSize * 0.62)

        Text {
          id: wordMaslow
          text: "MASLOW"
          textFormat: Text.PlainText
          color: Qt.rgba(1, 1, 1, 0.92)
          font.family: "Manrope"
          font.weight: Font.DemiBold
          font.pixelSize: root.wordSize
          font.letterSpacing: root.wordSize * 0.2
        }

        Rectangle {
          width: Math.max(1, Math.round(root.wordSize * 0.08))
          height: Math.round(root.wordSize * 0.95)
          anchors.verticalCenter: wordMaslow.verticalCenter
          color: Qt.rgba(1, 1, 1, 0.45)
        }

        Text {
          text: "AI-OS"
          textFormat: Text.PlainText
          color: Qt.rgba(1, 1, 1, 0.62)
          font.family: "Manrope"
          font.weight: Font.Medium
          font.pixelSize: root.wordSize
          font.letterSpacing: root.wordSize * 0.1
        }
      }
    }

    Text {
      id: clock
      anchors.horizontalCenter: lockup.horizontalCenter
      y: Math.round(root.height * 0.80 - height / 2)
      visible: text.length > 0
      text: root.clockText
      textFormat: Text.PlainText
      color: Qt.rgba(1, 1, 1, 0.82)
      font.family: "Manrope"
      font.weight: Font.ExtraLight
      font.pixelSize: root.clockSize
      font.letterSpacing: root.clockSize * 0.04
    }

    Text {
      id: hint
      anchors.horizontalCenter: lockup.horizontalCenter
      anchors.top: clock.bottom
      anchors.topMargin: Math.round(root.hintSize * 1.2)
      text: root.hintText
      textFormat: Text.PlainText
      color: Qt.rgba(1, 1, 1, 0.38)
      font.family: "Manrope"
      font.weight: Font.Medium
      font.pixelSize: root.hintSize
      font.letterSpacing: root.hintSize * 0.35
    }
  }
}
