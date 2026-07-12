# Feature assessment & implementation plan (2026-07-09)

Four proposed features for the VGI webapp, assessed against the actual code and
network data. Originally a plan; every change is documented in `CHANGES.md` and
marked inline with `CHANGE`/`FIX` comments, per the repo convention.

> **IMPLEMENTED (2026-07-09).** Features 1, 2, 3 and the added non-convergence
> feature (5) are built, tested, and verified end-to-end in the browser — see
> `CHANGES.md` §17. Feature 4 was dropped by decision (see §4 below). Test
> status: 133 backend tests pass; the numeric regression harness passes (max
> rel diff ~1e-10, i.e. the existing power-flow outputs are unchanged). The
> phases below (A–E) map to CHANGES §17.1 (A/5), §17.2 (B/C/D → features 1+3),
> §17.3 (E → feature 2).

Verdicts up front:

| # | Feature | Feasible? | Effort | Value |
|---|---------|-----------|--------|-------|
| 1 | Detailed visual of chosen networks (feeders, houses, distances) | **Yes** | ~3 days | High |
| 2 | 3-phase feeders + phase unbalance | **Yes — feeders are 3-phase, unbalance is already in the model, just not reported** | ~2 days | High (scientifically the strongest) |
| 3 | Choose LV networks from a map | **Yes as an interactive schematic; No as a geographic map** | merges with #1, +1–2 days | High |
| 4 | LV transformer settings (scaling, OLTC setpoint, bandwidth) | Yes, but **dropped by decision (2026-07-09)** — see §4 | — | — |
| 5 | Surface non-convergence to the user (added during review) | **Yes** | ~0.5 day | High (scientific integrity) |

Recommended order: **#1+#5 first (the non-convergence fix is half a day and
protects every result), #3 folded into #1, then #2.** #4 is kept below for
the record but is not being implemented.

---

## 0. What the code and data actually contain (verified facts)

These facts drive every verdict below.

- Two MV circuits ship with the API: **1060** (urban, `HV_UG_full.zip`) and
  **1061** (urban–rural, `HV_UG-OHa_full.zip`), in
  `vgi_api/vgi_api/data/opendssnetworks/`. The urban circuit contains **75 LV
  networks**; each request models 1–5 of them **in detail** and lumps the rest
  as aggregate MV loads (`funcsTuring.modify_network` comments/uncomments
  `redirect` lines in `redirect_lv_ntwx.dss` and toggles loads in
  `lds_edit.dss`).
- **Coordinates exist at both levels.** MV: `buscoords.csv` (schematic x,y per
  bus). LV: every feeder has `XY_Position*.csv` (metres-scale x,y for every
  bus, thousands of points per network).
- **LV line lengths are physical** (`Length=… Units=m` in
  `LinesUnq_pruned*.txt`), so house-to-LV-substation distances in metres are
  computable by graph traversal. **MV lines have impedances only** (absolute
  ohms, no `Length` attribute), so "distance from the MV substation" at MV
  level can only be expressed as hops, schematic distance, or electrical
  impedance — not metres. The visual must be honest about this.
- **Every LV feeder line is 3-phase** (`phases=3` on all lines checked);
  **house loads are single-phase**, allocated across phases `.1/.2/.3`
  (e.g. network 1125 feeder 2: loads on all three phases). So phase unbalance
  is *already being solved by OpenDSS on every run* — it is simply not
  extracted: `record_solution` (funcsTuring.py:1587) keeps only one phase per
  load (`VlvLds`), and the sequence voltages at LV substations (`Vsb`, from
  the DSS `SeqVoltages` attribute) are computed only when `full=True`, which
  the API never passes.
- **Each detailed LV network has exactly one MV/LV transformer**, defined in
  `Feeder_1/Transformers_mod*.txt`, e.g.
  `New Transformer.TR11_11251_1 Buses=[1125 1_1125_1] Conns=[Delta Wye]
  kVs=[11 0.416] kVAs=[500 500] XHL=5.0 … tap=1.000` — **fixed tap, no
  RegControl**. Lumped LV networks have no transformer at all (they are MV
  loads), so LV transformer settings can only ever apply to the
  networks modelled in detail — which matches the request.
