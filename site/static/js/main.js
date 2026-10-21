// Page controller: reads the embedded data document and draws every section.

import { el, $, eur, native, pct, dateLong, timeUTC, ago, shortHash, STATUS_LABEL, COUNTRY } from "./format.js";
import { lineChart, ladder, sparkline } from "./charts.js";
import { createMap } from "./map3d.js";

const D = JSON.parse(document.getElementById("compeu-data").textContent);
const P = Object.fromEntries(D.providers.map((p) => [p.id, p]));
const GPU = D.gpus;
const SCOPE = new Set(D.methodology.scope_countries);
const MATRIX_GPUS = ["gb300", "b300", "b200", "h200", "h100", "mi300x", "a100", "rtx-pro-6000", "l40s", "l4"];
const STATUS_ORDER = { sovereign: 0, under_review: 1, non_sovereign: 2 };
const gpuLabel = (id) => (GPU[id] ? GPU[id].label : id === "frontier" ? "Frontier GPU" : id);
const board = (id) => D.boards.find((b) => b.id === id);
const country = (cc) => COUNTRY[cc] || cc || "—";

// An offer counts as European compute when its country is in scope, or when it is a
// catalogue price the registry marks as the provider's European price list.
function inScope(o) {
  if (o.region === "catalogue") return !!P[o.provider]?.collection.catalogue_in_scope;
  return SCOPE.has(o.country);
}
const gpuMatch = (o, gpu) => (gpu === "frontier" ? GPU[o.gpu]?.tier === "frontier" : o.gpu === gpu);

function cheapest(offers) {
  return offers.filter((o) => o.eur !== null && !o.extra?.flag).reduce((a, b) => (a && +a.eur <= +b.eur ? a : b), null);
}

// ------------------------------------------------------------------ theme toggle
(function theme() {
  const btn = $("#theme");
  if (!btn) return;
  const root = document.documentElement;
  try { const t = localStorage.getItem("compeu-theme"); if (t) root.setAttribute("data-theme", t); } catch (e) {}
  btn.addEventListener("click", () => {
    const cur = root.getAttribute("data-theme");
    const dark = cur ? cur === "dark" : !matchMedia("(prefers-color-scheme: light)").matches;
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("compeu-theme", next); } catch (e) {}
  });
})();

// ------------------------------------------------------------------ live status
(function live() {
  const node = $("#live");
  if (!node || !D.ledger.last_run) return;
  const hours = (Date.now() - Date.parse(D.ledger.last_run)) / 3.6e6;
  if (hours > 30) node.classList.add("stale");
  node.title = `Last collection ${D.ledger.last_run}. ${D.schedule}.`;
})();

// ------------------------------------------------------------------ map
async function setupMap() {
  const host = $("#map");
  if (!host) return;
  let dots;
  const inline = document.getElementById("compeu-geo");
  try {
    dots = inline ? JSON.parse(inline.textContent) : await (await fetch(host.dataset.geo)).json();
  } catch (e) {
    host.append(el("div", { class: "map-fallback" }, "The map could not load. Every number is in the tables below."));
    return;
  }
  const map = createMap(host, { dots, sites: [], labelsHost: $("#map-labels"), tipHost: host.parentElement });
  if (!map) return;
  const state = { gpu: "h100", mode: "price" };
  const draw = () => map.setSites(mapSites(state.gpu));
  draw();
  bindSeg("#map-gpu", (v) => { state.gpu = v; draw(); caption(); });
  bindSeg("#map-mode", (v) => { state.mode = v; map.setMode(v); caption(); });
  const caption = () => {
    const c = $("#map-caption");
    if (!c) return;
    c.textContent = state.mode === "control"
      ? "Each arc runs from a data centre to the company that legally controls it."
      : `Column height: cheapest on-demand ${gpuLabel(state.gpu)} per GPU-hour at that site. Hollow ring: no public listing.`;
  };
  caption();
}

