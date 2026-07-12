# Front-end redesign — implementation handoff

Self-contained spec for implementing the EVENT front-end redesign. Written 2026-07-07 by a
Claude Fable session that reviewed the full front end; the visual mockup lives at
https://claude.ai/code/artifact/7c7d6821-9bc8-46da-850f-1a4b84943e62 (fetch it to see the
target design). **No backend/API changes are needed for any item below.**

## Ground rules (user preferences)
- Document every change in `CHANGES.md` and mark edited code with inline comment markers.
- Explain concepts simply when reporting back; the user is an EV/grid expert, not a Vue expert.
- Work in THIS folder (`vehicle-grid-integration-webapp-fixed`). NB: `.claude/launch.json`
  currently points at `../vehicle-grid-integration-webapp-v2` — update it to this folder
  before using preview tools.

## Stack & how to run
- Vue 3 + Vue CLI 4 (webpack 4), Bootstrap 4 CSS, Vuelidate. No TypeScript.
- Dev server: `NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve --port 8080`
  (the legacy-provider flag is required on modern Node).
- API base URL comes from `VUE_APP_API_URL` in `.env.development` / `.env.production`.
  If the live API is unreachable during dev, mock `/get-options`, `/lv-network`,
  `/lv-network-defaults`, `/simulate` (see `vgi_api/` for FastAPI schemas and
  `vgi_api/tests/dsssimulation_*.json` for real response payloads to mock with).

## Key files
- `src/views/SimulateNetworkAPI.vue` (693 lines) — the whole simulate page: form, fetch, results.
- `src/components/SelectProfile.vue` — per-technology profile dropdown + csv upload + penetration.
- `src/components/InputDetails.vue` — "?" info popover. `src/components/WalkthroughModal.vue` — modal to retire.
- `src/layouts/NavBar.vue`, `src/views/Home.vue`, `src/views/Resources.vue`, `src/router/index.js`.
- `src/assets/vgi_styles.css` — small global CSS (box-main pastel boxes to be replaced by tokens).

## API contract (do not change; reuse as-is)
- `GET /get-options?option_type={mv-solar-pv|mv-fcs|lv-smartmeter|lv-ev|lv-pv|lv-hp}` → JSON list of profile names (includes "None" and "csv").
- `GET /lv-network?n_id={1060|1061}` → `{networks: [ids]}`; `GET /lv-network-defaults?n_id&lv_default={near-sub|near-edge|mixed}` → `{networks: [ids]}`.
- `POST /simulate?{params}` with optional multipart csv. Response JSON keys: base64 plots
  `lv_comparison, trn_powers, pmry_loadings, mv_voltages, mv_highlevel_clean, mv_highlevel,
  profile_options, profile_options_dgs, profile_options_fcs` plus CSV strings
  `lv_comparison_data, trn_powers_data, primary_loadings_data, mv_voltages_data`.
- Param ranges: xfmr_scale 0.5–4 (default 1.0); oltc_setpoint 0.95–1.10 pu (1.04);
  oltc_bandwidth 0.01–0.05 pu (0.013); rs_pen 0–1 (0.8); penetrations 0–1 (API takes decimals —
  UI shows %, divide by 100 before sending).

## Design tokens
CSS variables, light/dark: paper #F6F7F5/#121815, card #FFF/#1B2420, ink #1C2620/#E8EDE9,
muted #5C6B62/#93A398, line #DCE3DD/#2A3630, accent (grid green) #0E7C5B/#3FBF8F,
wire blue #2B5EA7/#7BA8E4, warn amber #C2711B/#E0A050, breach red #B23A31/#E07268.
Semantic colours (green/amber/red) are reserved for voltage & loading verdicts only.
Type: Avenir Next / system sans; monospace (`ui-monospace`) with `tabular-nums` for all
parameter values and KPI numbers.

## Phases — implement in order, verify each before the next

### P1 — humane inputs & robust errors (SimulateNetworkAPI.vue, SelectProfile.vue)
1. Penetration: 0–1 decimal input → % slider (0–100, step 5) with live mono value; convert to
   decimal in `appendProfileParams`.
2. Each technology row: "None" profile option → on/off toggle; when off, grey the row and send
   profile "None".
3. LV network selection: `<select multiple>` → clickable ID chips (2–5 enforced, live counter);
   preset sets (near-sub/near-edge/mixed/custom) as a segmented control.
4. Network ID dropdown ("1060") → segmented control labelled "Urban 11 kV" / "Urban–rural 11 kV".
5. OLTC setpoint/bandwidth, xfmr_scale, rs_pen → range sliders with min/max/unit visible,
   folded in a collapsed "Advanced network parameters" disclosure showing current values inline.
6. Errors: replace all `alert()` with an inline dismissible banner; add `.catch`/`.finally` to the
   `/simulate` fetch so `isLoading` always resets (today a network failure leaves the spinner on).

### P2 — results lead with the answer
1. Parse returned CSVs client-side: min/max customer voltage from `lv_comparison_data`, peak
   transformer utilisation % from `trn_powers_data`, MV range from `mv_voltages_data`.
2. Three KPI cards above the figures with verdict pills: LV voltage vs statutory 0.94–1.10 pu
   (MV limits 0.94–1.06 pu); loading <80% ok / 80–100% warning / >100% breach.
3. One plain-English interpretation sentence (which network, when, what to try).
4. Group the 9 figures into 4 collapsible sections: Voltages, Transformer & feeder loadings,
   Network maps, Profiles used. Keep per-figure csv download buttons and info popovers.

### P3 — structure
1. Scenario preset chips at top (front-end constants): Today's network (EV 10%, PV 10%, HP 0);
   2030 high EV (EV 60%, PV 30%, HP 20%, FC on); Solar suburb (PV 70%, EV 20%); Electric
   heating winter (HP 60%, smart-meter Jan profile); Blank/custom.
2. Sticky right sidebar: scenario summary lines + Run button + "typically under a minute";
   collapses below the form on mobile.
3. Merge Home into Simulate (EVENT title + one-liner at top); delete the Home route and
   "Build a Network" button; retire WalkthroughModal (move its content to a "How it works" page).
4. Apply design tokens; replace pastel `box-main` borders; number the sections 1/2 + Run.
5. Delete dead code: `rawJson`, `isShowJson`, commented-out GitHub-links block.

### P4 — polish (optional)
Previous-run comparison (keep last results + verdict pill in memory), network map thumbnail on
selection (assets already in `src/assets/images/`), drag-and-drop CSV upload.

## Verification checklist (each phase)
- `npm run lint` passes; dev server starts with the legacy-provider flag.
- Preview at :8080 — form renders, all controls operable by keyboard; no console errors.
- With API (or mocks): change every control → run → results render; invalid custom LV selection
  (<2 or >5) blocks submit with a visible message; kill network mid-run → banner appears and
  spinner stops.
- Penetration slider at 60% sends `..._pen=0.6` (check the request URL in devtools/preview network).
- Dark mode and a 375 px viewport both render correctly (P3 onward).
