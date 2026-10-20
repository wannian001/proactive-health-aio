// A cartoon 3D body that turns all the way round: MakeHuman's CC0 base mesh, rounded, given muscle lines and split into
// the check-in regions by tools/make_body_mesh.py (models/recovery/MODEL.md), drawn with plain WebGL. All colours on
// it come from recorded regional data.
import { rv, t } from "./i18n.js";

// the side of the person turned towards you at a yaw of 0°, 90°, 180°, 270° (a positive yaw turns their front to your right)
const VIEWS = ["angleFront", "angleRight", "angleBack", "angleLeft"];
const QUARTER = Math.PI / 2, TURN = 2 * Math.PI;
const DRAG = 0.011;          // radians per CSS pixel dragged: about 570 px for a full turn
const FOV = 20 * Math.PI / 180;
// a cartoon: soft white, slate shorts, muscle lines a few shades darker, a dark outline (near black in the dark theme)
const LOOK = {
  light: { skin: [0.94, 0.945, 0.96], shorts: [0.38, 0.43, 0.54], outline: [0.30, 0.33, 0.40], ink: [0.30, 0.34, 0.44], rim: 0.12 },
  dark: { skin: [0.90, 0.91, 0.94], shorts: [0.36, 0.41, 0.53], outline: [0.04, 0.05, 0.08], ink: [0.30, 0.34, 0.44], rim: 0.22 },
};
const OUTLINE = 1.6;  // CSS pixels

export function viewIndex(yaw) { return ((Math.round(yaw / QUARTER) % 4) + 4) % 4; }

// "HAB3", uint32 header length, JSON header, then int16 positions, int8 normals, uint8 occlusion + cloth, uint8 regions
// (the two strongest, by their index in header.regions, and how much of the first),
// uint16 triangles; then the muscle lines' int16 positions and uint16 triangles, each block 4-byte aligned (tools/make_body_mesh.py)
export function parseBody(buffer) {
  const bytes = new Uint8Array(buffer);
  if (String.fromCharCode(...bytes.subarray(0, 4)) !== "HAB3") throw Error("Not a body file");
  const length = new DataView(buffer).getUint32(4, true);
  const header = JSON.parse(new TextDecoder().decode(bytes.subarray(8, 8 + length)));
  const n = header.vertices;
  let at = 8 + length;
  const quant = new Int16Array(buffer, at, n * 3); at += n * 6; at += (4 - at % 4) % 4;
  const normals = new Int8Array(buffer, at, n * 4); at += n * 4;
  const extra = new Uint8Array(buffer, at, n * 4); at += n * 4;
  const shares = new Uint8Array(buffer, at, n * 4); at += n * 4;
  const indices = new Uint16Array(buffer, at, header.triangles * 3); at += header.triangles * 6;
  let lines = null;
  if (header.lines) {
    at += (4 - at % 4) % 4;
    const quant = new Int16Array(buffer, at, header.lines.vertices * 3); at += header.lines.vertices * 6; at += (4 - at % 4) % 4;
    lines = { quant, indices: new Uint16Array(buffer, at, header.lines.triangles * 3) };
  }
  const positions = new Float32Array(n * 3);
  let radius = 0;
  for (let i = 0; i < n * 3; i++) positions[i] = header.center[i % 3] + quant[i] / 32767 * header.extent[i % 3];
  for (let i = 0; i < n; i++) radius = Math.max(radius, Math.hypot(positions[i * 3], positions[i * 3 + 2]));
  return { header, quant, normals, extra, shares, indices, positions, radius, lines };
}

let asset;
function loadAsset() {
  if (!asset) asset = fetch(new URL("../models/recovery/body.bin", import.meta.url))
    .then(r => { if (!r.ok) throw Error(`HTTP ${r.status}`); return r.arrayBuffer(); })
    .then(parseBody)
    .catch(error => { asset = null; throw error; });
  return asset;
}