- The MV transformer knobs work by **rewriting the top-level .dss text files**
  before compilation (`modify_network`: `vreg`/`band` in `regcontrols.dss`,
  `kVA` in `transformers.dss` via `dss_value_update`).
- ⚠️ **Implementation gotcha:** since the performance fix, the per-request
  directory contains *copies* of the top-level files but a **symlink to the
  shared read-only `lvNetworks/` cache**. Editing `Transformers_mod*.txt`
  through that symlink would corrupt the cache for every subsequent request
  on the machine. LV transformer changes must therefore be made **in-memory
  via OpenDSS `Edit`/`New` commands after compilation**, not by file rewriting
  (§4).
- The 48 half-hourly solves are snapshot solves with controls active
  (`run_dss_lds`; the MV OLTC acts and its tap is recorded each step via
  `sln.Tap`), so a RegControl added post-compile participates normally.
- Frontend (`event-frontend-v2/`, Vue 3 + vuelidate): network chosen with two
  buttons (1060/1061); LV selection via preset chips or a "custom" ID list
  fetched from `/lv-network`; the current "network map" is a **static PNG**
  (`overview_urban.png`) — same image for both networks. MV transformer
  sliders already exist under "Advanced network parameters".

---

## 1. Feature 1 — visualise the chosen networks in detail

### Verdict: feasible, high value

All the data needed is in the zips. The right architecture is to **precompute
a topology JSON per MV network offline** (the networks are static — they
change only if the zips change) rather than computing it per request with
OpenDSS.

What the visual can honestly show:

| Requested | Available? | How |
|---|---|---|
| Feeders per LV network | ✅ | count `Feeder_*` dirs (2–5 per network) |
| Houses per feeder | ✅ | count `New Load` rows in `LoadsCopyUnq*.txt` (e.g. network 1125: 55/31/39/75 across four feeders) |
| Distance of LV network from MV substation | ⚠️ partially | MV model has no line lengths. Show (a) schematic position on the MV single-line diagram, and (b) electrical distance (Σ|Z1| in ohms, or number of line sections) from bus 1100. Label it "electrical distance", not metres. |
| Distance of houses from LV substation | ✅ in metres | shortest-path traversal of the LV line graph (lengths in m) from the transformer bus to each load bus → report max / mean / distribution per feeder |
| Transformer rating | ✅ | parse `Transformers_mod*.txt` kVA |

### Implementation steps

1. **`vgi_api/scripts/build_network_topology.py`** (new, committed, run
   offline): for each of 1060/1061, parse the zip and emit
   `network_topology_<n_id>.json`:
   ```
   { mv: { buses: [{id, x, y}], lines: [{from, to}], substation: "1100" },
     lv_networks: { "1125": { mv_bus, xfmr_kva, n_feeders,
                              feeders: [{name, n_houses, total_line_m,
                                         max_house_dist_m, mean_house_dist_m}],
                              elec_dist_ohm, n_sections_from_sub } } }
   ```
   Size estimate: ~75 networks × a few hundred bytes ≈ tens of kB — trivially
   bundleable.
2. **Serve it**: new GET `/network-topology?n_id=` endpoint in `main.py`
   returning the pre-built JSON from `data/` (no OpenDSS, no worker pool —
   instant). Bundling into the frontend build is also possible, but the API
   endpoint keeps one source of truth next to the zips.
3. **Frontend**: new `NetworkExplorer.vue` component replacing the static
   `overview_urban.png` thumbnail — an SVG single-line diagram rendered from
   the JSON (plain Vue SVG bindings; no new heavy dependency needed):
   - MV buses/lines drawn from buscoords; primary substation marked.
   - Each LV network drawn as a node sized by house count, coloured by
     selection state.
   - Hover/click a node → side panel with the per-feeder table (houses,
     lengths, distances) and transformer rating.