function mapSites(gpu) {
  const out = [];
  for (const p of D.providers) {
    if (p.scope === "global") continue;
    const offers = D.offers.filter((o) => o.provider === p.id && o.model === "on_demand" && gpuMatch(o, gpu));
    const ctrl = p.controller || {};
    const hqCountry = ctrl.country || p.legal_entity?.country;
    for (const s of p.sites) {
      const here = offers.filter((o) => o.region === "catalogue" || o.region === s.id || (o.region || "").startsWith(s.id + "-"));
      const best = cheapest(here);
      out.push({
        provider: p.id, providerName: p.name, status: p.status, site: s, hq: p.hq,
        hqCountry, price: best ? +best.eur : null, gpuLabel: gpuLabel(gpu === "frontier" && best ? best.gpu : gpu),
        priceScope: best ? (best.region === "catalogue" ? "catalogue price" : best.region) : (p.collection.method === "none" ? "no public price list" : null),
        hqLabel: p.status === "under_review" ? `contested (${country(ctrl.country)})` : country(hqCountry),
      });
    }
  }
  return out;
}

function bindSeg(sel, onChange) {
  const g = $(sel);
  if (!g) return;
  g.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-v]");
    if (!b) return;
    for (const x of g.querySelectorAll("button")) x.setAttribute("aria-pressed", String(x === b));
    onChange(b.dataset.v);
  });
}

// ------------------------------------------------------------------ index board
function renderBoard() {
  const host = $("#board");
  if (!host) return;
  host.innerHTML = "";
  for (const b of D.boards) {
    const cls = D.methodology.baskets[b.basket].status;
    const pts = D.series[b.id] || [];
    const n = b.constituents.length;
    const dots = el("span", { class: "dots", title: `${n} fresh constituent(s), ${b.min} required` },
      Array.from({ length: Math.max(b.min, n) }, (_, i) => el("i", { class: i < n ? "on" + (cls === "non_sovereign" ? " for" : "") : "" })));
    const value = b.status === "published"
      ? el("div", { class: "val" }, eur(b.value), el("small", {}, "/GPU-h"))
      : el("div", { class: "val na" }, b.status === "not_started" ? "No fixing yet" : "Not published", el("small", {}, b.reason ? "only " + b.reason.replace(" fresh constituent(s), ", " of ").replace(" required", " providers needed") : "insufficient data"));
    host.append(el("article", { class: "cell", id: "ix-" + b.id },
      el("header", {}, el("span", { class: "code" }, b.id),
        el("span", { class: "pill " + (b.status === "published" ? "ok" : "gap") }, b.status === "published" ? "Published" : "Gap")),
      el("div", { class: "name" }, b.name),
      value,
      el("div", { class: "foot" }, dots, sparkline(pts, cls)),
      el("div", { class: "foot" }, el("span", {}, n + " of " + b.min + "+ providers"), el("span", {}, b.date ? dateLong(b.date) : "—")),
    ));
  }
}

// ------------------------------------------------------------------ history
function renderHistory(gpu = "h100") {
  const host = $("#history");
  if (!host) return;
  const pair = [["CSX-" + gpu.toUpperCase(), "sovereign", "Sovereign"], ["CHX-" + gpu.toUpperCase(), "non_sovereign", "Hyperscalers"]];
  const series = pair.filter(([id]) => D.series[id]).map(([id, cls, short]) => ({ id, cls, short, label: board(id)?.name || id, points: D.series[id] }));
  lineChart(host, { series, height: 300 });
  const days = new Set(series.flatMap((s) => s.points.map((p) => p[0]))).size;
  $("#history-note").textContent = days < 7
    ? `The series started on ${dateLong(D.ledger.first_run)}. Each day adds one fixing; the line fills in from here. Gaps are days without enough fresh providers, never estimates.`
    : "Gaps are days without enough fresh providers. They are never filled with estimates.";
}

// ------------------------------------------------------------------ price ladder + offers table
const ui = { gpu: "h100", model: "on_demand", provider: "", scope: true, sort: "eur", dir: 1, limit: 40 };

