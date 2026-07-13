<!--
  MultiLineChart (P5): native replacement for the one-line-per-column
  matplotlib figures (transformer utilisation, primary feeder loadings,
  phase unbalance). Dashed limit lines (rating / planning levels), red
  shading over non-converged windows, and an axis tooltip listing every
  series' value at the hovered half hour.
-->
<template>
  <evt-chart :option="option" :height="height" />
</template>

<script>
import EvtChart from "./EvtChart.vue";
import {
  chartTokens,
  timeLabels,
  baseOption,
  failedMarkArea,
  limitMarkLine,
  themeReactive
} from "./chartTheme.js";

export default {
  name: "MultiLineChart",
  components: { EvtChart },
  mixins: [themeReactive],
  props: {
    // [{name, data}]: one line per series, one value per half hour.
    series: { type: Array, required: true },
    limits: { type: Array, default: () => [] },
    failedHours: { type: Array, default: () => [] },
    unit: { type: String, default: "%" },
    decimals: { type: Number, default: 1 },
    height: { type: Number, default: 280 }
  },
  computed: {
    option() {
      this.themeDark; // recompute on OS theme flip (re-reads CSS tokens)
      const t = chartTokens();
      const n = this.series[0] ? this.series[0].data.length : 0;
      const labels = timeLabels(n);
      const palette = [t.wire, t.accent, t.solar, t.fcs, t.warn, t.crit];

      const vals = [
        ...this.series.flatMap(s => s.data),
        ...this.limits.map(l => l.value)
      ].filter(v => v != null);
      const hi = Math.max(...vals);

      const opt = baseOption(t, labels);
      // Loadings/VUF are magnitudes — anchor at zero, headroom above the
      // larger of the data and the limit lines.
      opt.yAxis.min = 0;
      opt.yAxis.max = Math.ceil(hi * 1.08);
      opt.grid.top = 40;
      opt.legend = {
        top: 0,
        left: 0,
        icon: "roundRect",
        itemWidth: 12,
        itemHeight: 3,
        textStyle: { color: t.muted, fontFamily: t.font, fontSize: 11 }
      };
      opt.tooltip.valueFormatter = v =>
        v == null ? "–" : v.toFixed(this.decimals) + this.unit;
      opt.series = this.series.map((s, i) => ({
        name: s.name,
        type: "line",
        data: s.data,
        symbol: "none",
        triggerLineEvent: true,
        lineStyle: { width: 2, color: palette[i % palette.length] },
        itemStyle: { color: palette[i % palette.length] },
        // Hovering a line (or its legend entry) dims the others and names
        // the hovered one at its right end, so 8 similar feeder lines are
        // tellable apart without reading the tooltip.
        emphasis: {
          focus: "series",
          lineStyle: { width: 3 },
          endLabel: {
            show: true,
            formatter: p => p.seriesName,
            align: "right",
            offset: [-4, 0],
            color: palette[i % palette.length],
            fontFamily: t.font,
            fontSize: 11,
            fontWeight: 600,
            backgroundColor: t.card,
            padding: [2, 5],
            borderRadius: 3
          }
        },
        ...(i === 0
          ? {
              markLine: limitMarkLine(this.limits, t),
              markArea: failedMarkArea(this.failedHours, n, t)
            }
          : {})
      }));
      return opt;
    }
  }
};
</script>
