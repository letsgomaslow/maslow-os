// WCAG contrast helpers. Colors are { r, g, b } with channels from 0 to 1, the
// shape of a QML color, so the shell and Node tests share the same math.

function channel(value) {
  return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4)
}

function luminance(c) {
  return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b)
}

function ratio(a, b) {
  var la = luminance(a)
  var lb = luminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

// What `top` at `alpha` looks like painted over an opaque `bottom`.
function over(top, bottom, alpha) {
  return {
    r: top.r * alpha + bottom.r * (1 - alpha),
    g: top.g * alpha + bottom.g * (1 - alpha),
    b: top.b * alpha + bottom.b * (1 - alpha)
  }
}

// Smallest alpha (in hundredths) at which `foreground` drawn over `background`
// reaches `target` contrast against both the bare background and a control
// fill of the same foreground at `fillAlpha`. A border sits between the two,
// so it has to stand out from each. Returns 1 when no alpha gets there.
function minimumAlpha(foreground, background, fillAlpha, target) {
  if (!foreground || !background) return 0
  var fill = over(foreground, background, fillAlpha || 0)
  for (var step = 0; step <= 100; step++) {
    var mixed = over(foreground, background, step / 100)
    if (ratio(mixed, background) >= target && ratio(mixed, fill) >= target) return step / 100
  }
  return 1
}

if (typeof module !== "undefined") {
  module.exports = {
    luminance: luminance,
    ratio: ratio,
    over: over,
    minimumAlpha: minimumAlpha
  }
}
