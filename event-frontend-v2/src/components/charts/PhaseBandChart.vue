<!--
  PhaseBandChart (P5): native replacement for the per-phase customer-voltage
  matplotlib figures (one per selected LV network). Per phase: a mean line
  plus a shaded min–max band across that phase's customers, with the LV
  statutory limits dashed and red shading over non-converged windows.
  Hovering shows each phase's mean and spread at that half hour.

  Bands use the same ECharts stacking trick as QuantileBandChart: an
  invisible base line at the band's minimum plus a stacked area holding
  (max - min); the tooltip reads the original arrays by dataIndex.
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
  name: "PhaseBandChart",
  components: { EvtChart },
  mixins: [themeReactive],
  props: {
    // [{phase, mean, lo, hi}]: arrays of one value per half hour.
    bands: { type: Array, required: true },
    limits: { type: Array, default: () => [] },
    failedHours: { type: Array, default: () => [] },
    unit: { type: String, default: " pu" },
    decimals: { type: Number, default: 3 },
    height: { type: Number, default: 280 }
  },
  computed: {
    option() {
      this.themeDark; // recompute on OS theme flip (re-reads CSS tokens)
      const t = chartTokens();
      const n = this.bands[0] ? this.bands[0].mean.length : 0;
      const labels = timeLabels(n);
      // Phase 1/2/3 in the same blue/amber/green roles as the rest of the app.
      const phaseColor = { 1: t.wire, 2: t.solar, 3: t.accent };
      const fmt = v => (v == null ? "–" : v.toFixed(this.decimals) + this.unit);

      const vals = [
        ...this.bands.flatMap(b => [...b.lo, ...b.hi]),
        ...this.limits.map(l => l.value)
      ].filter(v => v != null);
      const lo = Math.min(...vals);
      const hi = Math.max(...vals);
      const pad = (hi - lo || 1) * 0.08;

      const diff = (a, b) => a.map((v, i) => (v == null ? null : v - b[i]));

      const opt = baseOption(t, labels);
      opt.yAxis.min = +(lo - pad).toFixed(this.decimals);
      opt.yAxis.max = +(hi + pad).toFixed(this.decimals);
      opt.yAxis.axisLabel.formatter = v => v.toFixed(2);
      opt.grid.top = 40;
      opt.legend = {
        top: 0,
        left: 0,
        icon: "roundRect",
        itemWidth: 12,
        itemHeight: 3,
        data: this.bands.map(b => "Phase " + b.phase),
        textStyle: { color: t.muted, fontFamily: t.font, fontSize: 11 }
      };
      opt.tooltip.formatter = params => {
        const i = params[0].dataIndex;
        return [
          `<b>${labels[i]}</b>`,
          ...this.bands.map(
            b =>
              `Phase ${b.phase}: <b>${fmt(b.mean[i])}</b> ` +
              `(${fmt(b.lo[i])} – ${fmt(b.hi[i])})`
          )
        ].join("<br/>");
      };
      opt.series = this.bands.flatMap((b, bi) => {
        const color = phaseColor[b.phase] || t.fcs;
        return [
          {
            type: "line",
            data: b.lo,
            stack: "ph" + b.phase,
            symbol: "none",
            lineStyle: { opacity: 0 },
            emphasis: { disabled: true },
            tooltip: { show: false }
          },
          {
            type: "line",
            data: diff(b.hi, b.lo),
            stack: "ph" + b.phase,
            symbol: "none",
            lineStyle: { opacity: 0 },
            areaStyle: { color: hexToRgba(color, 0.18) },
            emphasis: { disabled: true },
            tooltip: { show: false }
          },
          {
            name: "Phase " + b.phase,
            type: "line",
            data: b.mean,
            symbol: "none",
            lineStyle: { color, width: 2 },
            itemStyle: { color },
            ...(bi === 0
              ? {
                  markLine: limitMarkLine(this.limits, t),
                  markArea: failedMarkArea(this.failedHours, n, t)
                }
              : {})
          }
        ];
      });
      return opt;
    }
  }
};
</script>
