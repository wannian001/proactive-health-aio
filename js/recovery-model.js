// BodyParts3D surface, locally hosted. Broad hit areas match the existing check-in schema.
// This is not per-muscle evidence; unsupported regions deliberately remain unclassified.
import { rv } from "./recovery-copy.js?v=11473b41ff";

export function regionAt(x, y) {
  const side = x >= 0 ? "left" : "right";
  if (y > 1.455) return "head";
  if (Math.abs(x) > .185 && y > 1.08 && y < 1.44) return `${side}_upper_arm`;
  if (y > .085 && y < .53 && Math.abs(x) > .035) return `${side}_calf`;
  if (y >= .77 && y < .98 && Math.abs(x) < .19) return "pelvis";
  if (y >= .98 && y < 1.455 && Math.abs(x) <= .185) return "torso";
  return null;
}

let assets;
async function loadAssets() {
  if (!assets) assets = Promise.all([
    import("../vendor/three/three.module.min.js"),
    fetch(new URL("../models/recovery/body.json", import.meta.url)).then(r => { if (!r.ok) throw Error("model metadata"); return r.json(); }),
    fetch(new URL("../models/recovery/body.bin", import.meta.url)).then(r => { if (!r.ok) throw Error("model geometry"); return r.arrayBuffer(); }),
  ]).catch(error => { assets = null; throw error; });
  return assets;
}

