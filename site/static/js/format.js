// Formatting and small helpers shared by every module.

export const STATUS_LABEL = {
  sovereign: "Sovereign",
  non_sovereign: "Not sovereign",
  under_review: "Under review",
};

export const COUNTRY = {
  AT: "Austria", BE: "Belgium", BG: "Bulgaria", HR: "Croatia", CY: "Cyprus", CZ: "Czechia",
  DK: "Denmark", EE: "Estonia", FI: "Finland", FR: "France", DE: "Germany", GR: "Greece",
  HU: "Hungary", IE: "Ireland", IT: "Italy", LV: "Latvia", LT: "Lithuania", LU: "Luxembourg",
  MT: "Malta", NL: "Netherlands", PL: "Poland", PT: "Portugal", RO: "Romania", SK: "Slovakia",
  SI: "Slovenia", ES: "Spain", SE: "Sweden", CH: "Switzerland", IS: "Iceland", NO: "Norway",
  LI: "Liechtenstein", GB: "United Kingdom", US: "United States", MX: "Mexico",
};

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export const $ = (sel, root = document) => root.querySelector(sel);

export function eur(v, digits = 2) {
  if (v === null || v === undefined || v === "") return "—";
  return "€" + Number(v).toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function native(v, ccy) {
  if (v === null || v === undefined) return "—";
  const sym = { EUR: "€", USD: "$", CHF: "CHF ", GBP: "£" }[ccy] ?? ccy + " ";
  return sym + Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

export function pct(v, digits = 0) {
  return (v * 100).toLocaleString("en-GB", { maximumFractionDigits: digits }) + "%";
}

export function dateLong(iso) {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? iso + "T12:00:00Z" : iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

export function timeUTC(iso) {
  if (!iso) return "";
  return iso.slice(11, 16) + " UTC";
}

export function ago(iso, now = Date.now()) {
  if (!iso) return "never";
  const h = (now - new Date(iso).getTime()) / 3.6e6;
  if (h < 1) return "under an hour ago";
  if (h < 36) return Math.round(h) + " h ago";
  return Math.round(h / 24) + " days ago";
}

export function shortHash(h) {
  return h ? h.replace("sha256:", "").slice(0, 12) : "—";
}

export function reducedMotion() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function cssVar(name, node = document.documentElement) {
  return getComputedStyle(node).getPropertyValue(name).trim();
}

// Theme: explicit choice on <html data-theme>, otherwise the OS preference.
export function isDark() {
  const t = document.documentElement.getAttribute("data-theme");
  if (t) return t === "dark";
  return !(window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches);
}
