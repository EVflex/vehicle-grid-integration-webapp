<!--
  QuantileBandChart (P5): native replacement for the matplotlib "fillplot"
  voltage figures. Median line, inner 25-75% band, outer min-max band,
  dashed statutory-limit lines and red shading over non-converged windows.
  Hovering anywhere shows the exact values at that half hour (median, IQR,
  min-max), like the axis tooltip the product owner asked for.

  The bands are drawn with ECharts' stacking trick: an invisible base line
  at the band's lower quantile plus a stacked area holding (upper - lower).
  The tooltip reads the ORIGINAL quantile arrays by dataIndex, so it shows
  real voltages, not the stacked differences.
-->
<template>
  <evt-chart :option="option" :height="height" />
</template>

<script>
import EvtChart from "./EvtChart.vue";
import {
  chartTokens,
  hexToRgba,
  timeLabels,
  baseOption,
  failedMarkArea,
  limitMarkLine,
  themeReactive
} from "./chartTheme.js";

export default {
  name: "QuantileBandChart",
  components: { EvtChart },
  mixins: [themeReactive],
  props: {
    // {q0, q25, q50, q75, q100}: arrays of one value per half hour.
    quantiles: { type: Object, required: true },
    // [{value, label}] dashed horizontal limit lines.
    limits: { type: Array, default: () => [] },
    // Starting clock-hours of non-converged steps (convergence.failed_hours).
    failedHours: { type: Array, default: () => [] },
    unit: { type: String, default: " pu" },
    decimals: { type: Number, default: 4 },
    height: { type: Number, default: 260 }
  },
  computed: {
    option() {
      // Referencing themeDark makes this recompute when the OS theme flips,
      // re-reading the CSS tokens under the new theme.
      this.themeDark;
      const t = chartTokens();
      const q = this.quantiles;
      const n = q.q50.length;
      const labels = timeLabels(n);
      const fmt = v => (v == null ? "–" : v.toFixed(this.decimals) + this.unit);

      // y extent: the data plus every limit line, with a little headroom.
      const vals = [...q.q0, ...q.q100, ...this.limits.map(l => l.value)];
      const finite = vals.filter(v => v != null);
      const lo = Math.min(...finite);
      const hi = Math.max(...finite);
      const pad = (hi - lo || 1) * 0.08;

      const diff = (a, b) => a.map((v, i) => (v == null ? null : v - b[i]));
      const band = (base, upper, stack, color) => [
        {
          type: "line",
          data: base,
          stack,
          symbol: "none",
          lineStyle: { opacity: 0 },
          emphasis: { disabled: true },
          tooltip: { show: false }
        },
        {
          type: "line",
          data: diff(upper, base),
          stack,
          symbol: "none",
          lineStyle: { opacity: 0 },
          areaStyle: { color },
          emphasis: { disabled: true },
          tooltip: { show: false }
        }
      ];

      const opt = baseOption(t, labels);
      opt.yAxis.min = +(lo - pad).toFixed(this.decimals);
      opt.yAxis.max = +(hi + pad).toFixed(this.decimals);
      opt.yAxis.axisLabel.formatter = v => v.toFixed(2);
      opt.tooltip.formatter = params => {
        const i = params[0].dataIndex;
        return [
          `<b>${labels[i]}</b>`,
          `Median: <b>${fmt(q.q50[i])}</b>`,
          `IQR: ${fmt(q.q25[i])} – ${fmt(q.q75[i])}`,
          `Max: ${fmt(q.q100[i])}`,
          `Min: ${fmt(q.q0[i])}`
        ].join("<br/>");
      };
      opt.series = [
        ...band(q.q0, q.q100, "outer", hexToRgba(t.wire, 0.14)),
        ...band(q.q25, q.q75, "iqr", hexToRgba(t.wire, 0.22)),
        {
          type: "line",
          data: q.q50,
          symbol: "none",
          lineStyle: { color: t.accent, width: 2 },
          markLine: limitMarkLine(this.limits, t),
          markArea: failedMarkArea(this.failedHours, n, t)
        }
      ];
      return opt;
    }
  }
};
</script>
