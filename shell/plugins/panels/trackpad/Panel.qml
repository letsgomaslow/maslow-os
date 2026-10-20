import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

Panel {
  id: root
  moduleName: "omarchy.trackpad"
  ipcTarget: "omarchy.trackpad"

  property var status: ({ present: false })
  property string view: "settings"
  property int cursorIndex: -1

  readonly property bool present: status.present === true
  readonly property var rows: Model.settingRows(status)
  readonly property var guide: Model.guideRows(status)
  readonly property color foreground: root.bar ? root.bar.foreground : Color.foreground
  readonly property string fontFamily: root.bar ? root.bar.fontFamily : Style.font.family

  // Cursor stops, top to bottom: hero switch (0), view chooser (1), then the
  // settings rows and the speed slider when the settings view is showing.
  readonly property int speedIndex: 2 + rows.length
  readonly property int cursorCount: view === "settings" ? speedIndex + 1 : 2

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function run(args) {
    if (actionProc.running) return
    actionProc.command = ["omarchy-trackpad-set"].concat(args)
    actionProc.running = true
  }

  // Flip the switch before the command returns so the knob moves at once; the
  // refresh after the command settles the real value.
  function toggleRow(row) {
    var next = Object.assign({}, root.status)
    if (row.command === "tap-to-click") next.tap_to_click = !row.checked
    else if (row.command === "two-finger-right-click") next.clickfinger_behavior = !row.checked
    else if (row.command === "natural-scroll") next.natural_scroll = !row.checked
    else if (row.command === "workspace-swipe") next.workspace_swipe = !row.checked
    else if (row.command === "three-finger-drag") next.drag_3fg = !row.checked
    else if (row.command === "ignore-while-typing") next.disable_while_typing = !row.checked
    root.status = next
    run([row.command, row.checked ? "off" : "on"])
  }

  function toggleEnabled() {
    if (enableProc.running) return
    root.status = Object.assign({}, root.status, { enabled: !root.status.enabled })
    enableProc.command = ["omarchy-toggle-touchpad", root.status.enabled ? "on" : "off"]
    enableProc.running = true
  }

  function setSpeed(value) {
    var speed = Math.round(value * 20) / 20
    root.status = Object.assign({}, root.status, { speed: speed })
    run(["speed", speed.toFixed(2)])
  }

  function activate(index) {
    if (index === 0) toggleEnabled()
    else if (index === 1) view = view === "settings" ? "guide" : "settings"
    else if (view === "settings" && index >= 2 && index < speedIndex) toggleRow(rows[index - 2])
  }

  function move(dx, dy) {
    if (cursorIndex < 0) { cursorIndex = 0; return }
    if (dy !== 0) {
      cursorIndex = Math.max(0, Math.min(cursorCount - 1, cursorIndex + dy))
    } else if (cursorIndex === 1) {
      view = dx > 0 ? "guide" : "settings"
    } else if (cursorIndex === speedIndex) {
      setSpeed(Math.max(-1, Math.min(1, status.speed + dx * 0.1)))
    }
  }

  onOpenedChanged: {
    if (opened) {
      if (!present) {
        close()
        return
      }
      refresh()
      cursorIndex = -1
    }
  }

  onCursorCountChanged: if (cursorIndex >= cursorCount) cursorIndex = cursorCount - 1
  onPresentChanged: if (!present) close()
  Component.onCompleted: refresh()

  visible: present
  implicitWidth: present ? button.implicitWidth : 0
  implicitHeight: present ? button.implicitHeight : 0

  Process {
    id: statusProc
    command: ["omarchy-trackpad-status"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.status = Model.parseStatus(text) }
  }

  Process {
    id: actionProc
    onExited: root.refresh()
  }

  Process {
    id: enableProc
    onExited: root.refresh()
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: Model.ICON
    opacity: root.status.enabled ? 1.0 : 0.5
    tooltipText: ""
    Accessible.role: Accessible.Button
    Accessible.name: root.status.enabled ? "Trackpad settings" : "Trackpad settings, trackpad is off"
    onPressed: function(b) { if (root.present) root.toggle() }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened && root.present
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(400))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onMoveRequested: function(dx, dy) { root.move(dx, dy) }
      onActivateRequested: if (root.cursorIndex >= 0) root.activate(root.cursorIndex)
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(14)

        PanelHero {
          width: parent.width
          title: "Trackpad"
          meta: root.status.enabled ? "On" : "Off"
          foreground: root.foreground
          fontFamily: root.fontFamily
          iconOpacity: root.status.enabled ? 1.0 : 0.5
          iconComponent: Component {
            Text {
              textFormat: Text.PlainText
              text: Model.ICON
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.display
            }
          }
          trailingControl: Component {
            ToggleSwitch {
              checked: root.status.enabled === true
              hasCursor: root.cursorIndex === 0
              foreground: root.foreground
              onToggled: root.toggleEnabled()
              onHovered: function(h) { if (h) root.cursorIndex = 0 }
              Accessible.role: Accessible.CheckBox
              Accessible.name: "Trackpad"
              Accessible.checkable: true
              Accessible.checked: checked
              Accessible.onToggleAction: root.toggleEnabled()
              Accessible.onPressAction: root.toggleEnabled()
            }
          }
        }

        // With the trackpad off, the panel itself may be out of reach, so say
        // how to get it back from the keyboard.
        Text {
          visible: root.status.enabled === false
          width: parent.width
          textFormat: Text.PlainText
          text: "The trackpad is off. To turn it back on without a mouse, press Super + Ctrl + H, then choose Touchpad."
          color: root.foreground
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
          Accessible.role: Accessible.StaticText
          Accessible.name: text
        }

        ButtonGroup {
          options: [
            { value: "settings", label: "Settings" },
            { value: "guide", label: "How to use" }
          ]
          value: root.view
          foreground: root.foreground
          fontFamily: root.fontFamily
          fontSize: Style.font.bodySmall
          focusable: false
          cursorIndex: root.cursorIndex === 1 ? (root.view === "settings" ? 0 : 1) : -1
          onChanged: function(value) { root.view = value }
          onHovered: function(index, isHovered) { if (isHovered) root.cursorIndex = 1 }
          Accessible.role: Accessible.PageTabList
          Accessible.name: root.view === "settings" ? "Trackpad view: Settings" : "Trackpad view: How to use"
        }

        // ---------- Settings ----------
        Column {
          visible: root.view === "settings"
          width: parent.width
          spacing: Style.space(8)

          Repeater {
            model: root.rows
            Toggle {
              required property var modelData
              required property int index
              width: parent.width
              label: modelData.label
              description: modelData.description
              checked: modelData.checked
              foreground: root.foreground
              fontFamily: root.fontFamily
              titleSize: Style.font.body
              hasCursor: root.cursorIndex === index + 2
              onHovered: function(h) { if (h) root.cursorIndex = index + 2 }
              onClicked: {
                root.cursorIndex = index + 2
                root.toggleRow(modelData)
              }
              Accessible.role: Accessible.CheckBox
              Accessible.name: modelData.label
              Accessible.description: modelData.description
              Accessible.checkable: true
              Accessible.checked: modelData.checked
              Accessible.onToggleAction: root.toggleRow(modelData)
              Accessible.onPressAction: root.toggleRow(modelData)
            }
          }

          Item { width: 1; height: Style.space(4) }

          Item {
            width: parent.width
            implicitHeight: speedLabel.implicitHeight

            PanelSectionHeader {
              id: speedLabel
              anchors.left: parent.left
              text: "POINTER SPEED"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            Text {
              anchors.right: parent.right
              anchors.verticalCenter: speedLabel.verticalCenter
              textFormat: Text.PlainText
              text: Model.speedLabel(root.status.speed)
              color: root.foreground
              opacity: 0.85
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
            }
          }

          PanelSlider {
            width: parent.width
            bar: root.bar
            minimum: -1
            maximum: 1
            step: 0.05
            tickCount: 3
            value: root.status.speed || 0
            onReleased: function(v) { root.setSpeed(v) }
            Accessible.role: Accessible.Slider
            Accessible.name: "Pointer speed"
            Accessible.description: Model.speedLabel(root.status.speed) + ". Use the left and right arrow keys to adjust."

            HoverHandler {
              onHoveredChanged: if (hovered) root.cursorIndex = root.speedIndex
            }

            Rectangle {
              anchors.fill: parent
              anchors.margins: -Style.space(4)
              visible: root.cursorIndex === root.speedIndex
              color: "transparent"
              radius: Style.cornerRadius
              border.width: 1
              border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.25)
            }
          }
        }

        // ---------- How to use ----------
        Column {
          visible: root.view === "guide"
          width: parent.width
          spacing: Style.space(10)

          Repeater {
            model: root.guide
            Item {
              required property var modelData
              width: parent.width
              implicitHeight: Math.max(badge.height, gestureText.implicitHeight)
              Accessible.role: Accessible.StaticText
              Accessible.name: modelData.fingers + (modelData.fingers === "1" ? " finger, " : " fingers, ") + modelData.gesture + ": " + modelData.action

              Rectangle {
                id: badge
                width: Style.space(26)
                height: Style.space(26)
                radius: Style.cornerRadius > 0 ? height / 2 : 0
                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.12)
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                Text {
                  anchors.centerIn: parent
                  textFormat: Text.PlainText
                  text: modelData.fingers
                  color: root.foreground
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  font.bold: true
                }
              }

              Text {
                id: gestureText
                anchors.left: badge.right
                anchors.leftMargin: Style.space(10)
                anchors.right: actionText.left
                anchors.rightMargin: Style.space(10)
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.PlainText
                text: modelData.gesture
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.bodySmall
                wrapMode: Text.WordWrap
              }

              Text {
                id: actionText
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.PlainText
                text: modelData.action
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.bodySmall
                font.bold: true
              }
            }
          }

          Text {
            width: parent.width
            textFormat: Text.PlainText
            text: "The number is how many fingers to use. Change these in Settings, with the mouse or with the arrow keys and Enter."
            color: root.foreground
            opacity: 0.85
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.WordWrap
          }
        }
      }
    }
  }
}