4. Keep the matplotlib `mv_highlevel` result plot untouched (it shows
   *results*; this shows *inputs*).

### Tests

- **Parser unit tests** (`tests/test_topology_builder.py`): run the builder
  against the real zips; assert (a) 75 networks for 1060, (b) house counts for
  a hand-counted network (1125: 55+31+39+75 = 200), (c) every load bus is
  reachable from the transformer bus (graph is connected), (d) all distances
  positive and < 2 km sanity bound, (e) JSON matches the committed file
  (regeneration guard — fails if zips and JSON drift apart).
- **Cross-check against OpenDSS** (slow test, marked): compile network 1125
  with `dss-python`, use `AllBusDistances`/energymeter registers to
  independently obtain bus distances; assert agreement within ~1 m. This
  validates the traversal against the engine itself.
- **API test**: `/network-topology?n_id=1060` returns 200 + schema-valid JSON
  (pydantic response model); 422 on bad n_id.
- **Frontend**: component test that a click on an LV node with `custom` mode
  active toggles the ID in `lv_options.lv_selected` (see Feature 3).

---

## 2. Feature 2 — confirm 3-phase feeders; capture phase unbalance

### Verdict: confirmed, and the most scientifically valuable of the four

**Confirmation:** yes — all LV feeder mains are 3-phase and houses are
single-phase loads spread across the three phases (verified in the DSS files,
§0). OpenDSS is already solving the unbalanced system every run; the results
pipeline just discards two of the three phases.

For EV work this matters directly: clustered single-phase 7 kW chargers on one
phase are exactly what drives voltage unbalance complaints, and almost no
public web tool shows this. Cheap to add, differentiating.

### What to report (per detailed LV network, per half hour)

- **VUF %** (IEC true definition, |V2|/|V1|) at the LV busbar — the DSS
  `SeqVoltages` per transformer is already extracted in `record_solution`
  under `full=True` (`sln.Vsb`); promote it to the always-on set (it is one
  `getObjAttr` pass over a handful of transformers — microseconds).
  Plot against the ER P29 / EN 50160 guide levels (1.3 % / 2 %).
- **Per-phase voltage envelopes**: extend `_build_result_index` to keep the
  YNode indices of *all* connected phases per load (it currently keeps one);
  `record_solution` already fetches the full `YNodeVarray` once per step, so
  the extra cost is pure indexing. Group loads by connected phase → min/max
  envelope per phase, reusing the existing `fillplot` style.
- Optional third metric, near-free: max phase-to-phase voltage spread at the
  busbar.

### Implementation steps

1. `funcsTuring._build_result_index`: build per-phase index arrays
   (`_lds_phase_yzidx[phase]`) alongside the existing phase-A one; keep the
   old key so existing plots are untouched.
2. `funcsTuring.record_solution`: always record `Vsb_seq` (V0,V1,V2 per
   secondary substation) and per-phase load voltages for the detailed
   networks.
3. `azure_mockup.py`: new plot `lv_unbalance_png` — top panel VUF % vs time
   (one line per detailed network, dashed guides at 1.3 %/2 %); bottom panel
   per-phase envelopes for the plotted networks. New CSV
   `lv_unbalance_data` (time × network VUF, plus per-phase min/max).
4. `main.py`: add both to the response dict; frontend: new result card in the
   existing results grid + download link (pattern already exists for the
   other four CSVs).
5. Only for detailed networks — exactly what was asked (lumped networks have
   no LV representation to be unbalanced).

### Tests

- **Analytical fixture**: tiny 3-bus DSS case built in-test with a known
  unbalanced load; assert computed VUF equals the hand-derived
  Fortescue value (|V2|/|V1|) to 6 decimals. This pins the maths, not just
  the plumbing.
