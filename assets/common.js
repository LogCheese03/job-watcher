// Shared by every page: navigation bar, data loading, CSV parsing, helpers,
// and the service worker that makes the site installable and work offline.

const PAGES = [
  ["index.html", "Today"],
  ["browse.html", "Browse"],
  ["market.html", "Market"],
];

function renderNav() {
  const here = location.pathname.split("/").pop() || "index.html";
  const links = PAGES.map(([href, label]) =>
    `<a class="link${href === here ? " on" : ""}" href="${href}">${label}</a>`).join("");
  document.body.insertAdjacentHTML("afterbegin",
    `<nav class="nav"><div class="wrap"><a class="brand" href="index.html">Job<span>Watcher</span></a>${links}</div></nav>`);
}

// RFC 4180 CSV parser (handles quoted fields with commas, quotes and newlines)
function parseCSV(text) {
  const rows = [];
  let row = [], field = "", i = 0, quoted = false;
  while (i < text.length) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
    i++;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const header = rows.shift() || [];
  return rows.filter(r => r.length === header.length).map(r => {
    const o = {};
    header.forEach((h, j) => { o[h] = r[j]; });
    o.in_role = o.in_role === "true";
    o.first_run = o.first_run === "true";
    return o;
  });
}

async function loadData() {
  const [statusRes, histRes] = await Promise.all([
    fetch("data/status.json", { cache: "no-cache" }),
    fetch("data/history.csv", { cache: "no-cache" }),
  ]);
  if (!statusRes.ok || !histRes.ok) throw new Error("Data files not found yet");
  const status = await statusRes.json();
  const history = parseCSV(await histRes.text());
  const runDay = status.run_time.slice(0, 10);
  return { status, history, runDay };
}

// Dates are YYYY-MM-DD strings in UTC; difference in whole days.
function dayDiff(later, earlier) {
  return Math.round((Date.parse(later + "T00:00:00Z") - Date.parse(earlier + "T00:00:00Z")) / 86400000);
}
function dayRange(start, end) {
  const out = [];
  for (let t = Date.parse(start + "T00:00:00Z"); t <= Date.parse(end + "T00:00:00Z"); t += 86400000)
    out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}
function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b), m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmtNum(n) { return Number(n).toLocaleString(); }
function fmtTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) + " (local)";
}
function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

function showOfflineBanner() {
  const b = document.getElementById("offline");
  if (b) b.style.display = navigator.onLine ? "none" : "block";
}

function showError(err) {
  const main = document.querySelector("main");
  main.insertAdjacentHTML("afterbegin",
    `<div class="panel"><strong>Could not load the data.</strong> ${esc(err.message)}</div>`);
}

if (document.body) renderNav(); else document.addEventListener("DOMContentLoaded", renderNav);
window.addEventListener("online", showOfflineBanner);
window.addEventListener("offline", showOfflineBanner);
document.addEventListener("DOMContentLoaded", showOfflineBanner);
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js"));
}
