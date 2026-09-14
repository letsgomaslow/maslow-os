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
  vec3 normal = normalize(vec3(p, sqrt(max(0.0, 1.0 - dot(p, p)))));
  vec3 lightDirection = normalize(vec3(-0.45, -0.55, 0.70));
  float diffuse = max(0.0, dot(normal, lightDirection));
  float highlight = pow(max(0.0, dot(normal, normalize(vec3(-0.35, -0.45, 0.90)))), 14.0) * 0.20;
  vec3 disabledShadow = vec3(0.271, 0.302, 0.357);
  vec3 disabledLight = vec3(0.824, 0.843, 0.871);
  vec3 disabledColor = mix(disabledShadow, disabledLight, clamp(0.17 + diffuse * 0.72, 0.0, 1.0));
  disabledColor += vec3(highlight);
  color = mix(color, disabledColor, disabled);
  fragColor = vec4(color * edge, edge) * qt_Opacity;
}
