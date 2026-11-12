// Shared by every page: navigation bar, data loading, CSV parsing, helpers,
// and the service worker that makes the site installable and work offline.

const PAGES = [
  ["index.html", "Today"],
  ["browse.html", "Browse"],
  ["market.html", "Market"],
];

const LOGO = `<svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
  <rect width="26" height="26" rx="7" fill="#1c2c3a"/>
  <rect x="6" y="13" width="3.5" height="7" rx="1" fill="#8ea2b2"/>
  <rect x="11.25" y="9" width="3.5" height="11" rx="1" fill="#8ea2b2"/>
  <rect x="16.5" y="5.5" width="3.5" height="14.5" rx="1" fill="#d9a441"/></svg>`;

function renderNav() {
  const here = location.pathname.split("/").pop() || "index.html";
  const links = PAGES.map(([href, label]) =>
    `<a class="link${href === here ? " on" : ""}" href="${href}">${label}</a>`).join("");
  document.body.insertAdjacentHTML("afterbegin",
    `<nav class="nav"><div class="wrap"><a class="brand" href="index.html" aria-label="Job Watcher home">${LOGO}<span class="word">Job Watcher</span></a>${links}</div></nav>`);
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
  return new Date(iso).toLocaleString(undefined, { weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// Employers write locations many ways ("New York, NY", "USA, NY, New York",
// "Remote - US", "3 Locations"). placeOf() turns one into a short place name
// used for location filters and counts.
const US_STATES = {AL:"Alabama",AK:"Alaska",AZ:"Arizona",AR:"Arkansas",CA:"California",CO:"Colorado",CT:"Connecticut",DE:"Delaware",DC:"District of Columbia",FL:"Florida",GA:"Georgia",HI:"Hawaii",ID:"Idaho",IL:"Illinois",IN:"Indiana",IA:"Iowa",KS:"Kansas",KY:"Kentucky",LA:"Louisiana",ME:"Maine",MD:"Maryland",MA:"Massachusetts",MI:"Michigan",MN:"Minnesota",MS:"Mississippi",MO:"Missouri",MT:"Montana",NE:"Nebraska",NV:"Nevada",NH:"New Hampshire",NJ:"New Jersey",NM:"New Mexico",NY:"New York",NC:"North Carolina",ND:"North Dakota",OH:"Ohio",OK:"Oklahoma",OR:"Oregon",PA:"Pennsylvania",RI:"Rhode Island",SC:"South Carolina",SD:"South Dakota",TN:"Tennessee",TX:"Texas",UT:"Utah",VT:"Vermont",VA:"Virginia",WA:"Washington",WV:"West Virginia",WI:"Wisconsin",WY:"Wyoming"};
const STATE_BY_NAME = Object.fromEntries(Object.entries(US_STATES).map(([k, v]) => [v.toLowerCase(), k]));
const COUNTRY_WORDS = new Set(["us", "usa", "u.s.", "united states", "united states of america"]);

function placeOf(location) {
  const raw = (location || "").trim();
  if (!raw) return "Not given";
  if (/remote|work from home|virtual/i.test(raw)) return "Remote";
  if (/^\d+\s+locations?$/i.test(raw) || /multiple locations/i.test(raw)) return "Multiple locations";
  const first = raw.split(/;|\||\n| or /)[0];
  const parts = first.split(/,| - /).map(p => p.trim()).filter(p => p && !COUNTRY_WORDS.has(p.toLowerCase()));
  if (!parts.length) return raw;
  let state = null, city = null;
  for (const p of parts) {
    const up = p.toUpperCase();
    if (!state && US_STATES[up]) { state = up; continue; }
    if (!state && STATE_BY_NAME[p.toLowerCase()] && parts.length > 1 && city) { state = STATE_BY_NAME[p.toLowerCase()]; continue; }
    if (!city) city = p;
  }
  if (city && state) return `${city}, ${state}`;
  return city || (state ? US_STATES[state] : raw);
}
function stateOf(place) {
  const m = /, ([A-Z]{2})$/.exec(place);
  return m ? US_STATES[m[1]] : null;
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