export async function mountBody(host, { regions, levels, known, trained, onSelect, onUnsupported }) {
  let disposed = false, renderer, resize, appearance, frame = 0;
  const detach = new MutationObserver(() => { if (!host.isConnected) dispose(); });
  detach.observe(host.closest("main") || document.body, { childList: true });
  const cleanup = [];
  function dispose() {
    if (disposed) return;
    disposed = true; cancelAnimationFrame(frame); detach.disconnect(); resize?.disconnect(); appearance?.disconnect();
    cleanup.forEach(fn => fn()); renderer?.dispose(); renderer?.forceContextLoss();
  }
  try {
    const [T, meta, buffer] = await loadAssets();
    if (disposed || !host.isConnected) { dispose(); return null; }
    const scene = new T.Scene();
    const camera = new T.OrthographicCamera(-.7, .7, .96, -.96, .1, 10);
    camera.position.set(0, .86, 3); camera.lookAt(0, .86, 0);
    renderer = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setClearColor(0, 0);
    renderer.outputColorSpace = T.SRGBColorSpace;
    const canvas = renderer.domElement;
    canvas.tabIndex = 0; canvas.setAttribute("role", "img"); canvas.setAttribute("aria-label", rv("bodyAria"));
    scene.add(new T.HemisphereLight(0xffffff, 0x8e919a, 2.3));
    const light = new T.DirectionalLight(0xffffff, 2.4); light.position.set(-2, 3, 4); scene.add(light);
    const edge = new T.DirectionalLight(0xe3eaff, 1.2); edge.position.set(2, 2, -2); scene.add(edge);
    const geometry = new T.BufferGeometry();
    const positions = new Float32Array(buffer, meta.positions, meta.vertexCount * 3);
    geometry.setAttribute("position", new T.BufferAttribute(positions, 3));
    geometry.setAttribute("normal", new T.BufferAttribute(new Int16Array(buffer, meta.normals, meta.vertexCount * 3), 3, true));
    const source = new Uint32Array(buffer, meta.indices, meta.indexCount);
    const keys = [...regions, null], buckets = keys.map(() => []);
    for (let i = 0; i < source.length; i += 3) {
      const [a, b, c] = [source[i] * 3, source[i + 1] * 3, source[i + 2] * 3];
      const region = regionAt((positions[a] + positions[b] + positions[c]) / 3, (positions[a + 1] + positions[b + 1] + positions[c + 1]) / 3);
      buckets[keys.indexOf(region)].push(source[i], source[i + 1], source[i + 2]);
    }
    const index = new Uint32Array(source.length);
    let offset = 0;
    buckets.forEach((indices, i) => { index.set(indices, offset); geometry.addGroup(offset, indices.length, i); offset += indices.length; });
    geometry.setIndex(new T.BufferAttribute(index, 1)); geometry.computeBoundingSphere();
    const materials = keys.map(() => new T.MeshStandardMaterial({ color: 0xc6c9cd, roughness: .76, metalness: .02, side: T.DoubleSide }));
    const body = new T.Mesh(geometry, materials); scene.add(body);
    const marker = new T.Mesh(new T.SphereGeometry(.011, 16, 12), new T.MeshBasicMaterial({ color: 0x3174bb, depthTest: false }));
    marker.renderOrder = 2; marker.visible = false; body.add(marker);
    let view = "sore", selected = null;
    const requestRender = () => { if (!disposed && !frame) frame = requestAnimationFrame(() => { frame = 0; if (!disposed) renderer.render(scene, camera); }); };
    const paint = () => {
      const style = getComputedStyle(host);
      keys.forEach((key, i) => {
        const value = key == null ? null : view === "trained" ? (trained.has(key) ? "trained" : null) : known ? (levels[key] || 0) : null;
        const token = value === "trained" ? "--c-exercise" : value == null ? "--ov-body-unknown" : `--ov-sore-${value}`;
        materials[i].color.set(style.getPropertyValue(token).trim() || "#c4c7cc");
      });
      requestRender();
    };
    const fit = () => {
      if (!host.isConnected) { dispose(); return; }
      const { width, height } = host.getBoundingClientRect();
      if (width < 1 || height < 1) return;
      const aspect = width / height, halfHeight = Math.max(.95, .39 / aspect);
      camera.left = -halfHeight * aspect; camera.right = halfHeight * aspect;
      camera.top = halfHeight; camera.bottom = -halfHeight; camera.updateProjectionMatrix();
      renderer.setSize(width, height, false); requestRender();
    };
    host.replaceChildren(canvas);
    resize = new ResizeObserver(fit); resize.observe(host);
    appearance = new MutationObserver(paint); appearance.observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode", "class"] });
    const media = matchMedia("(prefers-color-scheme: dark)"); media.addEventListener("change", paint);
    cleanup.push(() => media.removeEventListener("change", paint), () => geometry.dispose(), () => materials.forEach(m => m.dispose()), () => marker.geometry.dispose(), () => marker.material.dispose());
    const rotate = delta => { body.rotation.y += delta; requestRender(); };
    const ray = new T.Raycaster(), pointer = new T.Vector2();
    let drag = null;
    canvas.onpointerdown = event => { if (!event.isPrimary || event.button !== 0) return; drag = { id: event.pointerId, x: event.clientX, y: event.clientY, last: event.clientX, moved: false }; canvas.setPointerCapture(event.pointerId); };
    canvas.onpointermove = event => {
      if (!drag || event.pointerId !== drag.id) return;
      if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 6) drag.moved = true;
      if (drag.moved && Math.abs(event.clientX - drag.x) > Math.abs(event.clientY - drag.y)) rotate((event.clientX - drag.last) * .012);
      drag.last = event.clientX;
    };
    canvas.onpointercancel = () => { drag = null; };
    canvas.onpointerup = event => {
      if (!drag || event.pointerId !== drag.id) return;
      const clicked = !drag.moved; drag = null;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      if (!clicked) return;
      const box = canvas.getBoundingClientRect(); pointer.set((event.clientX - box.left) / box.width * 2 - 1, 1 - (event.clientY - box.top) / box.height * 2);
      scene.updateMatrixWorld(true); camera.updateMatrixWorld(true); ray.setFromCamera(pointer, camera);
      const hit = ray.intersectObject(body, false)[0];
      if (!hit) return;
      const region = keys[hit.face.materialIndex];
      if (!region) { onUnsupported(); return; }
      selected = region; marker.position.copy(body.worldToLocal(hit.point.clone())); marker.visible = true; requestRender(); onSelect(region);
    };
    canvas.onkeydown = event => { if (["ArrowLeft", "ArrowRight"].includes(event.key)) { event.preventDefault(); rotate(event.key === "ArrowLeft" ? -.25 : .25); } };
    canvas.addEventListener("webglcontextlost", event => { event.preventDefault(); dispose(); host.innerHTML = `<p class="ov-model-message">${rv("fallback")}</p>`; });
    paint(); fit();
    return {
      rotate,
      reset() { body.rotation.y = 0; requestRender(); },
      update(next) { levels = next.levels; known = next.known; view = next.view; if (selected !== next.selected) marker.visible = false; selected = next.selected; paint(); },
      dispose,
    };
  } catch {
    dispose();
    if (host.isConnected) host.innerHTML = `<p class="ov-model-message">${rv("fallback")}</p>`;
    return null;
  }
}
