<!--
  NetworkExplorer (P-B/C/D): an interactive single-line diagram of the chosen
  MV network. Renders the MV buses/lines from the pre-built topology JSON
  (GET /network-topology) and draws each LV network as a node placed at its MV
  connection bus, sized by the number of houses it serves.

  It replaces the previous static overview PNG, and doubles as the LV selector:
  - clicking an available LV node toggles it in/out of the selection (max 5),
    kept in sync with the chip list via the parent's lv_selected state; in a
    preset mode the preset's networks are highlighted and a click hands the
    preset selection over to "custom" (the parent handles the mode switch), so
    the user can see what "near substation" / "near edge" / "mixed" mean and
    tweak from there;
  - LV networks hosting the lumped MV assets (topology.mv_assets: solar_pv /
    fcs) are drawn in their own colours and are not selectable — they must stay
    lumped so that MV demand is preserved (RESERVED_LV_NETWORKS in the API).

  The map spans the full card width, with a fixed-height caption strip above
  it (round 2, 2026-07-11): hovering/focusing/selecting an LV network shows
  its transformer size, household count and how far it sits from the
  substation in plain language (never the raw electrical-distance ohm value);
  the four reserved solar/FCS host networks show their existing "cannot be
  selected" explanation instead. Primary feeders are labelled F1, F2, …,
  anchored close to the substation along each feeder's first cable (not at
  the far, node-cluttered end) and drawn in the foreground so they read over
  the lines and nodes, matching the results-page legend (topology.mv.feeders,
  built to the engine's feeder order).
-->
<template>
  <div class="nx">
    <div v-if="!topology" class="nx-empty">Loading network map…</div>
    <template v-else>
      <!-- CHANGE(round2-5): compact caption strip ABOVE the map, fixed
           height so the layout doesn't jump. Shows plain-language details
           (transformer size, households, distance from the substation — no
           ohm values) for the hovered/focused/selected LV network; the four
           reserved solar/FCS host networks keep their existing explanation
           instead; otherwise a neutral hint. -->
      <p class="nx-detail" :class="{ 'nx-detail-on': !!activeDetail }">
        {{ activeDetail ? activeDetail.text : "Hover a network for details." }}
      </p>
      <div class="nx-canvas-wrap">
        <svg
          :viewBox="`0 0 ${VW} ${VH}`"
          class="nx-svg"
          role="img"
          :aria-label="`Map of ${lvNodes.length} low-voltage networks`"
        >
          <!-- MV lines -->
          <line
            v-for="(ln, i) in mvSegments"
            :key="'l' + i"
            :x1="ln.x1"
            :y1="ln.y1"
            :x2="ln.x2"
            :y2="ln.y2"
            class="nx-mvline"
          />
          <!-- Substation marker -->
          <g v-if="substation">
            <rect
              :x="substation.x - 5"
              :y="substation.y - 5"
              width="10"
              height="10"
              class="nx-sub"
            />
            <text :x="substation.x" :y="substation.y - 8" class="nx-sub-lbl">
              MV substation
            </text>
          </g>
          <!-- LV network nodes: a visible circle plus an enlarged invisible
               hit circle so small nodes are still easy to click/tap. -->
          <g v-for="n in lvNodes" :key="n.id">
            <circle
              :cx="n.x"
              :cy="n.y"
              :r="n.r"
              :class="[nodeClass(n), { 'nx-hover': hovered === n.id }]"
            />
            <circle
              :cx="n.x"
              :cy="n.y"
              :r="n.r + 5"
              :class="['nx-hit', { 'nx-hit-click': isAvailable(n.id) }]"
              tabindex="0"
              :aria-label="
                `LV network ${n.id}, ${n.n_houses} houses` +
                  (isSelected(n.id) ? ', selected' : '') +
                  (isSolarHost(n.id) ? ', hosts the large solar farm' : '') +
                  (isFcsHost(n.id) ? ', hosts the fast-charging station' : '')
              "
              @click="onNodeClick(n)"
              @keydown.enter.prevent="onNodeClick(n)"
              @keydown.space.prevent="onNodeClick(n)"
              @mouseenter="setActive(n.id)"
              @mouseleave="hovered === n.id && (hovered = null)"
              @focus="setActive(n.id)"
            />
          </g>
          <!-- CHANGE(round2-6): primary feeder labels (F1, F2, …) render
               LAST (top SVG z-order = foreground) and are anchored close to
               the substation along each feeder's first cable, not at the
               far, node-cluttered end — see feederLabels(). -->
          <text
            v-for="f in feederLabels"
            :key="'f' + f.name"
            :x="f.x"
            :y="f.y"
            class="nx-feeder-lbl"
          >
            {{ f.name }}
          </text>
        </svg>
        <div class="nx-legend">
          <span class="nx-lg nx-lg-sel">selected</span>
          <span class="nx-lg nx-lg-avail">available</span>
          <span v-if="solarSet.size" class="nx-lg nx-lg-solar"
            >solar farm site</span
          >
          <span v-if="fcsSet.size" class="nx-lg nx-lg-fcs"
            >fast-charging site</span
          >
          <span v-if="!solarSet.size && !fcsSet.size" class="nx-lg nx-lg-dim"
            >MV solar PV &amp; fast-charging sites</span
          >
          <span class="nx-lg-note">node size ∝ houses</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: "NetworkExplorer",
  props: {
    topology: { type: Object, default: null },
    // The chosen LV network ids (numbers); mirrors lv_options.lv_selected.
    selected: { type: Array, default: () => [] },
    // The ids available to pick (numbers); mirrors lv_options.lv_list.
    available: { type: Array, default: () => [] },
    // "custom" enables clicking; anything else is read-only preset highlight.
    mode: { type: String, default: "custom" }
  },
  emits: ["toggle"],
  data() {
    // CHANGE(round3): viewBox height 320 -> 460 — a taller map (the width
    // already spans the full card) so the diagram, node spacing and feeder
    // labels all render larger.
    // lastId (round4): the most recently hovered/focused/clicked node — the
    // caption strip keeps showing its details after the pointer leaves, so
    // the text doesn't flash back to the hint between nodes.
    return { VW: 1000, VH: 460, hovered: null, lastId: null };
  },
  computed: {
    // Data-space -> viewBox projection, recomputed from the MV bus bounds so
    // both the wide rural network and the compact urban one fit.
    projection() {
      const buses = (this.topology.mv.buses || []).filter(
        b => b.x != null && b.y != null
      );
      const xs = buses.map(b => b.x);
      const ys = buses.map(b => b.y);
      const minX = Math.min(...xs),
        maxX = Math.max(...xs);
      const minY = Math.min(...ys),
        maxY = Math.max(...ys);
      const pad = 34;
      const sx = (this.VW - 2 * pad) / (maxX - minX || 1);
      const sy = (this.VH - 2 * pad) / (maxY - minY || 1);
      const s = Math.min(sx, sy);
      // Centre the drawing within the viewBox.
      const offX = pad + (this.VW - 2 * pad - s * (maxX - minX)) / 2;
      const offY = pad + (this.VH - 2 * pad - s * (maxY - minY)) / 2;
      return {
        // Flip Y: schematic y is up, SVG y is down.
        px: x => offX + s * (x - minX),
        py: y => offY + s * (maxY - y)
      };
    },
    busCoord() {
      const map = {};
      for (const b of this.topology.mv.buses) map[b.id] = b;
      return map;
    },
    mvSegments() {
      const p = this.projection;
      const out = [];
      for (const ln of this.topology.mv.lines) {
        const a = this.busCoord[ln.from],
          b = this.busCoord[ln.to];
        if (!a || !b || a.x == null || b.x == null) continue;
        out.push({
          x1: p.px(a.x),
          y1: p.py(a.y),
          x2: p.px(b.x),
          y2: p.py(b.y)
        });
      }
      return out;
    },
    substation() {
      const b = this.busCoord[this.topology.mv.substation];
      if (!b || b.x == null) return null;
      return { x: this.projection.px(b.x), y: this.projection.py(b.y) };
    },
    houseExtent() {
      const hs = Object.values(this.topology.lv_networks).map(n => n.n_houses);
      return { min: Math.min(...hs), max: Math.max(...hs) };
    },
    lvNodes() {
      const p = this.projection;
      const { min, max } = this.houseExtent;
      const out = [];
      for (const [id, net] of Object.entries(this.topology.lv_networks)) {
        const b = this.busCoord[net.mv_bus];
        if (!b || b.x == null) continue;
        // Radius 5–13 px by sqrt(houses) so area tracks house count.
        const t =
          max > min
            ? (Math.sqrt(net.n_houses) - Math.sqrt(min)) /
              (Math.sqrt(max) - Math.sqrt(min))
            : 0.5;
        out.push({
          id: Number(id),
          x: p.px(b.x),
          y: p.py(b.y),
          r: 5 + 8 * t,
          n_houses: net.n_houses
        });
      }
      return out;
    },
    // CHANGE(round3, replaces round2-6): primary feeder labels (F1, F2, …),
    // each placed ON its own feeder's cable a fixed on-screen distance out
    // from the substation. Verified against the real committed topologies:
    // on urban 1060 all 8 feeders leave the substation as SHORT stubs before
    // spreading out, so any placement confined to the first segment (or a
    // straight ray from the substation — the round-2 approach) crams 8
    // labels into a ~40 px cluster around the substation. Instead we now
    // TRACE each feeder's actual polyline (topology.mv.feeders[].to is the
    // first line's far bus; from there we follow mv.lines outward — the MV
    // network is radial, and at a branch the first line in file order is the
    // feeder's main run) and walk along it to a target screen distance where
    // the feeders have visibly separated. Candidate spots at several
    // distances × small perpendicular offsets are scored against the
    // substation label, already-placed labels, every LV node circle and the
    // viewBox edge; the first clear (else least-overlapping) one wins, so the
    // label always sits beside its own cable and stays legible. Order/naming
    // come straight from the topology JSON so they match the results-page
    // legend. Absent on older API responses → no labels.
    feederLabels() {
      const sub = this.substation;
      if (!sub) return [];
      const p = this.projection;
      const nodes = this.lvNodes;

      const box = (cx, cy, text) => {
        const w = 12 * text.length + 10,
          h = 20;
        return {
          x0: cx - w / 2,
          x1: cx + w / 2,
          y0: cy - h / 2,
          y1: cy + h / 2
        };
      };
      const overlaps = (a, b) =>
        a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
      const hitsNode = b =>
        nodes.some(
          n =>
            b.x0 - 2 < n.x + n.r &&
            b.x1 + 2 > n.x - n.r &&
            b.y0 - 2 < n.y + n.r &&
            b.y1 + 2 > n.y - n.r
        );
      const inView = b =>
        b.x0 >= 2 && b.x1 <= this.VW - 2 && b.y0 >= 2 && b.y1 <= this.VH - 2;

      // Outgoing lines per bus (file order = DSS order, so [0] follows the
      // feeder's main run at a branch).
      const nextOf = {};
      for (const ln of this.topology.mv.lines) {
        (nextOf[ln.from] = nextOf[ln.from] || []).push(ln.to);
      }
      const coord = id => {
        const b = this.busCoord[id];
        return b && b.x != null ? { x: p.px(b.x), y: p.py(b.y) } : null;
      };

      // Point at cumulative screen distance d along a polyline (clamped to
      // its end), plus the local direction there for the side offset.
      const pointAt = (path, d) => {
        for (let i = 1; i < path.length; i++) {
          const a = path[i - 1],
            b = path[i];
          const seg = Math.hypot(b.x - a.x, b.y - a.y);
          if (d <= seg && seg > 0) {
            const t = d / seg;
            return {
              x: a.x + (b.x - a.x) * t,
              y: a.y + (b.y - a.y) * t,
              ux: (b.x - a.x) / seg,
              uy: (b.y - a.y) / seg
            };
          }
          d -= seg;
        }
        const a = path[path.length - 2] || path[0],
          b = path[path.length - 1];
        const seg = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        return {
          x: b.x,
          y: b.y,
          ux: (b.x - a.x) / seg,
          uy: (b.y - a.y) / seg
        };
      };

      // The substation's own text sits just above the marker — keep every
      // feeder label's box clear of it too.
      const placed = [box(sub.x, sub.y - 10, "MV substation")];
      const out = [];
      for (const f of this.topology.mv.feeders || []) {
        // Trace this feeder's polyline outward from the substation.
        const path = [sub];
        let cur = f.to;
        let c = coord(cur);
        let guard = 40;
        while (c && guard-- > 0) {
          path.push(c);
          const nxt = (nextOf[cur] || [])[0];
          if (!nxt) break;
          cur = nxt;
          c = coord(cur);
        }
        if (path.length < 2) continue;

        // Try target distances out along the cable (far enough that the
        // feeders have separated, still clearly nearer the substation than
        // the feeder end), each with small perpendicular offsets.
        const dists = [70, 90, 55, 110, 130, 150, 170, 40];
        const sides = [13, -13, 21, -21, 28, -28];
        let best = null,
          bestScore = Infinity;
        for (const d of dists) {
          const pt = pointAt(path, d);
          const nx = -pt.uy,
            ny = pt.ux;
          for (const s of sides) {
            const bb = box(pt.x + nx * s, pt.y + ny * s, f.name);
            if (!inView(bb)) continue;
            const score =
              placed.filter(o => overlaps(bb, o)).length +
              (hitsNode(bb) ? 1 : 0);
            if (score < bestScore) {
              bestScore = score;
              best = bb;
            }
            if (bestScore === 0) break;
          }
          if (bestScore === 0) break;
        }
        if (!best) {
          const pt = pointAt(path, 70);
          best = box(pt.x, pt.y, f.name);
        }
        placed.push(best);
        out.push({
          name: f.name,
          x: (best.x0 + best.x1) / 2,
          y: (best.y0 + best.y1) / 2
        });
      }
      return out;
    },
    // LV networks hosting the lumped MV assets (absent on older API responses).
    solarSet() {
      const a = (this.topology.mv_assets || {}).solar_pv || [];
      return new Set(a.map(Number));
    },
    fcsSet() {
      const a = (this.topology.mv_assets || {}).fcs || [];
      return new Set(a.map(Number));
    },
    // CHANGE(round2-5): the caption-strip content for the currently active
    // (hovered/focused/selected) node — either the existing reserved-host
    // explanation, or the restored plain-language network details.
    activeDetail() {
      // Live hover wins; otherwise fall back to the last hovered/clicked
      // node so the caption stays put between interactions (round4).
      const id = this.hovered != null ? this.hovered : this.lastId;
      if (id == null) return null;
      if (this.isSolarHost(id))
        return {
          text: `LV network ${id} hosts the large solar farm — it cannot be selected for detailed modelling.`
        };
      if (this.isFcsHost(id))
        return {
          text: `LV network ${id} hosts the fast-charging station — it cannot be selected for detailed modelling.`
        };
      const net = this.topology.lv_networks[id];
      if (!net) return null;
      return { text: this.describeNetwork(id, net) };
    }
  },
  methods: {
    setActive(id) {
      this.hovered = id;
      this.lastId = id;
    },
    isSelected(id) {
      return this.selected.includes(Number(id));
    },
    isAvailable(id) {
      return this.available.includes(Number(id));
    },
    isSolarHost(id) {
      return this.solarSet.has(Number(id));
    },
    isFcsHost(id) {
      return this.fcsSet.has(Number(id));
    },
    nodeClass(n) {
      if (this.isSelected(n.id)) return "nx-node nx-node-sel";
      if (this.isSolarHost(n.id)) return "nx-node nx-node-solar";
      if (this.isFcsHost(n.id)) return "nx-node nx-node-fcs";
      if (this.mode === "custom" && this.isAvailable(n.id))
        return "nx-node nx-node-avail";
      if (this.isAvailable(n.id)) return "nx-node nx-node-preset";
      return "nx-node nx-node-dim";
    },
    // Plain-language per-network caption: transformer size, household count
    // and how far from the MV substation — expressed as a line-section count
    // (never the raw electrical-distance ohm value; product direction is
    // non-specialist-friendly labels only, see FRONTEND_REDESIGN_HANDOFF.md).
    describeNetwork(id, net) {
      const parts = [];
      if (net.xfmr_kva != null) parts.push(`${net.xfmr_kva} kVA transformer`);
      if (net.n_houses != null) {
        parts.push(`${net.n_houses} household${net.n_houses === 1 ? "" : "s"}`);
      }
      // CHANGE(round3): the feeder count and per-feeder household split are
      // back (they were in the pre-§20 detail panel and the owner missed
      // them). net.feeders[] carries one entry per LV feeder with n_houses.
      if (net.feeders && net.feeders.length) {
        const hs = net.feeders.map(f => f.n_houses).join(", ");
        parts.push(
          net.feeders.length === 1
            ? `1 feeder (${hs} households)`
            : `${net.feeders.length} feeders (${hs} households)`
        );
      } else if (net.n_feeders != null) {
        parts.push(`${net.n_feeders} feeder${net.n_feeders === 1 ? "" : "s"}`);
      }
      if (net.n_sections_from_sub != null) {
        const n = net.n_sections_from_sub;
        let dist = `${n} line section${n === 1 ? "" : "s"} from the substation`;
        const q = this.distanceQualifier(n);
        if (q) dist += ` (${q})`;
        parts.push(dist);
      }
      return `LV network ${id} — ${parts.join(" · ")}.`;
    },
    // Near/far qualifier relative to the other LV networks on this MV
    // network, since the raw section count alone isn't meaningful (urban
    // networks top out around a dozen sections, rural ones several dozen).
    distanceQualifier(n) {
      const all = Object.values(this.topology.lv_networks)
        .map(v => v.n_sections_from_sub)
        .filter(v => v != null);
      const max = Math.max(...all);
      if (!max || max <= 1) return "";
      const frac = n / max;
      if (frac <= 0.25) return "close";
      if (frac >= 0.7) return "far";
      return "";
    },
    onNodeClick(n) {
      // Any available network can be toggled by clicking; in a preset mode
      // the parent switches to "custom" first (keeping the preset selection).
      if (!this.isAvailable(n.id)) return;
      // Also mark it "active" so the detail strip updates immediately on
      // click even on touch devices, where a tap doesn't reliably carry
      // focus the way it does on desktop.
      this.setActive(n.id);
      this.$emit("toggle", n.id);
    }
  }
};
</script>