- **Symmetry test**: run one LV network with all loads forced equal on all
  three phases (balanced) → VUF ≈ 0; then move all load to phase 1 → VUF
  strictly larger. Monotonicity beats magic-number assertions.
- **Pipeline test**: full `/simulate` (dry_run=False path via the existing
  `test_localrun.py` pattern) asserting `lv_unbalance` key present, PNG
  decodes, CSV parses to 48 rows.
- **Regression guard**: existing baselines in `regression_harness/` must be
  bit-identical — this feature only *adds* outputs. Run the harness before
  merging.

---

## 3. Feature 3 — choose networks from a map

### Verdict: yes as an interactive schematic; a *geographic* map is not possible

Be aware of the hard limit: these are the Manchester LVNS + UKGDS-style
**synthetic/anonymised** models. Coordinates are local x,y (LV in metres from
an arbitrary origin, MV schematic units) with **no latitude/longitude and no
projection** — the deakin-HV-LV-models PDF describes them as representative,
not geo-located. A Leaflet/OpenStreetMap view would require inventing a
geography the models don't have, and would mislead users into reading street
addresses into synthetic feeders. Recommendation: don't fake it.

What *is* achievable — and I'd argue is what you actually want — is making the
Feature-1 SVG diagram **selectable**:

1. In `custom` LV mode, LV nodes on the diagram become click-targets that
   toggle membership of `lv_options.lv_selected` (same state the chip list
   drives today; chips and map stay in sync automatically because they share
   the store).
2. Enforce the 2–5 selection rule visually (6th click shakes/does nothing +
   tooltip; vuelidate rule already exists).
3. In preset modes (`near-sub`, `near-edge`, `mixed`) the diagram highlights
   the preset's networks read-only — this makes the presets *self-explanatory*
   for the first time (you can finally see what "near-edge" means).
4. Optional (+1 day): distance-to-substation colour ramp on the LV nodes, so
   the near-sub/near-edge concept is visible at a glance.

### Tests

- Component tests: click toggles selection in custom mode; click is inert in
  preset mode; 6th selection rejected; map highlight matches
  `/lv-network-defaults` response for each preset.
- E2E smoke (existing dev-mock-api.js pattern): select 2 networks on the map →
  submit → request URL contains the same `lv_list`.

---

## 4. Feature 4 — LV transformer settings (scaling, OLTC setpoint, bandwidth)

> **DECISION (Myriam, 2026-07-09): not implementing this feature.**
> Rationale: scaling up LV transformers presents them as a planning option,
> but the tool doesn't establish how much headroom ("envelope") exists
> upstream — whether the MV transformer and feeders could actually support
> larger LV transformers, nor the physical/cost feasibility of the swap.
> Offering the knob without that context could invite conclusions the model
> can't support.
>
> Technical footnotes for if this is ever revisited:
> - The simulation *would* still show the upstream consequence: the primary
>   transformer loading plots (`trn_powers`, `pmry_loadings`) reflect any
>   extra flow, so an MV overload caused by relaxed LV constraints would be
>   visible. What the tool cannot answer is the real-world planning question
>   (asset headroom, cost, physical envelope) — which is the basis of the
>   decision.
> - Scaling would only ever have applied to the 1–5 networks modelled in
>   detail (the other ~70 are lumped loads with no transformer), so the
>   system-level effect on MV loading is small either way.
> - The design and test plan below remain valid if the feature is revived,
>   including the symlinked-cache gotcha (§0), which applies to *any* future
>   LV-file modification, not just this feature.

### Original analysis (kept for reference): feasible; mirror the MV parameters, but default the OLTC to *off*

Two physically different asks bundled together:

- **kVA scaling** — uncontroversial, symmetric with `xfmr_scale`.
- **OLTC setpoint/bandwidth** — real distribution 11/0.416 kV transformers
  have **off-load taps only**; an LV OLTC is a "smart transformer" what-if
  (a perfectly good research question for EV hosting capacity — but it must
  be opt-in so the default simulation stays faithful to today's networks and
  to all existing baselines).

