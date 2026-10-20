// Theme toggle for the text pages (the home page has it in main.js).
const btn = document.getElementById("theme");
const root = document.documentElement;
btn?.addEventListener("click", () => {
  const cur = root.getAttribute("data-theme");
  const dark = cur ? cur === "dark" : !matchMedia("(prefers-color-scheme: light)").matches;
  const next = dark ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try { localStorage.setItem("ceresio-theme", next); } catch (e) {}
});
