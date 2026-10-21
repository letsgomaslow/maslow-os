import QtQuick
import Quickshell
import "screensaver/ScreensaverModel.js" as Model

// Renders the real ScreensaverScene without the service, a layer-shell
// surface or any input, so it runs offscreen with the software renderer. The
// test links the plugin directory in as ./screensaver for the model import.
//
// OMARCHY_QML_TEST_RESULT: instantiate the scene at 1440x900, 1280x800 and
// 1920x1080, check that every image loads, that the mark, wordmark, clock and
// hint stay on screen on one vertical axis at several instants including the
// drift extremes, that Reduced Motion holds a still frame, and write a JSON
// result.
//
// GALLERY_OUTPUT=<dir>: save <dir>/<WxH>-<ms>[-reduced].png for every size
// in SCREENS (default 1440x900) and time in GALLERY_TIMES (default 0), then
// quit. REDUCED=1 renders Reduced Motion, whose position follows the service's
// reduced cycle (one step per REDUCED_REPOSITION_MS). SCREEN_INDEX and
// SCREEN_COUNT render another screen of a multi-monitor setup.
ShellRoot {
  id: root

  readonly property string resultPath: Quickshell.env("OMARCHY_QML_TEST_RESULT")
  readonly property string rootPath: Quickshell.env("OMARCHY_PATH")
  readonly property string galleryOutput: Quickshell.env("GALLERY_OUTPUT")
  readonly property bool reduced: Quickshell.env("REDUCED") === "1"
  readonly property string sceneUrl: "file://" + rootPath + "/shell/plugins/screensaver/ScreensaverScene.qml"
  property var failures: []
  property var checks: []
  property var jobs: []
  property int jobIndex: 0
  property var current: null
  property int waits: 0

  function fail(message) {
    failures.push(String(message))
  }

  function assertTrue(condition, message) {
    if (!condition) fail(message)
    else checks.push(String(message))
  }

  function shellQuote(value) {
    return "'" + String(value).replace(/'/g, "'\\''") + "'"
  }

  function writeResult() {
    var payload = JSON.stringify({
      ok: failures.length === 0,
      failures: failures,
      checks: checks
    })

    if (resultPath) {
      Quickshell.execDetached(["bash", "-lc", "printf '%s' " + shellQuote(payload) + " > " + shellQuote(resultPath)])
    }
  }

  function parseSizes(value, fallback) {
    var parts = String(value || fallback).split(",")
    var sizes = []
    for (var i = 0; i < parts.length; i++) {
      var match = /^\s*(\d+)x(\d+)\s*$/.exec(parts[i])
      if (match) sizes.push({ width: Number(match[1]), height: Number(match[2]) })
    }
    return sizes
  }

  function parseTimes(value, fallback) {
    var parts = String(value || fallback).split(",")
    var times = []
    for (var i = 0; i < parts.length; i++) {
      var n = Number(parts[i])
      if (isFinite(n) && n >= 0) times.push(n)
    }
    return times
  }

  function createScene(size, reduced) {
    var component = Qt.createComponent(root.sceneUrl, Component.PreferSynchronous)
    if (component.status !== Component.Ready) {
      root.fail("ScreensaverScene failed to load: " + component.errorString())
      return null
    }
    var scene = component.createObject(host, {
      width: size.width,
      height: size.height,
      omarchyPath: root.rootPath,
      reducedMotion: reduced,
      screenIndex: Number(Quickshell.env("SCREEN_INDEX") || 0),
      screenCount: Number(Quickshell.env("SCREEN_COUNT") || 1),
      clockText: "21:45"
    })
    if (!scene) root.fail("ScreensaverScene failed to instantiate: " + component.errorString())
    return scene
  }

  function rectOf(item) {
    var point = item.mapToItem(root.current, 0, 0)
    return { x: point.x, y: point.y, width: item.width, height: item.height }
  }

  function centreX(rect) {
    return rect.x + rect.width / 2
  }

  function insideScreen(rect, size) {
    return rect.x >= 0 && rect.y >= 0 && rect.x + rect.width <= size.width && rect.y + rect.height <= size.height
  }

  // Every Image in the scene, Repeater delegates included.
  function imagesIn(item, list) {
    var found = list || []
    if (item && item.sourceSize !== undefined && item.status !== undefined && item.source !== undefined) found.push(item)
    var children = item ? item.children : []
    for (var i = 0; i < children.length; i++) root.imagesIn(children[i], found)
    return found
  }

  function findItem(item, test) {
    if (!item) return null
    if (test(item)) return item
    var children = item.children
    for (var i = 0; i < children.length; i++) {
      var hit = root.findItem(children[i], test)
      if (hit) return hit
    }
    return null
  }

  function sourceName(image) {
    var parts = String(image.source).split("/")
    return parts[parts.length - 1]
  }

  function imagesReady(scene) {
    var images = root.imagesIn(scene)
    for (var i = 0; i < images.length; i++) {
      if (images[i].status !== Image.Ready) return false
    }
    return images.length > 0
  }

  function visibleSprites(scene, name) {
    var images = root.imagesIn(scene)
    var count = 0
    for (var i = 0; i < images.length; i++) {
      if (root.sourceName(images[i]) === name && images[i].visible && images[i].opacity > 0.01) count++
    }
    return count
  }

  // Mirrors the service: the frame clock is elapsed time, and Reduced Motion
  // holds still and steps its reduced cycle every REDUCED_REPOSITION_MS.
  function setTime(scene, time, reduced) {
    scene.elapsedMs = time
    scene.repositionCycle = reduced ? Math.floor(time / Model.REDUCED_REPOSITION_MS) : 0
  }

  // Time at which sin(TAU * t / period + phase) reaches its extreme `target`
  // (1 or -1), for the drift extremes of screen 0.
  function extremeTime(period, phase, target) {
    var angle = target > 0 ? Math.PI / 2 : 3 * Math.PI / 2
    var t = (angle - phase) / (2 * Math.PI) * period
    while (t < 0) t += period
    return Math.round(t)
  }

  function layoutOf(scene) {
    var markBox = root.findItem(scene.lockupItem, function(item) {
      var kids = item.children
      for (var i = 0; i < kids.length; i++) {
        if (kids[i].source !== undefined && root.sourceName(kids[i]) === "maslow-mark-gradient.svg") return true
      }
      return false
    })
    var maslow = root.findItem(scene.lockupItem, function(item) { return item.text === "MASLOW" })
    var wordmark = maslow ? maslow.parent : null
    var box = markBox ? root.rectOf(markBox) : null
    // The visible paths sit opticalShift left of the mark's box; the scene
    // nudges the box right by the same amount so the paths look centred.
    // Mapping the point (not the box origin) keeps the breathing scale in.
    var visibleCentre = markBox ? markBox.mapToItem(root.current, markBox.width / 2 - scene.markWidth * scene.opticalShift, markBox.height / 2) : null
    return {
      lockup: root.rectOf(scene.lockupItem),
      markBox: box,
      markCentre: visibleCentre ? visibleCentre.x : NaN,
      markScale: markBox ? markBox.scale : NaN,
      wordmark: wordmark ? root.rectOf(wordmark) : null,
      clock: root.rectOf(scene.clockItem),
      hint: root.rectOf(scene.hintItem)
    }
  }

  function checkFrame(scene, size, time) {
    var label = size.width + "x" + size.height + " at " + time + " ms"
    root.setTime(scene, time, false)
    var l = root.layoutOf(scene)
    if (!l.markBox || !l.wordmark) {
      root.fail(label + " mark or wordmark not found in the lockup")
      return
    }
    root.assertTrue(root.insideScreen(l.lockup, size), label + " lockup in bounds " + JSON.stringify(l.lockup))
    root.assertTrue(root.insideScreen(l.clock, size), label + " clock in bounds " + JSON.stringify(l.clock))
    root.assertTrue(root.insideScreen(l.hint, size), label + " hint in bounds " + JSON.stringify(l.hint))
    root.assertTrue(l.wordmark.y >= l.markBox.y + l.markBox.height, label + " wordmark sits below the mark")
    root.assertTrue(l.clock.y >= l.wordmark.y + l.wordmark.height, label + " clock sits below the wordmark " + JSON.stringify([l.wordmark, l.clock]))
    root.assertTrue(l.hint.y >= l.clock.y + l.clock.height, label + " hint sits below the clock")
    var axis = root.centreX(l.wordmark)
    root.assertTrue(Math.abs(l.markCentre - axis) <= 2, label + " mark is centred over the wordmark, " + l.markCentre + " vs " + axis)
    root.assertTrue(Math.abs(root.centreX(l.clock) - axis) <= 2, label + " clock is centred under the wordmark, " + root.centreX(l.clock) + " vs " + axis)
    root.assertTrue(Math.abs(root.centreX(l.hint) - axis) <= 2, label + " hint is centred under the wordmark")
  }

  function checkScene(scene, size) {
    var label = size.width + "x" + size.height
    root.assertTrue(scene.markReady, label + " mark SVG is ready")
    root.assertTrue(scene.glowReady, label + " halo PNG is ready")
    var images = root.imagesIn(scene)
    var names = {}
    var unready = []
    for (var i = 0; i < images.length; i++) {
      names[root.sourceName(images[i])] = true
      if (images[i].status !== Image.Ready) unready.push(root.sourceName(images[i]))
    }
    root.assertTrue(unready.length === 0, label + " every image is ready, not ready: " + unready.join(", "))
    var expected = ["maslow-mark-gradient.svg", "glow.png", "particle.png", "ring.png"]
    for (var a = 0; a < Model.AURORA.length; a++) expected.push("aurora-" + Model.AURORA[a].key + ".png")
    for (var e = 0; e < expected.length; e++) root.assertTrue(names[expected[e]] === true, label + " scene draws " + expected[e])
    root.assertTrue(scene.rasterHeight > scene.markHeight, label + " mark raster is cut above display size, got " + scene.rasterHeight + " for " + scene.markHeight)
    root.assertTrue(scene.clockItem.text === "21:45" && scene.clockItem.width > 0, label + " clock text renders")
    root.assertTrue(scene.hintItem.text === "PRESS ANY KEY" && scene.hintItem.width > 0, label + " hint text renders")

    var times = [
      0,
      Model.PARTICLE_TRAVEL_MS / 2,
      Model.RIPPLE_MS * 1.5,
      root.extremeTime(97000, 0, 1),
      root.extremeTime(97000, 0, -1),
      root.extremeTime(131000, 1, 1),
      root.extremeTime(131000, 1, -1)
    ]
    for (var t = 0; t < times.length; t++) root.checkFrame(scene, size, times[t])

    root.setTime(scene, Model.PARTICLE_TRAVEL_MS / 2, false)
    root.assertTrue(root.visibleSprites(scene, "particle.png") >= 2, label + " light is crossing the bridges")
    root.setTime(scene, Model.RIPPLE_MS * 0.3, false)
    root.assertTrue(root.visibleSprites(scene, "ring.png") === 1, label + " one ripple is leaving a circle")
    root.setTime(scene, 0, false)
  }

  // Reduced Motion: no particles or ripples, no breathing, and nothing moves
  // within a cycle; the next cycle moves the composition at once.
  function checkReduced(scene, size) {
    var label = size.width + "x" + size.height + " Reduced Motion"
    root.setTime(scene, 1000, true)
    var first = root.layoutOf(scene)
    var aurora = root.imagesIn(scene).filter(function(image) { return root.sourceName(image).indexOf("aurora-") === 0 })
    var auroraBefore = JSON.stringify(aurora.map(function(image) { return [image.x, image.y, image.opacity] }))
    root.assertTrue(root.visibleSprites(scene, "particle.png") === 0, label + " shows no particles")
    root.assertTrue(root.visibleSprites(scene, "ring.png") === 0, label + " shows no ripples")
    root.assertTrue(Math.abs(first.markScale - 1 / (1 + Model.BREATH_DEPTH / 2)) < 1e-9, label + " mark does not breathe")
    root.setTime(scene, Model.REDUCED_REPOSITION_MS - 1000, true)
    var later = root.layoutOf(scene)
    root.assertTrue(JSON.stringify(later) === JSON.stringify(first), label + " holds a still frame within a cycle")
    root.assertTrue(JSON.stringify(aurora.map(function(image) { return [image.x, image.y, image.opacity] })) === auroraBefore, label + " holds the aurora still")
    root.setTime(scene, Model.REDUCED_REPOSITION_MS + 1000, true)
    var moved = root.layoutOf(scene)
    root.assertTrue(moved.lockup.x !== first.lockup.x || moved.lockup.y !== first.lockup.y, label + " moves to a new place each cycle")
    root.assertTrue(root.insideScreen(moved.lockup, size) && root.insideScreen(moved.hint, size), label + " stays on screen after moving")
  }

  FloatingWindow {
    id: window
    visible: true
    color: "#121D35"
    implicitWidth: 1920
    implicitHeight: 1080

    Item {
      id: host
      width: 1920
      height: 1080
    }
  }

  // Waits for the images, then either checks or captures the current job.
  // Jobs stay plain data; the live scene is held in root.current, since a var
  // list hands back copies of its elements.
  Timer {
    id: stepper
    interval: 50
    repeat: true
    running: false
    onTriggered: {
      try {
        root.step()
      } catch (error) {
        root.fail("screensaver preview fixture threw: " + error)
        root.finish()
      }
    }
  }

  function finish() {
    stepper.stop()
    if (root.galleryOutput) {
      for (var i = 0; i < root.failures.length; i++) console.warn(root.failures[i])
      Qt.quit()
    } else {
      root.writeResult()
    }
  }

  function step() {
    var job = root.jobs[root.jobIndex]
    if (!job) {
      root.finish()
      return
    }

    if (!root.current) {
      var scene = root.createScene(job.size, job.reduced)
      if (!scene) {
        root.finish()
        return
      }
      root.setTime(scene, job.time, job.reduced)
      root.current = scene
      root.waits = 0
      return
    }

    var live = root.current
    if (!root.imagesReady(live) && root.waits++ < 60) return

    stepper.stop()
    if (root.galleryOutput) {
      var name = root.galleryOutput + "/" + job.size.width + "x" + job.size.height + "-" + job.time + (job.reduced ? "-reduced" : "") + ".png"
      var grabbed = live.grabToImage(function(result) {
        result.saveToFile(name)
        console.log("Gallery saved " + name)
        root.finishJob(live)
      }, Qt.size(job.size.width, job.size.height))
      if (!grabbed) {
        root.fail("grabToImage refused " + name)
        root.finish()
      }
    } else {
      if (job.reduced) root.checkReduced(live, job.size)
      else root.checkScene(live, job.size)
      root.finishJob(live)
    }
  }

  function finishJob(scene) {
    root.current = null
    scene.destroy()
    root.jobIndex++
    stepper.start()
  }

  Component.onCompleted: {
    var list = []
    if (root.galleryOutput) {
      var sizes = root.parseSizes(Quickshell.env("SCREENS"), "1440x900")
      var times = root.parseTimes(Quickshell.env("GALLERY_TIMES"), "0")
      for (var i = 0; i < sizes.length; i++) {
        for (var j = 0; j < times.length; j++) list.push({ size: sizes[i], time: times[j], reduced: root.reduced })
      }
    } else {
      var checked = [{ width: 1440, height: 900 }, { width: 1280, height: 800 }, { width: 1920, height: 1080 }]
      for (var k = 0; k < checked.length; k++) {
        list.push({ size: checked[k], time: 0, reduced: false })
        list.push({ size: checked[k], time: 1000, reduced: true })
      }
    }
    root.jobs = list
    stepper.start()
  }
}