### Design

New API parameters (validated like their MV twins):

| Param | Default | Range | Meaning |
|---|---|---|---|
| `lv_xfmr_scale` | 1.0 | 0.5–4 | multiplies each detailed LV transformer's kVA (same convention as MV: %R/XHL are on the kVA base, so per-unit impedance is preserved) |
| `lv_oltc_enable` | false | bool | fit an OLTC to detailed LV transformers |
| `lv_oltc_setpoint` | 1.00 | 0.95–1.10 pu | RegControl `vreg` (converted with `ptratio` for the 240 V winding) |
| `lv_oltc_bandwidth` | 0.013 | 0.01–0.05 pu | RegControl `band` |

With defaults, the compiled circuit must be **identical to today's** — that is
the core regression contract.

### Implementation steps

1. **Do not touch the LV files** (symlinked shared cache, §0 gotcha). Instead
   add `turingNet.apply_lv_xfmr_settings(nd)` called in `azure_mockup.py`
   after `turingNet(...)` compiles and before `run_dss_lds`:
   - enumerate detailed LV transformers via the existing `d.TRN` +
     `self.xfmri.sdry` index (already used for `Ssec`);
   - `Edit Transformer.<name> kVAs=[…]` for scaling (read current kVA via the
     DSS API, multiply — same semantics as `dss_value_update(val_mult=…)`);
   - if enabled: `New RegControl.reg_<name> transformer=<name> winding=2
     vreg=<setpoint·240/ptratio…> band=… ptratio=…` — the LV winding is
     0.416 kV wye → 240.2 V phase-neutral, so `ptratio=1` with vreg in volts
     on a 240 V base is the cleanest encoding (state this in the inline
     comment). Transformer defaults (MinTap 0.9, MaxTap 1.1, NumTaps 32)
     already permit tapping.
2. **main.py**: four new Query params with the ge/le bounds above, passed into
   `parameters["network_data"]` (`lv_xfmr_scale`, `lv_oltc_*`), matching how
   the MV trio flows; `azureOptsXmpls.run_dict0` gains the keys with `None`
   defaults (existing "None = leave alone" convention in `dss_value_update`).
3. **Frontend**: extend the existing "Advanced network parameters" card with
   an "LV transformers (detailed networks only)" subsection — three sliders +
   one toggle, cloned from the MV rows, with `input-details` tooltips
   explaining (a) it applies only to the networks modelled in detail and
   (b) LV OLTC is an emerging/what-if technology. Setpoint/bandwidth sliders
   disabled until the toggle is on.
4. **Docs**: CHANGES.md entry + inline `CHANGE` markers, per repo convention.

### Tests

- **No-op regression (the critical one)**: with defaults, run the
  `regression_harness` baseline comparison — outputs bit-identical.
- **Scaling applied**: compile, apply `lv_xfmr_scale=2`, read back each
  detailed transformer's kVA via the DSS API → exactly 2× the value parsed
  from its `Transformers_mod*.txt`; MV transformer kVA unchanged.
- **OLTC regulates**: pick a network/profile whose busbar voltage at fixed tap
  sits below 0.98 pu under high EV load (`lv_ev_pen=1`); enable OLTC with
  setpoint 1.02, band 0.013 → assert (a) recorded LV tap positions change
  during the day, (b) busbar voltage stays within setpoint ± band/2 whenever
  the solve converged and the tap isn't railed, (c) with the OLTC disabled the
  same run violates that band (proves the assertion has teeth).
- **Bandwidth monotonicity**: wider band ⇒ tap-change count (Σ|Δtap|) is
  non-increasing. Physics-based, no magic numbers.
- **API validation tests**: out-of-range values → 422 (pattern exists in
  `test_api_validation.py`); `dry_run=True` accepts the new params.
- **Interaction test**: MV OLTC and LV OLTC both enabled → both converge
  (no control-loop fighting) across all 48 steps; assert converged count = 48.

---

