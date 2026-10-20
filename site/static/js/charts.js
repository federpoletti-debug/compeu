// Hand-built SVG charts: index history (line), price ladder (bars), sparkline.
// One scale per chart; thin marks; recessive grid; hover layer on every chart;
// text in ink tokens, series colour only on marks.

import { el, eur, dateLong } from "./format.js";

const NS = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) n.setAttribute(k, v);
  return n;
}

function niceTicks(min, max, count = 5) {
  if (min === max) { min -= 1; max += 1; }
  const span = max - min;
  const step0 = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= count) || 10 * mag;
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(10));
  return { lo, hi, ticks };
}

const seriesColor = { sovereign: "var(--sov)", non_sovereign: "var(--for)", under_review: "var(--rev)", global: "var(--rev)" };

// ------------------------------------------------------------------ line chart

export function lineChart(host, { series, height = 300, unit = "€ / GPU-hour" }) {
  host.innerHTML = "";
  const width = Math.max(host.clientWidth || 640, 300);
  const m = { t: 18, r: 86, b: 30, l: 46 };
  const w = width - m.l - m.r;
  const h = height - m.t - m.b;
  const dates = [...new Set(series.flatMap((s) => s.points.map((p) => p[0])))].sort();
  const values = series.flatMap((s) => s.points.map((p) => p[1]).filter((v) => v !== null)).map(Number);
  const root = svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `Index history in ${unit}` });
  if (!dates.length || !values.length) {
    host.append(el("p", { class: "note" }, "No published fixings yet."));
    return;
  }
  const y = niceTicks(0, Math.max(...values) * 1.1, 5);
  const t0 = Date.parse(dates[0]);
  const t1 = Date.parse(dates[dates.length - 1]);
  const pad = t0 === t1 ? 86400000 * 3 : 0;
  const X = (d) => m.l + ((Date.parse(d) - (t0 - pad)) / ((t1 + pad) - (t0 - pad))) * w;
  const Y = (v) => m.t + h - ((v - y.lo) / (y.hi - y.lo)) * h;

  const grid = svg("g", { class: "grid" });
  const axis = svg("g", { class: "axis" });
  for (const t of y.ticks) {
    grid.append(svg("line", { x1: m.l, x2: m.l + w, y1: Y(t), y2: Y(t) }));
    const tx = svg("text", { x: m.l - 8, y: Y(t) + 4, "text-anchor": "end" });
    tx.textContent = "€" + t.toFixed(t < 10 ? 2 : 0);
    axis.append(tx);
  }
  const xTicks = dates.length <= 6 ? dates : dates.filter((_, i) => i % Math.ceil(dates.length / 6) === 0);
  for (const d of xTicks) {
    const tx = svg("text", { x: X(d), y: m.t + h + 20, "text-anchor": "middle" });
    tx.textContent = dateLong(d).replace(/ \d{4}$/, "");
    axis.append(tx);
  }
  root.append(grid, svg("line", { class: "baseline", x1: m.l, x2: m.l + w, y1: m.t + h, y2: m.t + h }), axis);

  for (const s of series) {
    const color = seriesColor[s.cls] || "var(--ink-2)";
    let d = "";
    let pen = false;
    for (const [date, v] of s.points) {
      if (v === null) { pen = false; continue; }
      d += `${pen ? "L" : "M"}${X(date).toFixed(1)},${Y(+v).toFixed(1)}`;
      pen = true;
    }
    if (d) root.append(svg("path", { d, fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    const pts = s.points.filter((p) => p[1] !== null);
    for (const [date, v] of pts.length <= 40 ? pts : pts.slice(-1)) {
      root.append(svg("circle", { cx: X(date), cy: Y(+v), r: 4, fill: color, stroke: "var(--bg-2)", "stroke-width": 2 }));
    }
    const last = pts[pts.length - 1];
    if (last) {
      const lbl = svg("text", { x: X(last[0]) + 10, y: Y(+last[1]) + 4, fill: "var(--ink)", "font-size": 12, "font-weight": 600 });
      lbl.textContent = eur(last[1]);
      const sub = svg("text", { x: X(last[0]) + 10, y: Y(+last[1]) + 18, class: "axis" });
      sub.textContent = s.short || s.label;
      root.append(lbl, sub);
    }
  }

  // Hover layer: crosshair + tooltip on the nearest date.
  const hover = svg("line", { class: "hover-line", y1: m.t, y2: m.t + h, visibility: "hidden" });
  const hit = svg("rect", { x: m.l, y: m.t, width: w, height: h, fill: "transparent" });
  root.append(hover, hit);
  host.style.position = "relative";
  host.append(root);
  const tip = el("div", { class: "chart-tip", hidden: true });
  host.append(tip);
  const show = (clientX) => {
    const r = root.getBoundingClientRect();
    const sx = ((clientX - r.left) / r.width) * width;
    let best = dates[0];
    for (const d of dates) if (Math.abs(X(d) - sx) < Math.abs(X(best) - sx)) best = d;
    hover.setAttribute("x1", X(best)); hover.setAttribute("x2", X(best));
    hover.setAttribute("visibility", "visible");
    tip.innerHTML = "";
    tip.append(el("div", { class: "muted" }, dateLong(best)));
    for (const s of series) {
      const p = s.points.find((q) => q[0] === best);
      tip.append(el("div", { class: "r" }, el("span", { class: "swatch " + s.cls }), s.label + " ",
        el("b", {}, p && p[1] !== null ? eur(p[1]) : "not published")));
    }
    tip.hidden = false;
    const px = (X(best) / width) * r.width;
    tip.style.left = Math.min(Math.max(px + 12, 0), r.width - tip.offsetWidth) + "px";
    tip.style.top = "8px";
  };
  hit.addEventListener("pointermove", (e) => show(e.clientX));
  hit.addEventListener("pointerleave", () => { tip.hidden = true; hover.setAttribute("visibility", "hidden"); });
}

// ------------------------------------------------------------------ price ladder

export function ladder(host, { rows, refs = [], onSelect }) {
  host.innerHTML = "";
  if (!rows.length) {
    host.append(el("p", { class: "note" }, "No provider lists this GPU on demand in Europe today."));
    return;
  }
  const width = Math.max(host.clientWidth || 640, 300);
  const rowH = 30;
  const m = { t: 26 + 13 * Math.max(refs.length - 1, 0), r: 76, b: 26, l: Math.min(150, width * 0.34) };
  const height = m.t + m.b + rows.length * rowH;
  const w = width - m.l - m.r;
  const max = Math.max(...rows.map((r) => r.value), ...refs.map((r) => r.value));
  const x = niceTicks(0, max * 1.05, width < 500 ? 3 : 5);
  const X = (v) => m.l + (v / x.hi) * w;
  const root = svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Cheapest on-demand price per GPU-hour by provider" });
  const grid = svg("g", { class: "grid" });
  const axis = svg("g", { class: "axis" });
  for (const t of x.ticks) {
    grid.append(svg("line", { x1: X(t), x2: X(t), y1: m.t - 6, y2: height - m.b }));
    const tx = svg("text", { x: X(t), y: height - m.b + 16, "text-anchor": "middle" });
    tx.textContent = "€" + t;
    axis.append(tx);
  }
  root.append(grid, axis);
  refs.forEach((ref, i) => {
    const ly = m.t - 16 - 13 * (refs.length - 1 - i); // stack labels so close values never collide
    root.append(svg("line", { x1: X(ref.value), x2: X(ref.value), y1: ly + 4, y2: height - m.b, stroke: seriesColor[ref.cls], "stroke-width": 1.5, opacity: 0.9 }));
    const t = svg("text", { x: X(ref.value), y: ly, "text-anchor": "middle", class: "axis" });
    t.textContent = `${ref.label} ${eur(ref.value)}`;
    root.append(t);
  });
  host.style.position = "relative";
  const tip = el("div", { class: "chart-tip", hidden: true });
  rows.forEach((r, i) => {
    const cy = m.t + i * rowH + rowH / 2;
    const g = svg("g", { tabindex: 0, role: "button", "aria-label": `${r.label}: ${eur(r.value)} per GPU-hour` });
    const name = svg("text", { x: m.l - 10, y: cy + 4, "text-anchor": "end", fill: "var(--ink)", "font-size": 12.5 });
    name.textContent = r.label;
    const barW = Math.max(X(r.value) - m.l, 2);
    const bar = svg("rect", { x: m.l, y: cy - 7, width: barW, height: 14, rx: 3, fill: seriesColor[r.cls] || "var(--rev)", opacity: r.cls === "under_review" ? 0.55 : 1 });
    const val = svg("text", { x: m.l + barW + 8, y: cy + 4, fill: "var(--ink)", "font-size": 12, "font-weight": 600 });
    val.textContent = eur(r.value);
    const hit = svg("rect", { x: 0, y: cy - rowH / 2, width, height: rowH, fill: "transparent" });
    g.append(hit, name, bar, val);
    const showTip = () => {
      tip.innerHTML = "";
      tip.append(el("div", {}, el("b", {}, r.label)), el("div", { class: "muted" }, r.sub || ""), el("div", {}, eur(r.value), " / GPU-hour"));
      tip.hidden = false;
      const rect = root.getBoundingClientRect();
      tip.style.left = Math.min((X(r.value) / width) * rect.width + 14, rect.width - tip.offsetWidth - 4) + "px";
      tip.style.top = ((cy / height) * rect.height - 10) + "px";
    };
    g.addEventListener("pointerenter", showTip);
    g.addEventListener("focus", showTip);
    g.addEventListener("pointerleave", () => (tip.hidden = true));
    g.addEventListener("blur", () => (tip.hidden = true));
    if (onSelect) {
      g.style.cursor = "pointer";
      g.addEventListener("click", () => onSelect(r));
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(r); } });
    }
    root.append(g);
  });
  host.append(root, tip);
}

// ------------------------------------------------------------------ sparkline

export function sparkline(points, cls = "sovereign") {
  const vals = points.map((p) => (p[1] === null ? null : +p[1]));
  const real = vals.filter((v) => v !== null);
  const W = 120, H = 28;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, "aria-hidden": "true" });
  if (!real.length) return s;
  const lo = Math.min(...real), hi = Math.max(...real);
  const X = (i) => (vals.length === 1 ? W - 4 : 2 + (i / (vals.length - 1)) * (W - 6));
  const Y = (v) => (hi === lo ? H / 2 : H - 3 - ((v - lo) / (hi - lo)) * (H - 6));
  let d = "", pen = false;
  vals.forEach((v, i) => { if (v === null) { pen = false; return; } d += `${pen ? "L" : "M"}${X(i)},${Y(v)}`; pen = true; });
  if (d) s.append(svg("path", { d, fill: "none", stroke: seriesColor[cls], "stroke-width": 1.5 }));
  const li = vals.length - 1 - [...vals].reverse().findIndex((v) => v !== null);
  s.append(svg("circle", { cx: X(li), cy: Y(vals[li]), r: 2.5, fill: seriesColor[cls] }));
  return s;
}
