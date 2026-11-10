// Small SVG chart helpers (no outside library, so charts also work offline).
// drawChart(container, {type: "line"|"bar"|"hbar", labels, series: [{label, data, color}], x, y})

function drawChart(el, cfg) {
  const ink = cssVar("--muted"), grid = cssVar("--line");
  const { labels, series } = cfg;
  const n = labels.length;
  if (!n) { el.innerHTML = '<p class="empty">No data yet.</p>'; return; }
  const max = Math.max(1, ...series.flatMap(s => s.data));
  const nice = niceMax(max);
  const legend = series.length > 1
    ? `<div style="display:flex;gap:16px;font-size:13px;color:${ink};margin-bottom:6px">${series.map(s =>
        `<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${s.color};margin-right:5px"></span>${esc(s.label)}</span>`).join("")}</div>`
    : "";

  if (cfg.type === "hbar") {
    const rowH = 26, labW = 210, W = 700, H = n * rowH + 24, plotW = W - labW - 50;
    let svg = "";
    for (let t = 0; t <= 4; t++) {
      const x = labW + plotW * t / 4;
      svg += `<line x1="${x}" x2="${x}" y1="0" y2="${n * rowH}" stroke="${grid}"/>` +
             `<text x="${x}" y="${n * rowH + 16}" fill="${ink}" font-size="11" text-anchor="middle">${fmtNum(Math.round(nice * t / 4))}</text>`;
    }
    labels.forEach((lab, i) => {
      const v = series[0].data[i], w = plotW * v / nice, y = i * rowH;
      svg += `<text x="${labW - 8}" y="${y + rowH / 2 + 4}" fill="${ink}" font-size="12" text-anchor="end">${esc(trunc(lab, 30))}<title>${esc(lab)}</title></text>` +
             `<rect x="${labW}" y="${y + 4}" width="${w}" height="${rowH - 8}" rx="3" fill="${series[0].color}"><title>${esc(lab)}: ${fmtNum(v)}</title></rect>` +
             `<text x="${labW + w + 5}" y="${y + rowH / 2 + 4}" fill="${ink}" font-size="11">${fmtNum(v)}</text>`;
    });
    el.style.height = "auto";
    el.innerHTML = legend + `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img">${svg}</svg>`;
    return;
  }

  const W = 700, H = 280, L = 44, R = 12, T = 10, B = 52, pw = W - L - R, ph = H - T - B;
  const yOf = v => T + ph - ph * v / nice;
  let svg = "";
  for (let t = 0; t <= 4; t++) {
    const v = nice * t / 4, y = yOf(v);
    svg += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="${grid}"/>` +
           `<text x="${L - 6}" y="${y + 4}" fill="${ink}" font-size="11" text-anchor="end">${fmtNum(Math.round(v))}</text>`;
  }
  const step = Math.ceil(n / 12); // at most ~12 x labels
  const slot = pw / n;
  labels.forEach((lab, i) => {
    if (i % step === 0) {
      const x = L + slot * (i + .5);
      svg += `<text x="${x}" y="${H - B + 16}" fill="${ink}" font-size="11" text-anchor="middle">${esc(trunc(shortDate(lab), 22))}</text>`;
    }
  });
  if (cfg.type === "line") {
    series.forEach(s => {
      const pts = s.data.map((v, i) => `${L + slot * (i + .5)},${yOf(v)}`);
      svg += `<polyline points="${pts.join(" ")}" fill="none" stroke="${s.color}" stroke-width="2.5"/>` +
             s.data.map((v, i) => `<circle cx="${L + slot * (i + .5)}" cy="${yOf(v)}" r="3.5" fill="${s.color}"><title>${esc(labels[i])} · ${esc(s.label)}: ${fmtNum(v)}</title></circle>`).join("");
    });
  } else {
    const bw = Math.min(48, slot * .7);
    labels.forEach((lab, i) => {
      const v = series[0].data[i], color = Array.isArray(series[0].color) ? series[0].color[i] : series[0].color;
      svg += `<rect x="${L + slot * (i + .5) - bw / 2}" y="${yOf(v)}" width="${bw}" height="${T + ph - yOf(v)}" rx="3" fill="${color}"><title>${esc(lab)}: ${fmtNum(v)}</title></rect>`;
    });
  }
  if (cfg.x) svg += `<text x="${L + pw / 2}" y="${H - 8}" fill="${ink}" font-size="12" text-anchor="middle">${esc(cfg.x)}</text>`;
  if (cfg.y) svg += `<text transform="translate(12 ${T + ph / 2}) rotate(-90)" fill="${ink}" font-size="12" text-anchor="middle">${esc(cfg.y)}</text>`;
  el.style.height = "auto";
  el.innerHTML = legend + `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img">${svg}</svg>`;
}

// Top of the axis: four equal whole-number steps that cover v.
function niceMax(v) {
  const raw = v / 4, p = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    const step = m * p;
    if (step >= raw && Number.isInteger(step)) return step * 4;
  }
  return Math.ceil(raw) * 4;
}
function trunc(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
function shortDate(s) { return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s.slice(5) : s; }