// nearest triangle along a ray, in the body's own coordinates (Möller–Trumbore)
function raycast(body, origin, dir) {
  const P = body.positions, I = body.indices;
  let best = null;
  for (let k = 0; k < I.length; k += 3) {
    const a = I[k] * 3, b = I[k + 1] * 3, c = I[k + 2] * 3;
    const e1x = P[b] - P[a], e1y = P[b + 1] - P[a + 1], e1z = P[b + 2] - P[a + 2];
    const e2x = P[c] - P[a], e2y = P[c + 1] - P[a + 1], e2z = P[c + 2] - P[a + 2];
    const px = dir[1] * e2z - dir[2] * e2y, py = dir[2] * e2x - dir[0] * e2z, pz = dir[0] * e2y - dir[1] * e2x;
    const det = e1x * px + e1y * py + e1z * pz;
    if (Math.abs(det) < 1e-12) continue;
    const inv = 1 / det, tx = origin[0] - P[a], ty = origin[1] - P[a + 1], tz = origin[2] - P[a + 2];
    const u = (tx * px + ty * py + tz * pz) * inv;
    if (u < 0 || u > 1) continue;
    const qx = ty * e1z - tz * e1y, qy = tz * e1x - tx * e1z, qz = tx * e1y - ty * e1x;
    const v = (dir[0] * qx + dir[1] * qy + dir[2] * qz) * inv;
    if (v < 0 || u + v > 1) continue;
    const d = (e2x * qx + e2y * qy + e2z * qz) * inv;
    if (d > 1e-6 && (!best || d < best.d)) best = { d, k, u, v };
  }
  return best;
}

