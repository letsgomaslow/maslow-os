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

float hash(vec3 p) {
  p = fract(p * 0.3183099 + vec3(0.11, 0.17, 0.23));
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x),
                 mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x),
                 mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

float clouds(vec3 p) {
  float density = 0.0;
  float weight = 0.57;
  for (int i = 0; i < 4; i++) {
    density += weight * noise(p);
    p = p * 2.03 + vec3(3.7, 7.1, 2.9);
    weight *= 0.48;
  }
  return density;
}

void main() {
  vec2 p = qt_TexCoord0 * 2.0 - 1.0;
  float radius = length(p);
  float edge = 1.0 - smoothstep(0.965, 1.0, radius);
  float depth = sqrt(max(0.0, 1.0 - dot(p, p)));
  vec3 normal = vec3(p, depth);
  float drift = phase * 0.23;
  float turn = stateMode == 3.0 ? phase * 0.2 : sin(phase * 0.3) * 0.12;
  vec2 flow = mat2(cos(turn), -sin(turn), sin(turn), cos(turn)) * p;
  vec3 cloudPosition = vec3(flow * (2.1 - level * 0.35), depth * 1.7);
  cloudPosition += vec3(drift, -drift * 0.5, phase * 0.1);
  if (stateMode == 1.0) {
    cloudPosition.y *= 0.7;
    cloudPosition.y += phase * 0.2;
  } else if (stateMode == 2.0) {
    cloudPosition.xy += p * sin(radius * 7.0 - phase * 2.0) * level * 0.12;
  } else if (stateMode == 4.0) {
    cloudPosition.x += sin(p.y * 3.0 + phase * 2.5) * (0.1 + level * 0.25);
    cloudPosition.y -= phase * 0.18;
  }
  float density = clouds(cloudPosition);
  float cloud = smoothstep(0.31, 0.64, density + level * 0.065);
  float light = clamp(dot(normal, normalize(vec3(-0.4, -0.5, 0.9))), 0.0, 1.0);
  // Canonical Maslow Voice palette from branding/design-tokens.json.
  vec3 blue = mix(vec3(21.0, 75.0, 168.0) / 255.0, vec3(40.0, 117.0, 229.0) / 255.0, light);
  vec3 white = mix(vec3(147.0, 201.0, 255.0) / 255.0, vec3(239.0, 248.0, 255.0) / 255.0, light);
  vec3 color = mix(blue, white, cloud);
  // Cool edge light gives depth while preserving the circular silhouette.
  color += vec3(0.12, 0.20, 0.27) * pow(1.0 - depth, 3.0) * 0.5;
  color += vec3(0.08) * pow(light, 12.0);
  fragColor = vec4(color * edge, edge) * qt_Opacity;
}