## 5. Feature 5 — surface non-convergence to the user (added 2026-07-09)

**In scope by decision.** Found while reviewing the code for the features
above: when one or more of the 48 power-flow solves fails to converge,
`run_dss_simulation` (azure_mockup.py) only *logs* "results may be invalid" —
the API response and the UI carry no trace of it. A user pushing extreme
EV/PV penetrations (exactly the scenarios this tool invites) can get
confident-looking, physically meaningless plots.

### Implementation steps

1. **Backend**: `_run_dss_simulation_inner` already computes
   `n_not_converged`; add it (and the affected time-step indices) to the
   `results` dict, and pass it through `main.py` into the response as e.g.
   `"convergence": {"n_steps": 48, "n_failed": 2, "failed_steps": [37, 38]}`.
2. **Frontend**: amber warning banner above the results grid when
   `n_failed > 0` — plain-language text ("2 of 48 half-hours did not reach a
   valid electrical solution; treat results between 18:30–19:30 with
   caution"), with an `input-details` tooltip explaining what convergence
   means in simple terms.
3. Optionally shade the affected time windows on the time-series plots
   (matplotlib `axvspan` in the plot helpers) so the invalid region is
   visible on the images themselves — the images are also what users
   download and screenshot.

### Tests

- Unit: craft a parameter set known to diverge (or monkeypatch
  `SLN.Converged` on chosen steps) → response contains the correct
  `convergence` block; fully-converged run → `n_failed == 0` and no banner.
- Frontend component test: banner renders when `n_failed > 0`, absent
  otherwise.
- Regression: converged baseline runs unchanged apart from the new response
  key.

## 6. Suggested build order & effort

| Phase | Content | Effort* |
|---|---|---|
| A | Non-convergence surfacing (§5) | ~0.5 day |
| B | Topology builder + JSON + endpoint + tests (§1.1–1.2) | ~1.5 days |
| C | NetworkExplorer SVG, read-only (§1.3) | ~1.5 days |
| D | Click-to-select + preset highlighting (§3) | ~1–2 days |
| E | Unbalance extraction + plot + CSV + tests (§2) | ~2 days |

B→C→D is one coherent feature ("see and pick your networks"); A and E are
independent of it and of each other. A first: it is the cheapest and it
protects the validity of every result, including the demos of the new
features.

*"Effort" here is a conventional human-developer estimate used for relative
sizing — it is **not** compute time or agent runtime. Implemented with Claude
Code, each phase is typically one working session (roughly an hour or two of
wall-clock, most of it running the test suites and regression harness); the
real bottleneck is human review of the changes and validation of the results,
which is where these estimates come from.

## 7. Critical assessment — is this the right list?

Worth it? **#1+#3 yes** — the selector is currently the least explainable part
of the UI (opaque 4-digit IDs, a static PNG); making the presets visible and
the custom mode clickable directly serves the app's stated mission
(democratising network analysis). **#2 yes, and it's the sleeper hit** — the
model already solves unbalance; you're paying the computation and throwing
the answer away, while single-phase EV charging unbalance is precisely a VGI
question and a publishable differentiator. **#4 was the weakest of the
original four and has since been dropped** (see §4) — the reasoning being
that the tool cannot establish the upstream (MV) headroom or real-world
feasibility that would make the knob meaningful. **#5 (non-convergence) was
added** — it is a scientific-integrity fix and cheaper than everything else
here.

One further candidate for later, deliberately left out of scope for now:

- **Progress feedback / async simulation.** Simulations take tens of seconds
  to minutes; the UI currently just spins, and the 600 s server timeout is
  invisible to the user. Even a coarse staged progress indicator would cut
  perceived failure rates. (Bigger lift; consider after A–E.)

Also noted while reviewing (not urgent): phase allocation of EVs is currently
implicit — once #2 lands, an obvious follow-up is letting users skew EV
placement onto one phase to study worst-case unbalance; the plumbing from #2
makes that a small increment.