function renderLadder() {
  const host = $("#ladder");
  if (!host) return;
  const rows = [];
  for (const p of D.providers) {
    const offers = D.offers.filter((o) => o.provider === p.id && o.model === "on_demand" && gpuMatch(o, ui.gpu) && (p.scope === "global" || inScope(o)));
    const best = cheapest(offers);
    if (!best) continue;
    rows.push({
      id: p.id, label: p.name + (p.scope === "global" ? " (global)" : ""), value: +best.eur,
      cls: p.scope === "global" ? "global" : p.status,
      sub: `${STATUS_LABEL[p.status]} · ${gpuLabel(best.gpu)} ${best.variant ? best.variant.toUpperCase() : ""} · ${best.sku} · ${best.region === "catalogue" ? "catalogue" : best.region}`,
    });
  }
  rows.sort((a, b) => (STATUS_ORDER[a.cls] ?? 3) - (STATUS_ORDER[b.cls] ?? 3) || a.value - b.value);
  const refs = [];
  for (const [id, cls, label] of [["CSX-" + ui.gpu.toUpperCase(), "sovereign", "CSX"], ["CHX-" + ui.gpu.toUpperCase(), "non_sovereign", "CHX"]]) {
    const b = board(id);
    if (b && b.status === "published") refs.push({ value: +b.value, cls, label });
  }
  ladder(host, { rows, refs, onSelect: (r) => openProvider(r.id) });
}

function renderOffers() {
  const host = $("#offers");
  if (!host) return;
  let rows = D.offers.filter((o) =>
    (ui.gpu === "all" || gpuMatch(o, ui.gpu)) &&
    (ui.model === "all" || o.model === ui.model) &&
    (!ui.provider || o.provider === ui.provider) &&
    (!ui.scope || inScope(o)));
  const key = {
    provider: (o) => P[o.provider].name, status: (o) => STATUS_ORDER[o.class], gpu: (o) => o.gpu, sku: (o) => o.sku,
    count: (o) => o.gpu_count, region: (o) => o.region || "", model: (o) => o.model, native: (o) => +o.native, eur: (o) => (o.eur === null ? Infinity : +o.eur),
  }[ui.sort];
  rows.sort((a, b) => { const x = key(a), y = key(b); return (x < y ? -1 : x > y ? 1 : 0) * ui.dir; });
  const total = rows.length;
  rows = rows.slice(0, ui.limit);
  const th = (k, label, n) => el("th", { class: n ? "n" : null, "aria-sort": ui.sort === k ? (ui.dir > 0 ? "ascending" : "descending") : null },
    el("button", { type: "button", onclick: () => { ui.dir = ui.sort === k ? -ui.dir : 1; ui.sort = k; renderOffers(); } }, label, ui.sort === k ? (ui.dir > 0 ? " ↑" : " ↓") : ""));
  const table = el("table", {},
    el("caption", { class: "visually-hidden" }, "Latest observed offers"),
    el("thead", {}, el("tr", {}, th("provider", "Provider"), th("status", "Status"), th("gpu", "GPU"), th("sku", "Offer"),
      th("count", "GPUs", true), th("region", "Region"), th("model", "Pricing"), th("native", "Listed /GPU-h", true), th("eur", "€ /GPU-h", true), el("th", {}, "Observed"))),
    el("tbody", {}, rows.map((o) => el("tr", {},
      el("td", {}, el("span", { class: "prov" }, el("span", { class: "swatch " + o.class }), el("button", { type: "button", onclick: () => openProvider(o.provider) }, P[o.provider].name))),
      el("td", {}, el("span", { class: "badge " + o.class }, STATUS_LABEL[o.class])),
      el("td", {}, gpuLabel(o.gpu), o.variant ? el("span", { class: "muted" }, " " + o.variant.toUpperCase()) : null),
      el("td", { class: "mono", style: "font-size:12px" }, o.sku),
      el("td", { class: "n" }, o.gpu_count),
      el("td", {}, o.region === "catalogue" ? el("span", { class: "muted" }, "catalogue") : o.region === "global" ? el("span", { class: "muted" }, "global") : `${o.region} `, o.country && o.region !== "catalogue" ? el("span", { class: "muted" }, o.country) : null),
      el("td", {}, o.model.replace("_", "-")),
      el("td", { class: "n" }, native(o.native, o.currency)),
      el("td", { class: "n" }, o.extra?.flag ? el("span", { class: "flag", title: "Exactly 0.50 while the same GPU's other price is at least twice as high: probably a default value, not a real listing. Excluded from comparisons." }, "suspect ") : null, el("b", {}, o.eur === null ? "—" : eur(o.eur))),
      el("td", { class: "mono muted", style: "font-size:12px" }, dateLong(o.observed_at)),
    ))),
  );
  host.innerHTML = "";
  host.append(el("div", { class: "table-wrap" }, table));
  const more = $("#offers-more");
  more.innerHTML = "";
  more.append(el("span", { class: "muted" }, `${Math.min(total, ui.limit)} of ${total} offers. Prices excl. VAT; non-EUR prices converted at the ECB reference rate of the observation day.`));
  if (total > ui.limit) more.append(" ", el("button", { class: "chip", type: "button", onclick: () => { ui.limit = 10000; renderOffers(); } }, "Show all"));
}

