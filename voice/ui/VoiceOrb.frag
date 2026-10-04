#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
  mat4 qt_Matrix;
  float qt_Opacity;
  float phase;
  vec4 topColor;
  vec4 accentColor;
  vec4 bottomColor;
};
void main() {
  vec2 p = qt_TexCoord0 * 2.0 - 1.0;
  float angle = atan(p.y, p.x);
  float radius = 0.79 + sin(angle * 3.0 + phase * 1.4) * 0.035 + cos(angle * 2.0 - phase) * 0.025;
  float edge = 1.0 - smoothstep(radius - 0.012, radius, length(p));
  float t = clamp(dot(p - vec2(-0.5, -0.7), vec2(0.9, 1.5)) / 3.06, 0.0, 1.0);
  vec3 color = t < 0.32 ? mix(topColor.rgb, accentColor.rgb, t / 0.32) : mix(accentColor.rgb, bottomColor.rgb, (t - 0.32) / 0.68);
  float highlight = clamp(1.0 - length(p - vec2(-0.3, -0.4)) / 0.4, 0.0, 1.0) * 0.28;
  color = mix(color, vec3(1.0), highlight);
  fragColor = vec4(color * edge, edge) * qt_Opacity;
}
