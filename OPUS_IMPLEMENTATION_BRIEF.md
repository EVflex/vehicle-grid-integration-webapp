# Implementation brief — front-end v2 & API refinements (2026-07-11)

> **STATUS: IMPLEMENTED (2026-07-11).** All items 1–7 done; item 8 left as
> documentation only (no backend RNG change), as specified. Verified in the
> browser and against the real engine. See CHANGES.md §20. The item-1 change
> intentionally omits the "zeros are placeholders" clause (user override).

Requested by Myriam; investigated and specified by Fable, to be implemented by
Opus. Verify each item in the browser (dev server `event-v2-dev` +
`dev-mock-api.js` or the real backend; see `.claude/launch.json`). Follow
`CHANGES.md` conventions and append an entry when done.

## 1. CSV format hint wording
`event-frontend-v2/src/components/SelectProfile.vue`

Replace the hint sentence for **all** technology rows (drop the
`hasPenetration ? "household's" : "site's"` branch) with exactly:

> Format: a header row, then 48 half-hour rows (00:00:00–23:30:00). Column 1
> is the time; every further column is one daily profile in kW (or kWh per
> half-hour)

Keep the "Download a template" link. Also append a short clause telling the
user the template's zeros are placeholders to replace with real kW values
(this caused a confusing run: an uploaded all-zero template ≈ technology off).

## 2. Brand subtitle
Navbar (see `event-frontend-v2/src/App.vue` / layouts): next to the "EVENT"
wordmark add the subtitle "Electric Vehicle Network analysis Tool" — small,
muted, hidden on narrow viewports if it crowds the nav.

## 3. Feeder labels (F1, F2, …) on the network map
`event-frontend-v2/src/components/NetworkExplorer.vue`, plus data source.

Label each primary feeder on the map with the same names the results use
("F1 (to 1101)…"). **Numbering must match the backend legend**, which comes
from OpenDSS line order: lines whose Bus1 is the primary substation bus
(`funcsTuring.set_base_tags`, `self.pmryLnsi`), legend built in
`azure_mockup.py` (~line 624) from `simulation.fdr2pwr` (an ordered dict of
Bus2 → rating).

Recommended: extend `vgi_api/scripts/build_network_topology.py` to emit
`mv.feeders: [{name: "F1", to: "1101", rating_mva: 6.82}, …]` in that same
order (the script parses the same .dss sources, so the line order is
available; ratings can be reproduced from `funcsTuring.set_powers`'s
`ckts2rr` table for frId 1060/1061), regenerate the two committed
`network_topology_*.json`, and render small muted text labels near each
feeder's far-end bus in NetworkExplorer. **Verification:** run a real
`/simulate` and check the map labels agree with the `primary_loadings_data`
CSV header (e.g. "F1 (to 1101), 6.82 MVA").

## 4. Map layout — bigger map, minimal hover info
`NetworkExplorer.vue` + `SimulateNetworkAPI.vue`

- Delete the right-hand detail panel (`.nx-detail`: the "Hover or tap a
  network node…" box and the feeders/houses/transformer/distance table).
  Make the map span the full card width (drop the 2-column grid).
- Move the "interactive — hover & click the nodes" caption to sit directly
  under the "Network map & LV network selector" heading (it currently sits
  right-aligned next to it; keep exactly one instance).
- The ONLY remaining hover/tap information: for the four reserved networks
  (solar hosts 1106/1142, fast-charging hosts 1107/1143 — ids come from
  `topology.mv_assets`, do not hard-code) show "hosts the large solar farm" /
  "hosts the fast-charging station" and that it cannot be selected. A small
  caption line under the map that fills in on hover/focus is preferred over a
  native title tooltip (works on touch and for keyboard focus). Keep the
  aria-labels as they are.
- Keep the legend (selected / available / solar farm site / fast-charging
  site / node size ∝ houses).

## 5. MV advanced parameters summary on one line
`SimulateNetworkAPI.vue` (`.evt-advanced` block)

The collapsed summary ("scaling ×1 · OLTC 1.04 pu · band 0.013 pu ·
residential 80%") must render on a single line before "show" is clicked:
`white-space: nowrap` with `overflow-x: auto` (or `text-overflow: ellipsis`)
on the summary span; check ~360 px mobile width.

## 6. Per-phase customer voltages — user-selectable network
Backend `vgi_api/vgi_api/azure_mockup.py` (~lines 427–475) + frontend.

Today the per-phase panel is hard-coded to the FIRST selected network
(`plot_key = rd["plot_options"]["lv_voltages"][0]`). Change:

- Backend: loop over **all** selected networks; return one per-phase PNG per
  network in a new response key, e.g. `lv_phase_pngs: {"1159": <b64>, …}`
  (the data `s.VlvLds[p_idx]` is already in memory — no extra solves). Keep
  the existing combined `lv_unbalance` image unchanged for compatibility, or
  split VUF and per-phase into separate figures if cleaner. Update
  `main.py`'s response assembly and the dev mock.
- Frontend: a small `<select>` above the per-phase image, options = the
  selected network ids, default = first.
- `regression_harness/vgi_regression.py`: confirm unknown response keys are
  skipped (per CHANGES.md §17.3 it already skips non-baseline keys — verify).

## 7. Explain the graphs in the UI (accuracy fixes)
`SimulateNetworkAPI.vue`

- Headline sentence: make explicit it is the worst customer, e.g. "The
  lowest simulated customer voltage reaches 0.938 pu around 18:00 on LV
  network 1169 (below the 0.94 pu limit)." Mirror for the max/overvoltage
  branch ("highest simulated customer voltage"). Tile label "LOWEST CUSTOMER
  VOLTAGE" is already correct.
- "LV customer voltages" ⓘ tooltip: "Each panel is one modelled LV network.
  The centre line is the median customer's voltage; the shaded band spans all
  simulated customers (outer edge = min–max, inner = 25–75%). Dashed red
  lines are the statutory limits (0.94–1.10 pu)."
- Per-phase graph ⓘ tooltip: "Solid line = average voltage of customers on
  that phase; shaded band = the min–max spread across those customers. The
  three colours are the three phases; diverging phases indicate unbalance."

## 8. Backend RNG behaviour — DO NOT CHANGE (documentation only)

Decision (Myriam, 2026-07-11): leave the backend exactly as is. For context
only: all technologies share one seeded RNG (`rand_seed: 0`), so enabling a
technology changes the draw sequence and thereby the random placement of
*other* demand (observed: EVs-enabled-with-zero-profile vs EVs-off gave
0.938 vs 0.941 pu lowest customer voltage). This is deterministic and
reproducible, not a bug to fix here. No code change; do not touch
`funcsTuring.py` for this.