<style scoped>
.nx {
  display: block;
}
.nx-empty {
  padding: 24px;
  color: var(--muted, #888);
  text-align: center;
}
.nx-canvas-wrap {
  border: 1px solid var(--line, #d9e0e8);
  border-radius: 10px;
  background: var(--card, #fff);
  padding: 6px;
  overflow: hidden;
}
.nx-svg {
  width: 100%;
  height: auto;
  display: block;
}
.nx-mvline {
  stroke: var(--wire, #9fb3c8);
  stroke-width: 1.4;
}
.nx-sub {
  fill: var(--ink, #22303c);
}
.nx-sub-lbl {
  font-size: 11px;
  fill: var(--ink, #22303c);
  text-anchor: middle;
}
/* CHANGE(round2-6): bigger, foreground (last in the SVG so it paints on top
   of lines/nodes — see the template), with a card-coloured halo (a thick
   stroke painted behind the fill, paint-order: stroke) so the label stays
   readable wherever it lands over a line, in both themes. */
.nx-feeder-lbl {
  /* round3: 13px -> 15px, matching the enlarged map */
  font-size: 15px;
  font-weight: 700;
  fill: var(--wire, #2b5ea7);
  text-anchor: middle;
  dominant-baseline: middle;
  paint-order: stroke;
  stroke: var(--card, #fff);
  stroke-width: 3px;
  stroke-linejoin: round;
  pointer-events: none;
}
.nx-node {
  stroke-width: 1.4;
  transition: fill 0.1s, stroke 0.1s;
  /* The enlarged .nx-hit circle on top owns all pointer interaction. */
  pointer-events: none;
}
.nx-hit {
  fill: transparent;
  stroke: none;
  outline: none;
}
.nx-hit-click {
  cursor: pointer;
}
.nx-node-sel {
  fill: var(--accent, #2f8f5b);
  stroke: var(--accent, #2f8f5b);
}
.nx-node-avail {
  fill: var(--accent-soft, #cfeadd);
  stroke: var(--accent, #2f8f5b);
}
.nx-node-avail.nx-hover {
  fill: var(--accent, #2f8f5b);
  stroke-width: 2.6;
}
.nx-node-sel.nx-hover {
  stroke-width: 2.6;
}
.nx-node-preset {
  fill: var(--wire-soft, #e6eef8);
  stroke: var(--wire, #9fb3c8);
}
.nx-node-preset.nx-hover {
  stroke: var(--accent, #2f8f5b);
  stroke-width: 2.6;
}
.nx-node-solar {
  fill: var(--solar-soft, #f7edd0);
  stroke: var(--solar, #b8860b);
}
.nx-node-fcs {
  fill: var(--fcs-soft, #ece4f7);
  stroke: var(--fcs, #6f42c1);
}
.nx-node-dim {
  fill: var(--wire-soft, #e6eef8);
  stroke: var(--line, #d9e0e8);
  opacity: 0.55;
}
.nx-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  font-size: 0.72rem;
  padding: 4px 6px 2px;
  color: var(--muted, #667);
}
.nx-lg::before {
  content: "";
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: -1px;
}
.nx-lg-sel::before {
  background: var(--accent, #2f8f5b);
}
.nx-lg-avail::before {
  background: var(--accent-soft, #cfeadd);
  border: 1px solid var(--accent, #2f8f5b);
}
.nx-lg-dim::before {
  background: var(--wire-soft, #e6eef8);
  border: 1px solid var(--line, #d9e0e8);
}
.nx-lg-solar::before {
  background: var(--solar-soft, #f7edd0);
  border: 1px solid var(--solar, #b8860b);
}
.nx-lg-fcs::before {
  background: var(--fcs-soft, #ece4f7);
  border: 1px solid var(--fcs, #6f42c1);
}
.nx-lg-note {
  margin-left: auto;
  font-style: italic;
}
/* CHANGE(round4): the caption strip must NEVER change height, or the map
   below it bounces on every hover/click (the round-2 min-height reservation
   was silently defeated by the global box-sizing: border-box — 2.5em minus
   14px of padding+border only covered ONE line, so two-line captions grew
   the strip by a line). Hard height = clamped lines × line-height plus the
   14px of padding (12) + border (2), so hint and caption render identically
   tall and the map never moves. */
.nx-detail {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: calc(2 * 1.25em + 14px);
  margin: 0 0 8px;
  padding: 6px 10px;
  border: 1px solid var(--line, #d9e0e8);
  border-radius: 8px;
  background: var(--wire-soft, #e6eef8);
  font-size: 0.78rem;
  line-height: 1.25;
  color: var(--muted, #778);
}
.nx-detail-on {
  color: var(--ink, #22303c);
}
/* On narrow screens the richer caption needs more lines; the height stays
   hard-set (same formula, 4 lines) so the map still never moves. */
@media (max-width: 560px) {
  .nx-detail {
    -webkit-line-clamp: 4;
    height: calc(4 * 1.25em + 14px);
  }
}
</style>