const VERTEX = `
attribute vec3 aPos; attribute vec4 aNormal; attribute vec4 aExtra; attribute vec4 aRegion;
uniform vec3 uCenter, uExtent; uniform mat3 uTurn; uniform mat4 uCamera; uniform float uOutline;
uniform vec4 uTint[REGIONS];
varying vec3 vNormal, vWorld; varying float vCloth, vY, vOcclusion; varying vec4 vTint;
void main() {
  vec3 p = uCenter + aPos * uExtent;
  vY = p.y; vNormal = uTurn * aNormal.xyz; vOcclusion = aExtra.x; vCloth = aExtra.y;
  // the two strongest regions' colours, mixed by how much of the first (soft edges between regions)
  vTint = mix(uTint[int(aRegion.y + 0.5)], uTint[int(aRegion.x + 0.5)], aRegion.z / 255.0);
  vWorld = uTurn * (p + aNormal.xyz * uOutline);  // the outline pass draws the back faces a little bigger
  gl_Position = uCamera * vec4(vWorld, 1.0);
}`;
// drawn like a cartoon: soft flat tones (shadow, light, a highlight), shadows a little cool; the region tints are the
// surface colour. The same program draws the outline (uOutline > 0) and the muscle lines (uOutline < 0)
const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec3 vNormal, vWorld; varying float vCloth, vY, vOcclusion; varying vec4 vTint;
uniform vec3 uEye, uSkin, uShorts, uLineColor; uniform float uWaist, uHem, uRim, uOutline;
void main() {
  if (uOutline > 0.0) { gl_FragColor = vec4(uLineColor, 1.0); return; }
  if (uOutline < 0.0) { gl_FragColor = vec4(uLineColor, 0.72); return; }  // a muscle line, laid over the skin
  vec4 tint = vTint;
  vec3 n = normalize(vNormal);
  if (!gl_FrontFacing) n = -n;
  vec3 v = normalize(uEye - vWorld);
  float cloth = smoothstep(0.35, 0.65, vCloth);
  float shorts = cloth * smoothstep(uHem - 0.004, uHem + 0.004, vY) * (1.0 - smoothstep(uWaist - 0.004, uWaist + 0.004, vY));
  float band = shorts * smoothstep(uWaist - 0.040, uWaist - 0.036, vY);
  vec3 surface = mix(uSkin, uShorts, shorts) * (1.0 - 0.12 * band);
  surface = surface * (1.0 - tint.a) + tint.rgb;
  float ndl = dot(n, normalize(vec3(-0.5, 0.9, 0.7)));
  float lit = smoothstep(-0.12, 0.30, ndl), top = smoothstep(0.55, 0.75, ndl);
  float shade = (mix(0.76, 0.93, lit) + 0.06 * top) * mix(0.86, 1.0, vOcclusion);
  vec3 color = surface * shade * mix(vec3(0.92, 0.95, 1.02), vec3(1.0), lit);
  color += pow(1.0 - max(dot(n, v), 0.0), 3.0) * uRim;
  gl_FragColor = vec4(min(color, vec3(1.0)), 1.0);
}`;

function compile(gl, regions) {
  const shader = (type, source) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, source); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s) || "Shader failed");
    return s;
  };
  const program = gl.createProgram();
  gl.attachShader(program, shader(gl.VERTEX_SHADER, VERTEX.replace("REGIONS", String(regions))));
  gl.attachShader(program, shader(gl.FRAGMENT_SHADER, FRAGMENT));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program) || "Link failed");
  return program;
}

// a CSS colour (any syntax the browser knows) as sRGB 0..1 and its alpha
const swatch = document.createElement("canvas");
swatch.width = swatch.height = 1;
function rgba(css) {
  const c = swatch.getContext("2d", { willReadFrequently: true });
  c.clearRect(0, 0, 1, 1); c.fillStyle = "#000"; c.fillStyle = css || "#000"; c.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = c.getImageData(0, 0, 1, 1).data;
  return [r / 255, g / 255, b / 255, a / 255];
}

export async function mountBody(host, { regions, levels, known, trained, onSelect, onUnsupported }) {
  let disposed = false, resize, appearance, frame = 0, gl, lose;
  const cleanup = [];
  const detach = new MutationObserver(() => { if (!host.isConnected) dispose(); });
  detach.observe(host.closest("main") || document.body, { childList: true });
  function dispose() {
    if (disposed) return;
    disposed = true; cancelAnimationFrame(frame); detach.disconnect(); resize?.disconnect(); appearance?.disconnect();
    cleanup.forEach(fn => fn());
    lose?.loseContext();
  }
  try {
    const body = await loadAsset();
    if (disposed || !host.isConnected) { dispose(); return null; }
    const canvas = document.createElement("canvas");
    gl = canvas.getContext("webgl", { antialias: true, alpha: true, premultipliedAlpha: true });
    if (!gl) throw Error("WebGL unavailable");
    lose = gl.getExtension("WEBGL_lose_context");
    canvas.tabIndex = 0; canvas.setAttribute("role", "img");
    const badge = document.createElement("span"); badge.className = "ov-angle-label"; badge.setAttribute("aria-live", "polite");
    const pin = document.createElement("span"); pin.className = "ov-body-pin"; pin.hidden = true;
    const floor = document.createElement("span"); floor.className = "ov-body-floor";
    const label = document.createElement("span"); label.className = "ov-body-label"; label.hidden = true;
    host.replaceChildren(floor, canvas, badge, pin, label);
    const H = body.header, R = H.regions;

    let program, loc, bindBody, bindLines;
    function setup() {
      program = compile(gl, R.length);
      gl.useProgram(program);
      loc = Object.fromEntries(["uCenter", "uExtent", "uTurn", "uCamera", "uTint", "uEye", "uSkin", "uShorts", "uWaist", "uHem", "uRim", "uOutline", "uLineColor"]
        .map(name => [name, gl.getUniformLocation(program, name)]));
      const buffer = (data, target = gl.ARRAY_BUFFER) => { const b = gl.createBuffer(); gl.bindBuffer(target, b); gl.bufferData(target, data, gl.STATIC_DRAW); return b; };
      const at = Object.fromEntries(["aPos", "aNormal", "aExtra", "aRegion"].map(name => [name, gl.getAttribLocation(program, name)]));
      const own = { pos: buffer(body.quant), normal: buffer(body.normals), extra: buffer(body.extra), shares: buffer(body.shares),
        index: buffer(body.indices, gl.ELEMENT_ARRAY_BUFFER) };
      const ink = body.lines && { pos: buffer(body.lines.quant), index: buffer(body.lines.indices, gl.ELEMENT_ARRAY_BUFFER) };
      const point = (name, b, size, type, normalized = true) => {
        gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(at[name]); gl.vertexAttribPointer(at[name], size, type, normalized, 0, 0);
      };
      bindBody = () => {
        point("aPos", own.pos, 3, gl.SHORT); point("aNormal", own.normal, 4, gl.BYTE); point("aExtra", own.extra, 4, gl.UNSIGNED_BYTE);
        point("aRegion", own.shares, 4, gl.UNSIGNED_BYTE, false);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, own.index);
      };
      bindLines = ink && (() => {  // only positions; the rest held constant
        point("aPos", ink.pos, 3, gl.SHORT);
        for (const name of ["aNormal", "aExtra", "aRegion"]) { gl.disableVertexAttribArray(at[name]); gl.vertexAttrib4f(at[name], 0, 0, 0, 0); }
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ink.index);
      });
      gl.uniform3fv(loc.uCenter, H.center); gl.uniform3fv(loc.uExtent, H.extent);
      gl.uniform1f(loc.uWaist, H.shorts.waist); gl.uniform1f(loc.uHem, H.shorts.hem);
      gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.clearColor(0, 0, 0, 0);
    }
    setup();
    const lost = event => { event.preventDefault(); cancelAnimationFrame(frame); frame = 0; };
    const restored = () => { setup(); paint(); };
    canvas.addEventListener("webglcontextlost", lost); canvas.addEventListener("webglcontextrestored", restored);
    cleanup.push(() => { canvas.removeEventListener("webglcontextlost", lost); canvas.removeEventListener("webglcontextrestored", restored); });

    let knownRegions = null, annotations = {}, view = "sore", selected = "", colors = null;
    let yaw = 0, spin = 0, tween = null, last = 0, chosen = null;  // chosen: the point tapped, kept while its region stays selected
    let camera = { eye: [0, 0, 1], width: 0, height: 0, tan: Math.tan(FOV / 2) };
    // how far back the camera stands so the whole body fits at every angle, the same size all the way round: its
    // height with 8 px above and below, its widest turn with a little air at the sides
    const fit = (width, height) => {
      const P = body.positions, cy = H.center[1], up = camera.tan * (1 - 16 / height), across = camera.tan * width / height * 0.92;
      let d = 0;
      for (let i = 0; i < P.length; i += 3) {
        const r = Math.hypot(P[i], P[i + 2]);
        d = Math.max(d, Math.abs(P[i + 1] - cy) / up + r, r / across + r);
      }
      return d;
    };
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    const readColors = () => {
      const style = getComputedStyle(host), v = name => style.getPropertyValue(name).trim();
      const [r, g, b] = rgba(v("--surface"));
      colors = { axis: rgba(v("--c-axis")), trained: rgba(v("--c-exercise")), sore: [1, 2, 3].map(i => rgba(v(`--c-sore-${i}`))),
        look: LOOK[0.2126 * r + 0.7152 * g + 0.0722 * b < 0.4 ? "dark" : "light"] };
    };
    const turn = () => { const c = Math.cos(yaw), s = Math.sin(yaw); return [c, 0, -s, 0, 1, 0, s, 0, c]; };
    // body coordinates -> the room, and back
    const toRoom = (p, m = turn()) => [m[0] * p[0] + m[3] * p[1] + m[6] * p[2], m[1] * p[0] + m[4] * p[1] + m[7] * p[2], m[2] * p[0] + m[5] * p[1] + m[8] * p[2]];
    const toBody = (p, m = turn()) => [m[0] * p[0] + m[1] * p[1] + m[2] * p[2], m[3] * p[0] + m[4] * p[1] + m[5] * p[2], m[6] * p[0] + m[7] * p[1] + m[8] * p[2]];
    const ray = (x, y) => {  // CSS pixels in the canvas -> a ray in the room
      const nx = x / camera.width * 2 - 1, ny = 1 - y / camera.height * 2;
      const d = [nx * camera.tan * camera.width / camera.height, ny * camera.tan, -1], l = Math.hypot(...d);
      return d.map(c => c / l);
    };
    const project = p => {  // a point in the room -> CSS pixels, or null behind the camera
      const z = camera.eye[2] - p[2];
      if (z <= 0) return null;
      return [(p[0] / (z * camera.tan * camera.width / camera.height) + 1) / 2 * camera.width,
        (1 - (p[1] - camera.eye[1]) / (z * camera.tan)) / 2 * camera.height];
    };
    const shown = (point, normal) => {  // faces the camera and nothing of the body is in front of it
      const room = toRoom(point), to = camera.eye.map((c, i) => c - room[i]), dist = Math.hypot(...to);
      if (toRoom(normal).reduce((s, c, i) => s + c * to[i], 0) / dist < 0.08) return false;
      const hit = raycast(body, toBody(camera.eye), toBody(to.map(c => -c / dist)));
      return !hit || hit.d > dist - 0.012;
    };
    const tint = region => {
      if (!regions.includes(region)) return [0, 0, 0, 0];
      const value = view === "trained" ? (trained.has(region) ? "trained" : null) : known && (!knownRegions || knownRegions.includes(region)) ? (levels[region] || 0) : null;
      if (value === 0) return [0, 0, 0, 0];  // a recorded zero keeps the neutral grey
      const [r, g, b, a] = value == null ? colors.axis : value === "trained" ? colors.trained : colors.sore[value - 1];
      const alpha = a * (value == null ? 0.28 : value === "trained" ? 0.6 : [0, 0.42, 0.66, 0.85][value]);
      return [r * alpha, g * alpha, b * alpha, alpha];
    };

    function draw(now) {
      frame = 0;
      if (disposed || !host.isConnected || gl.isContextLost()) return;
      const dt = last ? Math.min(now - last, 64) : 16;
      last = now;
      if (tween) {
        const k = Math.min(1, (now - tween.start) / tween.ms), ease = 1 - (1 - k) ** 3;
        yaw = tween.from + (tween.to - tween.from) * ease;
        if (k >= 1) tween = null;
      } else if (spin) {
        yaw += spin * dt; spin *= Math.exp(-dt / 260);
        if (Math.abs(spin) < 0.00004) spin = 0;
      }
      const { width, height } = host.getBoundingClientRect();
      if (width < 1 || height < 1) return;
      const dpr = Math.min(devicePixelRatio || 1, 2), w = Math.round(width * dpr), h = Math.round(height * dpr);
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      if (camera.width !== width || camera.height !== height) camera = { ...camera, width, height, eye: [0, H.center[1], fit(width, height)] };
      const aspect = width / height, distance = camera.eye[2], f = 1 / camera.tan;
      const near = distance - body.radius - 0.1, far = distance + body.radius + 0.1;
      const a = (far + near) / (near - far), b = 2 * far * near / (near - far);
      // perspective x the camera's offset (0, -centre, -distance); column-major
      gl.uniformMatrix4fv(loc.uCamera, false, [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, a, -1,
        0, -H.center[1] * f, -distance * a + b, distance]);
      gl.uniformMatrix3fv(loc.uTurn, false, turn());
      gl.uniform3fv(loc.uEye, camera.eye);
      gl.uniform4fv(loc.uTint, R.flatMap(tint));
      gl.uniform3fv(loc.uSkin, colors.look.skin); gl.uniform3fv(loc.uShorts, colors.look.shorts); gl.uniform1f(loc.uRim, colors.look.rim);
      gl.viewport(0, 0, w, h);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      // the outline: the back faces pushed out by a pixel and a half, then the body over them
      gl.uniform3fv(loc.uLineColor, colors.look.outline);
      bindBody();
      gl.cullFace(gl.FRONT); gl.uniform1f(loc.uOutline, OUTLINE * 2 * camera.tan * distance / height);
      gl.drawElements(gl.TRIANGLES, body.indices.length, gl.UNSIGNED_SHORT, 0);
      gl.cullFace(gl.BACK); gl.uniform1f(loc.uOutline, 0);
      gl.drawElements(gl.TRIANGLES, body.indices.length, gl.UNSIGNED_SHORT, 0);
      if (bindLines) {  // the muscle lines over the skin, a touch transparent, nudged towards the camera
        bindLines();
        gl.uniform3fv(loc.uLineColor, colors.look.ink); gl.uniform1f(loc.uOutline, -1);
        gl.disable(gl.CULL_FACE); gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE);
        gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(-2, -2);
        gl.drawElements(gl.TRIANGLES, body.lines.indices.length, gl.UNSIGNED_SHORT, 0);
        gl.disable(gl.POLYGON_OFFSET_FILL); gl.disable(gl.BLEND); gl.enable(gl.CULL_FACE);
      }

      const ground = project([0, 0, 0]), side = project([0.3, 0, 0]);
      if (ground && side) {
        floor.style.left = `${ground[0]}px`; floor.style.top = `${ground[1]}px`; floor.style.width = `${(side[0] - ground[0]) * 2}px`;
      }
      const index = viewIndex(yaw);
      if (badge.textContent !== rv(VIEWS[index])) {
        badge.textContent = rv(VIEWS[index]);
        canvas.setAttribute("aria-label", `${rv("bodyAria")} ${rv(VIEWS[index])}`);
      }
      // the marker: the tapped point while it shows, else the region's point that faces you most
      let mark = null;
      if (selected && H.anchors[selected]) {
        const m = turn();
        const facing = H.anchors[selected].map(a => ({ point: a.slice(0, 3), normal: a.slice(3) }))
          .sort((p, q) => toRoom(q.normal, m)[2] - toRoom(p.normal, m)[2]).slice(0, 3);
        const candidates = chosen?.region === selected ? [chosen, ...facing] : facing;
        mark = candidates.find(c => shown(c.point, c.normal)) || null;
      }
      const at = mark && project(toRoom(mark.point));
      pin.hidden = label.hidden = !at;
      if (at) {
        const [x, y] = at;
        pin.style.left = `${x}px`; pin.style.top = `${y}px`;
        const value = known ? t(`sore.level.${levels[selected] || 0}`) : rv("unknown");
        label.textContent = view === "sore" && annotations[selected] ? annotations[selected] : `${t(`sore.region.${selected}`)} · ${view === "trained" ? (trained.has(selected) ? rv("trainingLegend") : rv("unknown")) : value}`;
        label.style.left = `${Math.max(6, Math.min(width - 150, x + 14))}px`;
        label.style.top = `${Math.max(6, y - 38)}px`;
      }
      if (tween || spin) paint(); else last = 0;
    }
    const paint = () => { if (!disposed && !frame) frame = requestAnimationFrame(draw); };
    const turnTo = target => {
      spin = 0;
      if (motion.matches) { yaw = target; tween = null; } else tween = { from: yaw, to: target, start: performance.now(), ms: 480 };
      paint();
    };
    const rotate = step => turnTo(Math.round((tween ? tween.to : yaw) / QUARTER + Math.sign(step)) * QUARTER);
    readColors();
    resize = new ResizeObserver(paint); resize.observe(host);
    const restyle = () => { readColors(); paint(); };
    appearance = new MutationObserver(restyle); appearance.observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode", "class"] });
    const media = matchMedia("(prefers-color-scheme: dark)"); media.addEventListener("change", restyle);
    cleanup.push(() => media.removeEventListener("change", restyle));

    let drag;
    canvas.onpointerdown = event => {
      if (!event.isPrimary || event.button !== 0) return;
      tween = null; spin = 0;
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, yaw, moved: false, at: event.timeStamp, speed: 0 };
      canvas.setPointerCapture(event.pointerId);
    };
    canvas.onpointermove = event => {
      if (drag?.id !== event.pointerId) return;
      const dx = event.clientX - drag.x;
      if (!drag.moved && Math.hypot(dx, event.clientY - drag.y) > 6) drag.moved = true;
      if (!drag.moved) return;
      const next = drag.yaw + dx * DRAG, gap = Math.max(1, event.timeStamp - drag.at);
      drag.speed = 0.6 * drag.speed + 0.4 * (next - yaw) / gap;  // radians per millisecond, smoothed
      drag.at = event.timeStamp; yaw = next; paint();
    };
    canvas.onpointercancel = () => { drag = null; };
    canvas.onpointerup = event => {
      if (!drag || event.pointerId !== drag.id) return;
      const { x, y, moved, speed, at } = drag; drag = null;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      if (moved) {  // let it run on a little, unless the finger stopped before letting go
        if (!motion.matches && event.timeStamp - at < 80) { spin = Math.max(-0.006, Math.min(0.006, speed)); last = 0; paint(); }
        return;
      }
      const rect = canvas.getBoundingClientRect(), dir = ray(x - rect.left, y - rect.top);
      const hit = raycast(body, toBody(camera.eye), toBody(dir));
      if (!hit) return;
      const I = body.indices, S = body.shares, P = body.positions, w = [1 - hit.u - hit.v, hit.u, hit.v];
      const share = R.map(() => 0);
      w.forEach((wk, j) => {  // each corner's two regions, by how much of each
        const v = I[hit.k + j] * 4, first = S[v + 2] / 255;
        share[S[v]] += wk * first; share[S[v + 1]] += wk * (1 - first);
      });
      const region = R[share.indexOf(Math.max(...share))];
      if (region !== "other" && regions.includes(region)) {
        const point = [0, 1, 2].map(c => w.reduce((s, wk, j) => s + wk * P[I[hit.k + j] * 3 + c], 0));
        const e1 = [0, 1, 2].map(c => P[I[hit.k + 1] * 3 + c] - P[I[hit.k] * 3 + c]), e2 = [0, 1, 2].map(c => P[I[hit.k + 2] * 3 + c] - P[I[hit.k] * 3 + c]);
        let normal = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
        const toEye = toBody(camera.eye).map((c, i) => c - point[i]);
        const length = Math.hypot(...normal) * (normal.reduce((s, c, i) => s + c * toEye[i], 0) < 0 ? -1 : 1);
        normal = normal.map(c => c / length);
        chosen = { region, point, normal };
        onSelect(region);
      } else onUnsupported();
    };
    canvas.onkeydown = event => {
      if (["ArrowLeft", "ArrowRight"].includes(event.key)) { event.preventDefault(); rotate(event.key === "ArrowLeft" ? -1 : 1); }
    };
    cleanup.push(() => { canvas.onpointerdown = canvas.onpointermove = canvas.onpointerup = canvas.onpointercancel = canvas.onkeydown = null; });
    paint();
    return {
      rotate,
      reset() { turnTo(Math.round(yaw / TURN) * TURN); },
      update(next) {
        levels = next.levels; known = next.known; knownRegions = next.knownRegions; annotations = next.annotations || {}; view = next.view; selected = next.selected;
        if (chosen?.region !== selected) chosen = null;
        paint();
      },
      dispose,
    };
  } catch {
    dispose();
    if (host.isConnected) host.innerHTML = `<p class="ov-model-message">${rv("fallback")}</p>`;
    return null;
  }
}
