/* ============================================================================
   CSV -> chart-series helpers for the native results charts (P5).

   The /simulate response ships each figure's numbers as a CSV string (the
   same ones behind the "csv" download links). These helpers turn a parsed
   {header, rows} into the shapes the chart components take. Header matching
   is by regex on the embedded numbers, NOT exact strings — the real API
   formats quantiles as "0.0%" (np.linspace floats) where the dev mock says
   "0%", and both must parse.

   Every helper returns null when the CSV doesn't match what it expects, and
   the view falls back to the matplotlib image for that figure — older API
   deployments keep working.
   ========================================================================== */

/** CSV string -> {header: [...], rows: [[...numbers|null]]}. */
export function parseFigureCsv(str) {
  if (!str || typeof str !== "string") return null;
  const lines = str
    .trim()
    .split("\n")
    .filter(l => l.length);
  if (lines.length < 2) return null;
  const header = lines[0].split(",");
  const rows = lines.slice(1).map(l =>
    l.split(",").map(c => {
      const x = Number(c);
      return isFinite(x) ? x : null; // gaps render as breaks, not zeros
    })
  );
  return { header, rows };
}

const column = (rows, ci) => rows.map(r => (ci < r.length ? r[ci] : null));

/**
 * lv_comparison_data: 5 quantile columns per LV network, headers like
 * "0% quantile: LV Network: 1101". -> [{net, quantiles: {q0..q100}}, ...]
 */
export function lvQuantilePanels(parsed) {
  if (!parsed) return null;
  const nets = {};
  parsed.header.forEach((h, ci) => {
    const m = /(\d+(?:\.\d+)?)\s*%\s*quantile.*?LV\s*Network:?\s*(\d+)/i.exec(
      h
    );
    if (!m) return;
    const q = Math.round(Number(m[1]));
    (nets[m[2]] = nets[m[2]] || {})["q" + q] = column(parsed.rows, ci);
  });
  const panels = Object.entries(nets)
    .filter(([, qs]) => qs.q0 && qs.q25 && qs.q50 && qs.q75 && qs.q100)
    .map(([net, quantiles]) => ({ net, quantiles }));
  return panels.length ? panels : null;
}

/** mv_voltages_data: one column per quantile ("MV voltage: 25.0% quantile"). */
export function mvQuantiles(parsed) {
  if (!parsed) return null;
  const qs = {};
  parsed.header.forEach((h, ci) => {
    const m = /(\d+(?:\.\d+)?)\s*%\s*quantile/i.exec(h);
    if (m) qs["q" + Math.round(Number(m[1]))] = column(parsed.rows, ci);
  });
  return qs.q0 && qs.q25 && qs.q50 && qs.q75 && qs.q100 ? qs : null;
}

/** Generic one-line-per-column figure -> [{name, data}, ...]. */
export function lineSeries(parsed, prettify) {
  if (!parsed || !parsed.header.length) return null;
  return parsed.header.map((h, ci) => ({
    name: prettify ? prettify(h) : h,
    data: column(parsed.rows, ci)
  }));
}

/** "Prmy. Sub. Util." / "Sdry. Sub. Util.1101 (500 kVA)" -> plain labels. */
export function prettyTransformerName(h) {
  if (/^Prmy\./i.test(h)) return "Primary substation";
  const m = /^Sdry\.\s*Sub\.\s*Util\.?\s*(\d+)\s*(\(.*\))?/i.exec(h);
  if (m) return `LV ${m[1]}${m[2] ? " " + m[2] : ""}`;
  return h;
}

/** "VUF %: LV Network 1101" -> "LV 1101". */
export function prettyVufName(h) {
  const m = /LV\s*Network:?\s*(\d+)/i.exec(h);
  return m ? `LV ${m[1]}` : h;
}
