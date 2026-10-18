import QtQuick
import Quickshell
import "services/AuthServiceStore.js" as AuthServiceStore

ShellRoot {
  id: shell
  property var _services: ({})
  property var _backgroundServiceLoad: null
  property int _backgroundServiceGeneration: 0
  property bool pluginReloading: false
  property string omarchyPath: "/fixture"
  property var pluginRegistry: registry
  property bool cancelDuringInjection: false
  property int created: 0
  property int destroyed: 0
  property int observedTicks: 0
  property int heartbeats: 0
  property int loadSerial: 0
  property int phase: 0
  property int waits: 0
  property var originalClaim: null
  property var keptAuth: null
  Item { id: serviceHost; property var host: shell }
  QtObject {
    id: registry
    property var installedPlugins: ({})
    property bool enabled: true
    function isEnabled(id) { return enabled }
    function entryPointUrl(manifest, kind) { return manifest.url || "" }
  }
  function pluginShellFor(manifest) { return shell }
  function publicPluginManifest(manifest) { return { id: manifest.id, label: manifest.label || "" } }
  function pluginBarWidgetRegistryFor(manifest) { return null }
  function pluginRegistryFor(manifest) { return null }
  function observeMaslowVoiceLock(inst) {}
  function forgetMaslowVoiceLock(id) {}
  function check(ok, message) {
    if (!ok) {
      console.log("RESULT fail " + message)
      Qt.quit()
      throw new Error(message)
    }
  }
  function setBackground(file, firstParty, auth) {
    registry.enabled = true
    registry.installedPlugins = ({ "omarchy.background": {
      id: "omarchy.background", kinds: ["service"], entryPoints: { service: file },
      url: Qt.resolvedUrl(file).toString(), __isFirstParty: firstParty !== false,
      __hostCapabilities: auth ? ["authentication"] : [], label: "initial"
    } })
  }
  function disableBackground() {
    registry.enabled = false
    shell._syncServices()
  }
  function begin(file) {
    loadSerial++
    setBackground(loadSerial + "-" + file)
    check(ensureService("omarchy.background") === null, "async ensure returns no premature service")
    check(_backgroundServiceLoad !== null, "retain a loading claim")
    check(_backgroundServiceLoad.component.status === Component.Loading, "real Qt component is asynchronous")
    originalClaim = _backgroundServiceLoad
  }
  function clear() {
    registry.installedPlugins = ({})
    shell._syncServices()
    check(_backgroundServiceLoad === null, "removal cancels claim")
    check(!_services["omarchy.background"], "removal drops published service")
  }
  Connections {
    target: shell._services["omarchy.background"] || null
    function onHeartbeat(count) { shell.heartbeats++ }
  }
  // PRODUCTION_METHODS

  Component.onCompleted: {
    begin("a.qml")
    ensureService("omarchy.background")
    _syncServices()
    check(_backgroundServiceLoad === originalClaim, "duplicate ensure and sync reuse pending claim")
    registry.installedPlugins["omarchy.background"].label = "fresh"
  }
  Timer {
    interval: 20
    repeat: true
    running: true
    onTriggered: {
      shell.waits++
      shell.check(shell.waits < 500, "bounded lifecycle completion")
      var live = shell._services["omarchy.background"]
      if (shell.phase === 0) {
        if (!live || live.ticks < 2 || shell.heartbeats < 2) return
        shell.check(shell.created === 1 && live.parent === serviceHost, "one parented first-party background")
        shell.check(live.manifest.label === "fresh", "publish latest same-source metadata")
        shell.check(shell._backgroundServiceLoad === null, "component claim is released after publication")
        shell.observedTicks = live.ticks
        shell.omarchyPath = "/updated"
        shell.phase = 10
      } else if (shell.phase === 10) {
        if (live.ticks <= shell.observedTicks) return
        shell.check(live.touch() === "a:/updated", "post-component-release callbacks, signals and property bindings stay alive")
        shell.clear()
        shell.begin("b.qml")
        shell.disableBackground()
        shell.check(shell._backgroundServiceLoad === null, "disable cancels immediately")
        shell.phase = 1
      } else if (shell.phase === 1) {
        shell.check(!live && shell.created === 1, "disabled pending service never appears")
        shell.begin("a.qml")
        shell.clear()
        shell.phase = 2
      } else if (shell.phase === 2) {
        shell.check(!live && shell.created === 1, "removed pending service never appears")
        shell.begin("a.qml")
        shell.setBackground("b.qml")
        shell._syncServices()
        shell.check(shell._backgroundServiceLoad !== shell.originalClaim, "source replacement gets new claim")
        shell.phase = 3
      } else if (shell.phase === 3) {
        if (!live) return
        shell.check(live.tag === "b" && shell.created === 2, "only replacement source publishes")
        shell.clear()
        shell.begin("a.qml")
        var generation = shell._backgroundServiceGeneration
        shell.pluginReloading = true
        shell.unloadPluginServices()
        shell.check(shell._backgroundServiceLoad === null && shell._backgroundServiceGeneration > generation, "reload invalidates generation")
        shell.pluginReloading = false
        shell.ensureService("omarchy.background")
        shell.phase = 4
      } else if (shell.phase === 4) {
        if (!live) return
        shell.check(live.tag === "a" && shell.created === 3, "reload creates one current service")
        shell.clear()
        shell.begin("broken.qml")
        shell.phase = 5
      } else if (shell.phase === 5) {
        if (shell._backgroundServiceLoad) return
        shell.check(!live, "failed compilation publishes nothing")
        shell.ensureService("omarchy.background")
        shell.check(shell._backgroundServiceLoad !== shell.originalClaim, "failed claim permits retry")
        shell.phase = 6
      } else if (shell.phase === 6) {
        if (shell._backgroundServiceLoad) return
        shell.begin("b.qml")
        shell.cancelDuringInjection = true
        shell.phase = 7
      } else if (shell.phase === 7) {
        if (shell._backgroundServiceLoad) return
        shell.check(!live && shell.created === 4, "creation-time disable never publishes stale object")
        shell.cancelDuringInjection = false
        shell.setBackground("b.qml")
        shell.ensureService("omarchy.background")
        shell.phase = 8
      } else if (shell.phase === 8) {
        if (!live) return
        shell.check(shell.created === 5, "creation-time cancellation permits fresh retry")
        shell.clear()
        shell.setBackground("a.qml", false)
        var thirdParty = shell.ensureService("omarchy.background")
        shell.check(thirdParty !== null && thirdParty.parent === null && shell._backgroundServiceLoad === null, "third-party keeps synchronous detached path")
        shell.clear()
        registry.installedPlugins = ({ "omarchy.lock": {
          id: "omarchy.lock", kinds: ["service"], entryPoints: { service: "a.qml" },
          url: Qt.resolvedUrl("a.qml").toString(), __isFirstParty: true,
          __hostCapabilities: ["authentication"], keepLoaded: true
        } })
        shell.check(shell.ensureService("omarchy.lock") === null, "auth return contract remains private")
        shell.check(AuthServiceStore.has("omarchy.lock") && !shell._services["omarchy.lock"], "auth stays outside public service map")
        shell.check(shell._backgroundServiceLoad === null, "auth never enters async background claim")
        shell.keptAuth = AuthServiceStore.services["omarchy.lock"]
        shell.check(shell.keptAuth.parent === null, "authentication service remains detached")
        shell._syncServices()
        shell.unloadPluginServices()
        shell.check(AuthServiceStore.services["omarchy.lock"] === shell.keptAuth, "keepLoaded auth identity survives sync and unload")
        shell.keptAuth = null
        AuthServiceStore.destroy("omarchy.lock")
        shell.begin("a.qml")
        shell.setBackground("b.qml", true, true)
        shell._syncServices()
        shell.check(!shell._services["omarchy.background"] && AuthServiceStore.has("omarchy.background"), "new auth capability cancels public async creation")
        shell.check(shell._backgroundServiceLoad === null, "new auth capability clears pending claim")
        AuthServiceStore.destroy("omarchy.background")
        shell.clear()
        shell.phase = 9
      } else {
        shell.check(shell.destroyed >= 5, "real QObject destruction was observed")
        console.log("RESULT pass")
        Qt.quit()
      }
    }
  }
}