function setupPriceFilters() {
  const gpus = [...new Set(D.offers.map((o) => o.gpu))].sort((a, b) => (GPU[b]?.memory_gb || 0) - (GPU[a]?.memory_gb || 0));
  const gsel = $("#f-gpu");
  if (!gsel) return;
  gsel.append(el("option", { value: "frontier" }, "Any frontier GPU"), ...gpus.map((g) => el("option", { value: g, selected: g === ui.gpu }, gpuLabel(g))), el("option", { value: "all" }, "All GPUs (table)"));
  const psel = $("#f-provider");
  psel.append(el("option", { value: "" }, "All providers"), ...D.providers.filter((p) => D.offers.some((o) => o.provider === p.id)).map((p) => el("option", { value: p.id }, p.name)));
  gsel.addEventListener("change", () => { ui.gpu = gsel.value; renderLadder(); renderOffers(); });
  psel.addEventListener("change", () => { ui.provider = psel.value; renderOffers(); });
  $("#f-model").addEventListener("change", (e) => { ui.model = e.target.value; renderOffers(); });
  $("#f-scope").addEventListener("click", (e) => { ui.scope = !ui.scope; e.currentTarget.setAttribute("aria-pressed", String(ui.scope)); renderOffers(); });
}

// ------------------------------------------------------------------ coverage matrix
function renderMatrix() {
  const host = $("#matrix");
  if (!host) return;
  const groups = [["sovereign", "Sovereign"], ["under_review", "Under review"], ["non_sovereign", "Not sovereign (benchmarks)"]];
  const head = el("tr", {}, el("th", {}, "Provider"), MATRIX_GPUS.map((g) => el("th", { class: "n " + (GPU[g]?.tier === "frontier" ? "frontier" : "") }, gpuLabel(g))));
  const body = [];
  for (const [st, label] of groups) {
    const ps = D.providers.filter((p) => p.status === st);
    if (!ps.length) continue;
    body.push(el("tr", { class: "group" }, el("td", { colspan: MATRIX_GPUS.length + 1 }, label)));
    for (const p of ps) {
      const noData = !D.offers.some((o) => o.provider === p.id);
      body.push(el("tr", {},
        el("td", {}, el("span", { class: "prov" }, el("span", { class: "swatch " + p.status }), el("button", { type: "button", onclick: () => openProvider(p.id) }, p.name)),
          noData ? el("div", { class: "muted", style: "font-size:11px" }, collectionLabel(p)) : p.scope === "global" ? el("div", { class: "muted", style: "font-size:11px" }, "global marketplace") : null),
        MATRIX_GPUS.map((g) => {
          if (noData) return el("td", { class: "c" }, el("span", { class: "unknown", title: "No public price data" }, "?"));
          const best = cheapest(D.offers.filter((o) => o.provider === p.id && o.gpu === g && o.model === "on_demand" && (p.scope === "global" || inScope(o))));
          return el("td", { class: "c" }, best ? el("span", { class: "has " + p.status, title: `${best.sku}` }, eur(best.eur)) : el("span", { class: "none" }, "·"));
        }),
      ));
    }
  }
  host.innerHTML = "";
  host.append(el("div", { class: "table-wrap", style: "max-height:none" }, el("table", { class: "matrix" },
    el("caption", { class: "visually-hidden" }, "Cheapest on-demand price per GPU-hour, by provider and GPU"), el("thead", {}, head), el("tbody", {}, body))));
}

