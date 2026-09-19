#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
  mat4 qt_Matrix;
  float qt_Opacity;
  float level;
  float phase;
  float stateMode;
};

mat2 rotation(float angle) {
  return mat2(cos(angle), -sin(angle), sin(angle), cos(angle));
}

// A curved translucent sheet inside the shell. Depth changes both its
// projected shape and edge softness; no texture or noise is needed.
vec2 ribbon(vec3 point, float turn, float offset) {
  point.xz = rotation(turn) * point.xz;
  point.xy = rotation(offset) * point.xy;
  float curve = point.y + 0.32 * sin(point.x * 2.6 + point.z * 1.8);
  float distanceToSheet = abs(curve - offset * 0.22);
  float front = smoothstep(-0.65, 0.8, point.z);
  float width = 0.16 + level * 0.055;
  float softness = mix(0.16, 0.035, front);
  float body = 1.0 - smoothstep(width, width + softness, distanceToSheet);
  float lipDistance = (distanceToSheet - width) / (0.028 + softness * 0.35);
  float lip = exp(-(lipDistance * lipDistance));
  return vec2(body * mix(0.28, 0.78, front), lip * front);
}

void main() {
  vec2 p = qt_TexCoord0 * 2.0 - 1.0;
  float radius = length(p);
  float edge = 1.0 - smoothstep(0.975, 1.0, radius);
  float depth = sqrt(max(0.0, 1.0 - dot(p, p)));
  vec3 normal = vec3(p, depth);
  float turn = phase * 0.31;
  if (stateMode == 3.0) turn += phase * 0.21;

  // Refraction-like compression keeps motion inside a stable glass silhouette.
  vec3 interior = vec3(p * (0.72 + depth * 0.28), depth * 0.8);
  if (stateMode == 2.0) {
    interior.xy *= 1.0 - level * 0.12;
    interior.y += sin(p.x * 2.8 + phase) * level * 0.12;
  } else if (stateMode == 4.0) {
    interior.x *= 1.0 + level * 0.18;
    interior.y *= 1.0 - level * 0.14;
  }

  // Canonical Maslow Voice palette from branding/design-tokens.json.
  vec3 blueDeep = vec3(21.0, 75.0, 168.0) / 255.0;
  vec3 blue = vec3(40.0, 117.0, 229.0) / 255.0;
  vec3 ice = vec3(147.0, 201.0, 255.0) / 255.0;
  vec3 white = vec3(239.0, 248.0, 255.0) / 255.0;
  vec3 teal = vec3(115.0, 193.0, 174.0) / 255.0;
  vec3 purple = vec3(101.0, 76.0, 143.0) / 255.0;
  float light = max(0.0, dot(normal, normalize(vec3(-0.48, -0.6, 0.8))));
  vec3 color = mix(blueDeep * 0.38, blue, 0.24 + light * 0.35);

  // Three broad sheets overlap at different orientations and drift rates.
  vec2 back = ribbon(interior, -turn * 0.62 + 1.7, -0.8);
  vec2 middle = ribbon(interior, turn + 0.3, 0.55);
  vec2 front = ribbon(interior, -turn * 0.77 - 0.6, 1.9);
  color = mix(color, mix(blue, teal, 0.26), back.x);
  color = mix(color, mix(ice, teal, 0.12), middle.x * 0.82);
  color = mix(color, mix(mix(blue, white, 0.46), purple, 0.12), front.x * 0.72);
  color += white * (back.y * 0.035 + middle.y * 0.16 + front.y * 0.12);

  // Uneven Fresnel reflection and a localized softbox highlight establish
  // thickness without adding a second circular outline over the material.
  float fresnel = pow(1.0 - depth, 3.1);
  float rimLight = 0.18 + 0.68 * max(0.0, dot(normal.xy, normalize(vec2(-0.7, -0.9))));
  if (stateMode == 1.0) {
    rimLight += 0.48 * pow(max(0.0, dot(normal.xy, vec2(cos(phase * 1.8), sin(phase * 1.8)))), 6.0);
  }
  color = mix(color, ice, fresnel * rimLight);
  vec2 reflection = (p - vec2(-0.34, -0.56)) / vec2(0.38, 0.12);
  float specular = exp(-dot(reflection, reflection) * 1.8);
  color = mix(color, white, specular * 0.8);
  color += ice * pow(max(0.0, dot(normal, normalize(vec3(0.68, 0.56, 0.28)))), 24.0) * 0.24;
  fragColor = vec4(clamp(color, 0.0, 1.0) * edge, edge) * qt_Opacity;
}
