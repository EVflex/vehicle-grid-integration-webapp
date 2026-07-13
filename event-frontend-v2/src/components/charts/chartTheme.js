/* ============================================================================
   Shared theming + geometry helpers for the native results charts (P5).

   The charts read their colours from the SAME CSS design tokens as the rest
   of the app (vgi_styles.css), resolved at option-build time — so they match
   the current light/dark theme automatically instead of arriving as white
   matplotlib JPEGs. Components rebuild their option when the OS theme flips
   (see themeReactive below).
   ========================================================================== */

/** Resolve the app's CSS design tokens (with light-theme fallbacks). */
export function chartTokens() {
  const s = getComputedStyle(document.documentElement);
  const v = (name, fallback) => (s.getPropertyValue(name) || fallback).trim();
  return {
    ink: v("--ink", "#1c2620"),
    muted: v("--muted", "#5c6b62"),
    line: v("--line", "#dce3dd"),
    card: v("--card", "#ffffff"),
    accent: v("--accent", "#0e7c5b"),
    wire: v("--wire", "#2b5ea7"),
    solar: v("--solar", "#a07908"),
    fcs: v("--fcs", "#6f42c1"),
    warn: v("--warn", "#c2711b"),
    crit: v("--crit", "#b23a31"),
    font: getComputedStyle(document.body).fontFamily
  };
}

/** "#rrggbb" (or "#rgb") -> "rgba(r,g,b,a)". Falls through non-hex values. */
export function hexToRgba(hex, alpha) {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex);
  if (!m) return hex;
  let h = m[1];
  if (h.length === 3) h = h.replace(/./g, c => c + c);
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

/** "HH:MM" labels for n equal steps over the 24 h day (row i of the CSVs). */
export function timeLabels(n) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const hours = (i / n) * 24;
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    out.push(String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0"));
  }
  return out;
}

/**
 * Shared axis/grid/tooltip scaffolding. Ticks every 3 hours so 48 half-hour
 * categories don't smudge into each other.
 */
export function baseOption(t, labels) {
  const every = Math.max(1, Math.round(labels.length / 8));
  return {
    animation: false,
    textStyle: { fontFamily: t.font, color: t.muted },
    grid: { left: 10, right: 14, top: 14, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: t.line } },
      axisTick: { show: false },
      axisLabel: {
        color: t.muted,
        interval: i => i % every === 0
      }
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisLabel: { color: t.muted },
      splitLine: { lineStyle: { color: hexToRgba(t.line, 0.6) } }
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: t.card,
      borderColor: t.line,
      textStyle: { color: t.ink, fontFamily: t.font, fontSize: 12 },
      axisPointer: { lineStyle: { color: t.muted } }
    }
  };
}

/**
 * markArea shading the non-converged half-hours red (same meaning as the
 * matplotlib figures). failedHours are the starting clock-hours of failed
 * steps; contiguous steps are merged into one area.
 */
export function failedMarkArea(failedHours, nRows, t) {
  if (!failedHours || !failedHours.length || !nRows) return undefined;
  const step = 24 / nRows;
  const idx = [...new Set(failedHours.map(h => Math.round(h / step)))]
    .filter(i => i >= 0 && i < nRows)
    .sort((a, b) => a - b);
  if (!idx.length) return undefined;
  const ranges = [];
  let start = idx[0];
  let prev = idx[0];
  for (const i of idx.slice(1)) {
    if (i !== prev + 1) {
      ranges.push([start, prev]);
      start = i;
    }
    prev = i;
  }
  ranges.push([start, prev]);
  return {
    silent: true,
    itemStyle: { color: hexToRgba(t.crit, 0.12) },
    data: ranges.map(([a, b]) => [
      { xAxis: a },
      { xAxis: Math.min(b + 1, nRows - 1) }
    ])
  };
}

/** Dashed horizontal limit lines (statutory / rating / planning levels). */
export function limitMarkLine(limits, t) {
  if (!limits || !limits.length) return undefined;
  return {
    silent: true,
    symbol: "none",
    lineStyle: { color: t.crit, type: "dashed", width: 1 },
    label: {
      color: t.crit,
      fontSize: 10,
      formatter: p => p.name,
      position: "insideEndTop"
    },
    data: limits.map(l => ({ name: l.label || "", yAxis: l.value }))
  };
}

/**
 * Mixin: makes a component's chart option rebuild when the OS colour scheme
 * flips (the app's theme mechanism is prefers-color-scheme — CHANGES.md §21).
 * Components reference `this.themeDark` in their option computed so the CSS
 * tokens are re-read under the new theme.
 */
export const themeReactive = {
  data() {
    return {
      themeDark:
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches
    };
  },
  mounted() {
    if (!window.matchMedia) return;
    this._themeMq = window.matchMedia("(prefers-color-scheme: dark)");
    this._themeCb = e => {
      this.themeDark = e.matches;
    };
    if (this._themeMq.addEventListener)
      this._themeMq.addEventListener("change", this._themeCb);
    else this._themeMq.addListener(this._themeCb);
  },
  beforeUnmount() {
    if (!this._themeMq) return;
    if (this._themeMq.removeEventListener)
      this._themeMq.removeEventListener("change", this._themeCb);
    else this._themeMq.removeListener(this._themeCb);
  }
};