function collectionLabel(p) {
  return {
    awaiting_agreement: "no public price list · data agreement pending",
    no_public_price: "no public price list",
    no_machine_readable_price: "price page not machine-readable",
    no_public_api: "contract pricing, no public data",
    planned: "collector planned",
  }[p.collection.status] || "no public data";
}

// ------------------------------------------------------------------ sovereignty
function renderSovereignty() {
  const host = $("#chains");
  if (!host) return;
  const ps = [...D.providers].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.name.localeCompare(b.name));
  host.innerHTML = "";
  for (const p of ps) {
    const ctrl = p.controller || {};
    host.append(el("button", { class: "chain", type: "button", onclick: () => openProvider(p.id), "aria-label": `${p.name}: ${STATUS_LABEL[p.status]}. Open details.` },
      el("header", {}, el("b", {}, p.name), el("span", { class: "badge " + p.status }, STATUS_LABEL[p.status] + (p.provisional ? " · provisional" : ""))),
      el("div", { class: "links" },
        el("div", {}, el("span", { class: "lbl" }, "Entity"), el("span", {}, p.legal_entity?.name || "—"), el("span", { class: "cc" }, p.legal_entity?.country || "")),
        el("div", {}, el("span", { class: "lbl" }, "Control"), el("span", {}, (ctrl.name || "—").split(",")[0].replace(/ under a syndicate.*$/, "")), el("span", { class: "cc" }, ctrl.contested ? "?" : ctrl.country || "")),
      ),
      el("div", { class: "checks" }, p.criteria.map((c) => el("span", { class: "check " + c.result }, { seat: "EU/CH seat", control: "EU/CH control", no_extraterritorial: "No CLOUD Act reach" }[c.id]))),
    ));
  }
}

