// The 3D map: Europe as a field of dots, one light column per provider site.
//
// Price mode:   column height = cheapest on-demand price per GPU-hour at that site
//               for the selected GPU; a hollow ring = the provider has no public
//               listing for that GPU (the capacity gap, made visible).
// Control mode: an arc from every site to the place that legally controls it.
//               Sovereign sites stay inside Europe; US-controlled sites all fly to
//               one point beyond the Atlantic.
//
// Projection: Lambert azimuthal equal-area on 52N 10E (EPSG:3035, spherical),
// the same formula as scripts/make_geo.py, in thousands of km.

import * as THREE from "../vendor/three.module.min.js";
import { cssVar, reducedMotion, isDark, eur, el } from "./format.js";

const R = 6371.0072;
const LAT0 = (52 * Math.PI) / 180;
const LON0 = (10 * Math.PI) / 180;
export const LUGANO = { lat: 46.0037, lon: 8.9511 };
export const US_ANCHOR = { lat: 49, lon: -36 }; // drawn point for "US jurisdiction"

export function laea(lon, lat) {
  const lam = (lon * Math.PI) / 180, phi = (lat * Math.PI) / 180;
  const d = lam - LON0;
  const k = Math.sqrt(2 / (1 + Math.sin(LAT0) * Math.sin(phi) + Math.cos(LAT0) * Math.cos(phi) * Math.cos(d)));
  return [R * k * Math.cos(phi) * Math.sin(d), R * k * (Math.cos(LAT0) * Math.sin(phi) - Math.sin(LAT0) * Math.cos(phi) * Math.cos(d))];
}
const toWorld = (xKm, yKm) => new THREE.Vector3(xKm / 1000, 0, -yKm / 1000);
const geo = (lat, lon) => toWorld(...laea(lon, lat));

function glowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, "rgba(255,255,255,1)");
  grd.addColorStop(0.25, "rgba(255,255,255,0.55)");
  grd.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const DOT_VERT = `
  attribute vec3 color; attribute float group;
  varying vec3 vColor; varying float vGroup;
  uniform float uSize; uniform float uPixelRatio;
  void main() {
    vColor = color; vGroup = group;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = uSize * uPixelRatio * (group > 2.5 ? 1.5 : 1.0) * (7.0 / -mv.z);
    gl_Position = projectionMatrix * mv;
  }`;
const DOT_FRAG = `
  varying vec3 vColor; varying float vGroup;
  void main() {
    vec2 p = gl_PointCoord - 0.5;
    float d = length(p);
    if (d > 0.5) discard;
    float a = 1.0 - smoothstep(0.32, 0.5, d);
    gl_FragColor = vec4(vColor, a);
  }`;
