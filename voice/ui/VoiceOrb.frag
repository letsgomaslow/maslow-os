#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
  mat4 qt_Matrix;
  float qt_Opacity;
  float level;
  float phase;
  float disabled;
};

float circle(vec2 p, float radius) {
  return 1.0 - smoothstep(radius - 0.025, radius + 0.025, length(p));
}

void main() {
  vec2 p = qt_TexCoord0 * 2.0 - 1.0;
  float ripple = sin(atan(p.y, p.x) * 5.0 + phase) * level * 0.10;
  float edge = circle(p, 0.94 + ripple * 0.25);
  vec3 teal = vec3(0.427, 0.769, 0.678);
  vec3 purple = vec3(0.251, 0.094, 0.467);
  vec3 color = mix(purple, teal, clamp(qt_TexCoord0.y + sin(p.x * 4.0 + phase) * 0.13 + level * 0.2, 0.0, 1.0));
  color = mix(color, vec3(0.42), disabled);
  fragColor = vec4(color * edge, edge) * qt_Opacity;
}
