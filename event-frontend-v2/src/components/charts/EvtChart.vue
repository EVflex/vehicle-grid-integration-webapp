<!--
  EvtChart (P5): thin ECharts host used by every native results chart.
  Owns the chart lifecycle only (init / setOption / resize / dispose);
  the option itself is built by the owning component so all styling logic
  lives next to the data it describes. Tree-shaken echarts/core build —
  only the pieces the results charts need are registered.
-->
<template>
  <div ref="el" class="evt-chart" :style="{ height: height + 'px' }"></div>
</template>

<script>
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  CanvasRenderer
]);

export default {
  name: "EvtChart",
  props: {
    option: { type: Object, required: true },
    height: { type: Number, default: 280 }
  },
  watch: {
    option(v) {
      if (this.chart) this.chart.setOption(v, { notMerge: true });
    }
  },
  mounted() {
    this.chart = echarts.init(this.$refs.el);
    this.chart.setOption(this.option);
    // The card/group containers resize with the viewport; keep the canvas
    // in step (also fires when a collapsed results group is reopened).
    this.ro = new ResizeObserver(() => {
      if (this.chart) this.chart.resize();
    });
    this.ro.observe(this.$refs.el);
  },
  beforeUnmount() {
    if (this.ro) this.ro.disconnect();
    if (this.chart) {
      this.chart.dispose();
      this.chart = null;
    }
  }
};
</script>

<style scoped>
.evt-chart {
  width: 100%;
}
</style>