// ------------------------------------------------------------------ data health
function renderHealth() {
  const host = $("#health-list");
  if (!host) return;
  const rows = [...D.providers].sort((a, b) => (a.collection.method === "none") - (b.collection.method === "none") || a.name.localeCompare(b.name));
  const method = { api: "Public API", html: "Product page", none: "None" };
  host.innerHTML = "";
  host.append(el("div", { class: "table-wrap", style: "max-height:none" }, el("table", { class: "health" },
    el("caption", { class: "visually-hidden" }, "Collection status per provider"),
    el("thead", {}, el("tr", {}, ["Provider", "Source", "Status", "Last success", "Offers read", "Notes"].map((h, i) => el("th", { class: i === 4 ? "n" : null }, h)))),
    el("tbody", {}, rows.map((p) => {
      const h = p.health;
      let pill;
      if (p.collection.method === "none") pill = el("span", { class: "pill none" }, collectionLabel(p));
      else if (!h) pill = el("span", { class: "pill none" }, "not run yet");
      else if (h.last_status === "ok") pill = el("span", { class: "pill ok" }, "Collected");
      else pill = el("span", { class: "pill fail" }, `Failing ${h.failed_streak} run(s)`);
      const notes = h?.last_status === "failed" ? h.last_error : p.collection.note;
      return el("tr", {},
        el("td", {}, el("span", { class: "prov" }, el("span", { class: "swatch " + p.status }), el("button", { type: "button", onclick: () => openProvider(p.id) }, p.name))),
        el("td", {}, method[p.collection.method] || "—", p.collection.source ? el("div", { class: "muted mono", style: "font-size:11px;max-width:280px;overflow:hidden;text-overflow:ellipsis" }, p.collection.source.replace(/^https:\/\//, "")) : null),
        el("td", {}, pill),
        el("td", { class: "mono", style: "font-size:12px" }, h?.last_ok ? `${dateLong(h.last_ok)} ${timeUTC(h.last_ok)}` : "—"),
        el("td", { class: "n" }, h?.offers ?? "—"),
        el("td", {}, el("span", { class: "err" }, notes || "")),
      );
    })),
  )));
}

// ------------------------------------------------------------------ provider drawer
function openProvider(id) {
  const p = P[id];
  if (!p) return;
  const drawer = $("#drawer");
  const scrim = $("#scrim");
  const ctrl = p.controller || {};
  const offers = D.offers.filter((o) => o.provider === id && o.model === "on_demand").sort((a, b) => (+a.eur || 1e9) - (+b.eur || 1e9)).slice(0, 12);
  const body = $("#drawer-body");
  body.innerHTML = "";
  body.append(
    el("div", { class: "eyebrow" }, "Provider"),
    el("h2", { id: "drawer-title" }, p.name, p.aka ? el("span", { class: "muted", style: "font-weight:400" }, ` (formerly ${p.aka})`) : null),
    el("div", {}, el("span", { class: "badge " + p.status }, STATUS_LABEL[p.status]), p.provisional ? el("span", { class: "muted", style: "font-size:12px;margin-left:8px" }, "Some facts provisional: not yet checked against a company register.") : null),
    el("div", { class: "checks" }, p.criteria.map((c) => el("span", { class: "check " + c.result, title: c.question }, c.question.replace(/\?$/, "")))),
    el("dl", { class: "kv" },
      el("dt", {}, "Legal entity"), el("dd", {}, `${p.legal_entity?.name || "—"}, ${p.legal_entity?.city || ""} (${country(p.legal_entity?.country)})`),
      el("dt", {}, "Controlled by"), el("dd", {}, ctrl.name || "—", ctrl.country ? ` (${country(ctrl.country)})` : ""),
      ctrl.note ? [el("dt", {}, "Why"), el("dd", { class: "soft" }, ctrl.note)] : null,
      p.disclosures.length ? [el("dt", {}, "Disclosures"), el("dd", {}, el("ul", { style: "margin:0;padding-left:1.1em" }, p.disclosures.map((d) => el("li", {}, d))))] : null,
      el("dt", {}, "Rule"), el("dd", { class: "mono" }, D.rule.id),
      el("dt", {}, "Collection"), el("dd", { class: "soft" }, p.collection.note || "—"),
      p.collection.source ? [el("dt", {}, "Source"), el("dd", {}, el("a", { href: p.collection.source, target: "_blank", rel: "noopener" }, p.collection.source.replace(/^https:\/\//, "").slice(0, 70)))] : null,
      p.health?.last_ok ? [el("dt", {}, "Last success"), el("dd", { class: "mono" }, `${p.health.last_ok} (${ago(p.health.last_ok)})`)] : null,
      p.evidence.length ? [el("dt", {}, "Evidence"), el("dd", {}, p.evidence.map((e) => el("div", {}, el("a", { href: e.url, target: "_blank", rel: "noopener" }, e.claim))))] : null,
    ),
    offers.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, el("th", {}, "Offer"), el("th", {}, "GPU"), el("th", { class: "n" }, "€ /GPU-h"))),
      el("tbody", {}, offers.map((o) => el("tr", {}, el("td", { class: "mono", style: "font-size:12px" }, o.sku, el("div", { class: "muted" }, o.region)), el("td", {}, `${o.gpu_count}× ${gpuLabel(o.gpu)}`), el("td", { class: "n" }, el("b", {}, eur(o.eur)))))))) :
      el("p", { class: "muted" }, "No public prices collected for this provider."),
  );
  drawer.hidden = false;
  scrim.hidden = false;
  requestAnimationFrame(() => drawer.classList.add("open"));
  $("#drawer-close").focus();
}
function closeProvider() {
  const drawer = $("#drawer");
  drawer.classList.remove("open");
  $("#scrim").hidden = true;
  setTimeout(() => (drawer.hidden = true), 300);
}

// ------------------------------------------------------------------ boot
function boot() {
  renderBoard();
  renderHistory();
  bindSeg("#hist-gpu", (v) => renderHistory(v));
  setupPriceFilters();
  renderLadder();
  renderOffers();
  renderMatrix();
  renderSovereignty();
  renderHealth();
  $("#drawer-close")?.addEventListener("click", closeProvider);
  $("#scrim")?.addEventListener("click", closeProvider);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#drawer").hidden) closeProvider(); });
  let w = window.innerWidth;
  window.addEventListener("resize", () => {
    if (Math.abs(window.innerWidth - w) < 40) return;
    w = window.innerWidth;
    renderHistory($("#hist-gpu button[aria-pressed=true]")?.dataset.v || "h100");
    renderLadder();
  });
  setupMap();
}
boot();