const ARC_VERT = `
  varying float vT;
  void main() { vT = uv.x; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const ARC_FRAG = `
  uniform vec3 uColor; uniform float uTime; uniform float uReveal; uniform float uOpacity;
  varying float vT;
  void main() {
    if (vT > uReveal) discard;
    float pulse = smoothstep(0.0, 0.12, fract(vT * 2.0 - uTime * 0.35)) * (1.0 - smoothstep(0.12, 0.3, fract(vT * 2.0 - uTime * 0.35)));
    float a = (0.35 + 0.65 * pulse) * uOpacity * smoothstep(0.0, 0.04, vT);
    gl_FragColor = vec4(uColor, a);
  }`;

export function createMap(host, { dots, sites, labelsHost, tipHost }) {
  const canvas = document.createElement("canvas");
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  } catch (e) {
    host.append(el("div", { class: "map-fallback" }, "This map needs WebGL, which your browser has turned off. Every number on it is also in the tables below."));
    return null;
  }
  host.append(canvas);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 100);
  const target = new THREE.Vector3(wideTarget(), 0, -0.45);
  // On wide screens the copy sits over the left of the map, so aim the camera further west.
  function wideTarget() { return host.clientWidth / Math.max(host.clientHeight, 1) > 1.3 ? -0.6 : 0.3; }
  const view = { az: -0.06, polar: 0.98, dist: 7.6, az0: -0.06, polar0: 0.98 };
  const motion = !reducedMotion();

  // ---- palette from CSS tokens
  const palette = {};
  function readPalette() {
    for (const k of ["sov", "for", "rev", "dot-eu", "dot-out", "dot-ch", "ink"]) palette[k] = new THREE.Color(cssVar("--" + k) || "#888");
  }
  readPalette();

  // ---- dots
  const pts = dots.points;
  const n = pts.length / 3;
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), grp = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const v = toWorld(pts[i * 3], pts[i * 3 + 1]);
    pos.set([v.x, 0, v.z], i * 3);
    grp[i] = pts[i * 3 + 2];
  }
  const dotGeo = new THREE.BufferGeometry();
  dotGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  dotGeo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  dotGeo.setAttribute("group", new THREE.BufferAttribute(grp, 1));
  const dotMat = new THREE.ShaderMaterial({
    vertexShader: DOT_VERT, fragmentShader: DOT_FRAG, transparent: true, depthWrite: false,
    uniforms: { uSize: { value: 4.4 }, uPixelRatio: { value: renderer.getPixelRatio() } },
  });
  scene.add(new THREE.Points(dotGeo, dotMat));
  function paintDots() {
    const out = palette["dot-out"], eu = palette["dot-eu"], ch = palette["dot-ch"];
    const mid = out.clone().lerp(eu, 0.45);
    for (let i = 0; i < n; i++) {
      const g = grp[i];
      const c = g === 3 ? ch : g === 2 ? eu : g === 1 ? mid : out;
      col.set([c.r, c.g, c.b], i * 3);
    }
    dotGeo.attributes.color.needsUpdate = true;
  }
  paintDots();
  dotMat.uniforms.uSize.value = isDark() ? 4.4 : 3.4;

  // ---- sites
  const glow = glowTexture();
  const colGeo = new THREE.CylinderGeometry(1, 1, 1, 12, 1, true).translate(0, 0.5, 0);
  const ringGeo = new THREE.RingGeometry(0.026, 0.034, 32).rotateX(-Math.PI / 2);
  const hitGeo = new THREE.CylinderGeometry(1, 1, 1, 6).translate(0, 0.5, 0);
  const siteGroup = new THREE.Group();
  const arcGroup = new THREE.Group();
  scene.add(siteGroup, arcGroup);
  const hitTargets = [];
  let items = [];
  const lugano = geo(LUGANO.lat, LUGANO.lon);
  const usAnchor = geo(US_ANCHOR.lat, US_ANCHOR.lon);

  // Spread providers that share a city around that city, deterministically.
  function placeSites(list) {
    const byCity = new Map();
    for (const s of list) {
      const key = `${Math.round(s.site.lat * 4)}:${Math.round(s.site.lon * 4)}`;
      if (!byCity.has(key)) byCity.set(key, []);
      byCity.get(key).push(s);
    }
    for (const group of byCity.values()) {
      group.sort((a, b) => a.provider.localeCompare(b.provider));
      group.forEach((s, i) => {
        const base = geo(s.site.lat, s.site.lon);
        if (group.length > 1) {
          const ang = (i / group.length) * Math.PI * 2 + 0.6;
          base.x += Math.cos(ang) * 0.055;
          base.z += Math.sin(ang) * 0.055;
        }
        s.pos = base;
      });
    }
  }

  const colorFor = (status) => (status === "sovereign" ? palette.sov : status === "non_sovereign" ? palette.for : palette.rev);
  let maxPrice = 1;

  function buildSites(list) {
    siteGroup.clear();
    arcGroup.clear();
    hitTargets.length = 0;
    placeSites(list);
    maxPrice = Math.max(4, ...list.map((s) => s.price || 0));
    items = list.map((s) => {
      const color = colorFor(s.status);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.92, depthWrite: false });
      const column = new THREE.Mesh(colGeo, mat);
      column.position.copy(s.pos);
      const ringMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: s.price ? 0.9 : 0.75, side: THREE.DoubleSide, depthWrite: false });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(s.pos).setY(0.002);
      const spriteMat = new THREE.SpriteMaterial({ map: glow, color, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
      const sprite = new THREE.Sprite(spriteMat);
      const hit = new THREE.Mesh(hitGeo, new THREE.MeshBasicMaterial({ visible: false }));
      hit.position.copy(s.pos);
      hit.userData.item = s;
      hitTargets.push(hit);
      siteGroup.add(column, ring, sprite, hit);
      const height = s.price ? 0.08 + (s.price / maxPrice) * 0.95 : 0;
      const delay = motion ? s.pos.distanceTo(lugano) * 0.16 : 0; // ripple out from Lugano
      // Arc to the controlling jurisdiction.
      const end = s.status === "non_sovereign" && s.hqCountry === "US" ? usAnchor : geo(s.hq.lat, s.hq.lon);
      const dist = s.pos.distanceTo(end);
      let arc = null;
      if (dist > 0.03) {
        const mid = s.pos.clone().lerp(end, 0.5).setY(0.15 + dist * 0.32);
        const curve = new THREE.QuadraticBezierCurve3(s.pos.clone().setY(0.01), mid, end.clone().setY(0.01));
        const tube = new THREE.TubeGeometry(curve, 64, s.status === "non_sovereign" ? 0.0055 : 0.0045, 5, false);
        const arcMat = new THREE.ShaderMaterial({
          vertexShader: ARC_VERT, fragmentShader: ARC_FRAG, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
          uniforms: { uColor: { value: color.clone() }, uTime: { value: Math.random() * 4 }, uReveal: { value: 0 }, uOpacity: { value: 0 } },
        });
        arc = new THREE.Mesh(tube, arcMat);
        arcGroup.add(arc);
      }
      return { s, column, ring, sprite, hit, height, delay, arc, mat, ringMat, spriteMat };
    });
  }

  // ---- labels (HTML, projected each frame)
  const labels = [];
  function addLabel(text, cls, world) {
    const node = el("span", { class: cls }, text);
    labelsHost.append(node);
    labels.push({ node, world, cls });
  }
  addLabel("Lugano", "lugano", lugano);
  addLabel("→ US jurisdiction · CLOUD Act", "us", usAnchor.clone().setY(0.02));

  // ---- state
  let mode = "price";
  let modeT = 0; // 0 = price, 1 = control (animated)
  let start = performance.now();
  let lastFrame = performance.now();
  let lastInteract = 0;
  let hovered = null;

  function setSites(list) {
    buildSites(list);
    start = performance.now();
  }
  function setMode(m) { mode = m; lastInteract = performance.now(); }

  // ---- camera
  function resize() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // Wider screens see more of Europe; narrow ones zoom to the core.
    view.dist = w / h > 1.3 ? 6.3 : w / h > 0.9 ? 7.6 : 9.6;
    camera.updateProjectionMatrix();
  }
  function placeCamera() {
    const sp = Math.sin(view.polar), cp = Math.cos(view.polar);
    camera.position.set(target.x + view.dist * sp * Math.sin(view.az), view.dist * cp, target.z + view.dist * sp * Math.cos(view.az));
    camera.lookAt(target);
  }

  // ---- interaction: drag to turn, no wheel capture (the page keeps scrolling)
  let drag = null;
  canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, az: view.az, polar: view.polar }; canvas.setPointerCapture(e.pointerId); lastInteract = performance.now(); });
  canvas.addEventListener("pointerup", (e) => { drag = null; canvas.releasePointerCapture(e.pointerId); });
  canvas.addEventListener("dblclick", () => { lastInteract = 0; view.polar = view.polar0; });
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  canvas.addEventListener("pointermove", (e) => {
    const r = canvas.getBoundingClientRect();
    if (drag) {
      view.az = Math.max(-0.8, Math.min(1.2, drag.az - (e.clientX - drag.x) * 0.005));
      view.polar = Math.max(0.5, Math.min(1.18, drag.polar - (e.clientY - drag.y) * 0.004));
      lastInteract = performance.now();
      return;
    }
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(hitTargets, false)[0];
    hovered = hit ? hit.object.userData.item : null;
    canvas.style.cursor = hovered ? "pointer" : "";
  });
  canvas.addEventListener("pointerleave", () => { hovered = null; });

  const tip = el("div", { class: "tip", hidden: true });
  tipHost.append(tip);
  function renderTip(item, screen) {
    if (!item) { tip.hidden = true; return; }
    const s = item;
    tip.innerHTML = "";
    tip.append(
      el("h4", {}, el("span", { class: "swatch " + s.status }), s.providerName),
      el("div", { class: "muted" }, `${s.site.label ? s.site.label + " · " : ""}${s.site.city}, ${s.site.country}`),
      el("div", { class: "row" }, s.gpuLabel + " on demand", el("b", {}, s.price ? eur(s.price) + " /GPU-h" : "no public listing")),
      s.priceScope ? el("div", { class: "row" }, "Price scope", el("b", {}, s.priceScope)) : null,
      el("div", { class: "row" }, "Controlled from", el("b", {}, s.hqLabel)),
    );
    tip.hidden = false;
    tip.style.left = screen.x + "px";
    tip.style.top = screen.y + "px";
  }

  // ---- loop
  const tmp = new THREE.Vector3();
  let visible = true;
  let running = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(host);
  document.addEventListener("visibilitychange", () => { running = !document.hidden; });
  function frame(now) {
    requestAnimationFrame(frame);
    if (!visible || !running) return;
    const t = (now - start) / 1000;
    const dt = Math.min((now - lastFrame) / 1000, 0.25);
    lastFrame = now;
    const k = motion ? 1 - Math.exp(-dt * 3.2) : 1; // time-based easing, frame-rate independent
    const goal = mode === "control" ? 1 : 0;
    modeT += (goal - modeT) * k;
    // In control mode the camera swings west, toward the Atlantic where US-controlled arcs land.
    const azHome = view.az0 + 0.5 * modeT;
    const tx = wideTarget() - 0.9 * modeT;
    target.x += (tx - target.x) * k;
    const idle = now - lastInteract > 5000;
    if (!drag && (idle || Math.abs(goal - modeT) > 0.01)) {
      const sway = motion && idle ? Math.sin(now / 9000) * 0.1 : 0;
      view.az += (azHome + sway - view.az) * k;
    }
    placeCamera();
    for (const it of items) {
      const grow = motion ? Math.min(1, Math.max(0, (t - it.delay) / 0.9)) : 1;
      const ease = 1 - Math.pow(1 - grow, 3);
      const hgt = Math.max(0.0001, it.height * ease * (1 - 0.82 * modeT));
      const isHover = hovered === it.s;
      const radius = (isHover ? 0.016 : 0.011) * (1 - 0.3 * modeT);
      it.column.scale.set(radius, hgt, radius);
      it.column.visible = it.height > 0;
      it.mat.opacity = 0.92 - 0.45 * modeT;
      it.sprite.position.copy(it.s.pos).setY(hgt + 0.002);
      const sz = (it.height > 0 ? 0.16 : 0.08) * (isHover ? 1.5 : 1) * (0.5 + 0.5 * ease);
      it.sprite.scale.set(sz, sz, 1);
      it.spriteMat.opacity = it.height > 0 ? 0.9 : 0.35;
      it.hit.scale.set(0.05, Math.max(hgt, 0.12), 0.05);
      if (it.arc) {
        const u = it.arc.material.uniforms;
        u.uTime.value = motion ? now / 1000 : 1.3;
        u.uReveal.value += ((modeT > 0.02 ? 1.01 : 0) - u.uReveal.value) * (motion ? 1 - Math.exp(-dt * 1.6) : 1);
        u.uOpacity.value = modeT * (it.s.status === "non_sovereign" ? 1 : 0.85);
        it.arc.visible = u.uOpacity.value > 0.01;
      }
    }
    renderer.render(scene, camera);
    // Labels and tooltip follow the camera.
    const w = host.clientWidth, h = host.clientHeight;
    for (const L of labels) {
      tmp.copy(L.world).project(camera);
      const show = L.cls !== "us" || modeT > 0.5;
      L.node.style.opacity = show ? 1 : 0;
      L.node.style.left = ((tmp.x + 1) / 2) * w + "px";
      L.node.style.top = ((1 - tmp.y) / 2) * h + (L.cls === "lugano" ? 14 : 0) + "px";
    }
    if (hovered) {
      const it = items.find((i) => i.s === hovered);
      tmp.copy(hovered.pos).setY((it ? it.height * (1 - 0.82 * modeT) : 0) + 0.04).project(camera);
      renderTip(hovered, { x: ((tmp.x + 1) / 2) * w, y: ((1 - tmp.y) / 2) * h });
    } else renderTip(null);
  }

  new ResizeObserver(resize).observe(host);
  resize();
  requestAnimationFrame(frame);

  function retheme() {
    readPalette();
    paintDots();
    dotMat.uniforms.uSize.value = isDark() ? 4.4 : 3.4;
    for (const it of items) {
      const c = colorFor(it.s.status);
      it.mat.color.copy(c); it.ringMat.color.copy(c); it.spriteMat.color.copy(c);
      if (it.arc) it.arc.material.uniforms.uColor.value.copy(c);
    }
    it_blend();
  }
  function it_blend() {
    // Additive glow reads well on dark ground; on paper it washes out, so use normal blending.
    const mode = isDark() ? THREE.AdditiveBlending : THREE.NormalBlending;
    for (const it of items) { it.spriteMat.blending = mode; it.spriteMat.needsUpdate = true; if (it.arc) { it.arc.material.blending = mode; it.arc.material.needsUpdate = true; } }
  }
  new MutationObserver(retheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", retheme);

  return {
    setSites(list) { setSites(list); it_blend(); },
    setMode,
  };
}
