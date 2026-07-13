<template>
  <!-- REDESIGN 2026-07: single-page Simulate. Home merged in at top (P3),
       scenario presets + sticky summary sidebar, humane inputs (P1),
       results-lead-with-the-answer KPI cards (P2). -->
  <div class="evt-wrap">
    <!-- Merged Home header -->
    <header class="evt-header">
      <div class="evt-eyebrow">EVENT</div>
      <h1>
        Build and simulate an electricity distribution network with EVs, PVs and
        heat pumps
      </h1>
      <p class="evt-lede">
        Pick a scenario or configure your own, then run the simulation to see
        whether the network copes — voltages and transformer loading against
        their statutory limits.
        <router-link :to="{ name: 'HowItWorks' }">How it works</router-link>
      </p>
    </header>

    <form id="config" ref="config" @submit.prevent class="evt-layout">
      <div class="evt-main">
        <!-- ---- Scenario presets (P3.1) ---- -->
        <div class="evt-card evt-presets-card">
          <span class="evt-lbl">Start from a scenario</span>
          <div class="evt-presets">
            <button
              v-for="(p, key) in presets"
              :key="key"
              type="button"
              class="evt-chip"
              :class="{ on: activePreset === key }"
              @click="applyPreset(key)"
            >
              {{ p.label }}
            </button>
          </div>
        </div>

        <!-- ---- Step 1: choose the network ---- -->
        <div class="evt-card">
          <h2 class="evt-step">
            <span class="evt-step-n">1</span> Choose the network
          </h2>

          <div class="evt-field">
            <span class="evt-lbl">Network type</span>
            <div class="evt-seg" role="group" aria-label="Network type">
              <button
                type="button"
                :class="{ on: network_options.n_id === 1060 }"
                @click="setNetwork(1060)"
              >
                Urban 11&nbsp;kV
              </button>
              <button
                type="button"
                :class="{ on: network_options.n_id === 1061 }"
                @click="setNetwork(1061)"
              >
                Urban–rural 11&nbsp;kV
              </button>
            </div>
          </div>

          <!-- Network map & LV selector — always visible; this *is* the main
               way to explore the network and pick LV areas. -->
          <div class="evt-field">
            <div class="evt-map-head">
              <span class="evt-lbl evt-map-lbl">
                Network map &amp; LV network selector
                <input-details
                  inputName="Network map"
                  inputInfo="An interactive map of the chosen MV network. Each circle is an LV network (a neighbourhood); its size tracks the number of houses. Click nodes to choose which LV networks are modelled in detail. F1, F2… label the primary feeders leaving the substation."
                />
              </span>
              <span class="evt-map-cta">
                <i class="bi bi-hand-index-thumb"></i>
                interactive — hover &amp; click the nodes
              </span>
            </div>
            <div class="evt-thumb evt-thumb-explorer">
              <network-explorer
                :topology="topology"
                :selected="lv_options.lv_selected"
                :available="lv_options.lv_list"
                :mode="lv_options.lv_default"
                @toggle="toggleLvId"
              />
              <p v-if="lv_options.lv_default === 'custom'" class="evt-map-hint">
                Click nodes to choose 2–5 LV networks to model in detail.
              </p>
              <p v-else class="evt-map-hint">
                Highlighted nodes are the “{{ lvLabel(lv_options.lv_default) }}”
                preset. Click any node to start customising from it.
              </p>
            </div>
          </div>

          <div class="evt-field">
            <span class="evt-lbl">
              LV areas modelled in detail
              <input-details
                inputName="LV areas modelled in detail"
                inputInfo="Choose which low-voltage neighbourhoods are simulated in full. Presets pick a representative spread; 'Custom' lets you select 2–5 network IDs."
              />
            </span>
            <div class="evt-seg" role="group" aria-label="LV selection preset">
              <button
                v-for="opt in ['near-sub', 'near-edge', 'mixed', 'custom']"
                :key="opt"
                type="button"
                :class="{ on: lv_options.lv_default === opt }"
                @click="setLvDefault(opt)"
              >
                {{ lvLabel(opt) }}
              </button>
            </div>

            <!-- Preset mode: show the auto-selected IDs read-only.
                 Custom mode: full available list in a scrollable picker. -->
            <div
              class="evt-lvchips"
              :class="{
                'evt-lvchips-scroll': lv_options.lv_default === 'custom'
              }"
            >
              <button
                v-for="id in lv_options.lv_default === 'custom'
                  ? lv_options.lv_list
                  : lv_options.lv_selected"
                :key="id"
                type="button"
                class="evt-idchip"
                :class="{ on: lv_options.lv_selected.includes(id) }"
                :disabled="lv_options.lv_default !== 'custom'"
                @click="toggleLvId(id)"
              >
                {{ id }}
              </button>
            </div>
            <div class="evt-lvcount">
              {{ lv_options.lv_selected.length }} selected<span
                v-if="lv_options.lv_default === 'custom'"
              >
                · choose 2 to 5</span
              >
            </div>
            <div
              v-for="error of v$.lv_options.lv_selected.$errors"
              :key="error.$uid"
              class="text-danger evt-inline-err"
            >
              {{ error.$message }}
            </div>
          </div>

          <!-- Advanced network parameters (P1.5) -->
          <div class="evt-advanced">
            <button
              type="button"
              class="evt-adv-toggle"
              @click="showAdvanced = !showAdvanced"
            >
              <i class="bi bi-sliders"></i>
              <!-- CHANGE(round2-3): title as an explicit two-line block ("MV
                   advanced" / "network parameters") frees enough width for
                   the summary to fit on one line without the horizontal
                   scrollbar from §20. -->
              <span class="evt-adv-label"
                >MV advanced<br />network parameters</span
              >
              <span class="evt-adv-chevron">{{
                showAdvanced ? "▾ hide" : "▸ show"
              }}</span>
              <span v-if="!showAdvanced" class="evt-adv-summary">
                scaling ×{{ network_options.xfmr_scale }} · OLTC
                {{ network_options.oltc_setpoint }} pu · band
                {{ network_options.oltc_bandwidth }} pu · residential
                {{ Math.round(network_options.rs_pen * 100) }}%
              </span>
            </button>
            <div v-if="showAdvanced" class="evt-adv-body">
              <div class="evt-slider-row">
                <label
                  >MV transformer scaling
                  <input-details
                    inputName="MV transformer scaling"
                    inputInfo="Multiplies the nominal power rating of the primary (HV/MV) transformer, allowing more demand before the substation overloads."
                    inputValues="0.5 to 4."
                  />
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="4"
                  step="0.1"
                  v-model.number="network_options.xfmr_scale"
                  @input="markCustom"
                />
                <span class="evt-mono"
                  >×{{ network_options.xfmr_scale.toFixed(1) }}</span
                >
              </div>
              <div
                v-for="error of v$.network_options.xfmr_scale.$errors"
                :key="error.$uid"
                class="text-danger evt-inline-err"
              >
                {{ error.$message }}
              </div>

              <div class="evt-slider-row">
                <label
                  >MV transformer OLTC set point
                  <input-details
                    inputName="MV transformer OLTC set point"
                    inputInfo="Target voltage (per-unit) held on the MV side of the primary substation transformer by its on-load tap changer."
                    inputValues="0.95 to 1.10 pu."
                  />
                </label>
                <input
                  type="range"
                  min="0.95"
                  max="1.10"
                  step="0.005"
                  v-model.number="network_options.oltc_setpoint"
                  @input="markCustom"
                />
                <span class="evt-mono"
                  >{{ network_options.oltc_setpoint.toFixed(3) }} pu</span
                >
              </div>
              <div
                v-for="error of v$.network_options.oltc_setpoint.$errors"
                :key="error.$uid"
                class="text-danger evt-inline-err"
              >
                {{ error.$message }}
              </div>

              <div class="evt-slider-row">
                <label
                  >MV transformer OLTC bandwidth
                  <input-details
                    inputName="MV transformer OLTC bandwidth"
                    inputInfo="The transformer tap only changes when voltage moves outside setpoint ± bandwidth. Wider means the substation voltage varies more before correcting."
                    inputValues="0.01 to 0.05 pu."
                  />
                </label>
                <input
                  type="range"
                  min="0.01"
                  max="0.05"
                  step="0.001"
                  v-model.number="network_options.oltc_bandwidth"
                  @input="markCustom"
                />
                <span class="evt-mono"
                  >{{ network_options.oltc_bandwidth.toFixed(3) }} pu</span
                >
              </div>
              <div
                v-for="error of v$.network_options.oltc_bandwidth.$errors"
                :key="error.$uid"
                class="text-danger evt-inline-err"
              >
                {{ error.$message }}
              </div>

              <div class="evt-slider-row">
                <label
                  >Residential load share
                  <input-details
                    inputName="Proportion residential loads"
                    inputInfo="Share of network load that is residential (the rest is industrial &amp; commercial)."
                    inputValues="0% to 100%."
                  />
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  v-model.number="network_options.rs_pen"
                  @input="markCustom"
                />
                <span class="evt-mono"
                  >{{ Math.round(network_options.rs_pen * 100) }}%</span
                >
              </div>
              <div
                v-for="error of v$.network_options.rs_pen.$errors"
                :key="error.$uid"
                class="text-danger evt-inline-err"
              >
                {{ error.$message }}
              </div>
            </div>
          </div>
        </div>

        <!-- ---- Step 2: add low-carbon technologies ---- -->
        <div class="evt-card">
          <h2 class="evt-step">
            <span class="evt-step-n">2</span> Add low-carbon technologies
          </h2>

          <span class="evt-lbl evt-group-lbl">In homes (LV connected)</span>
          <select-profile
            v-model:profileOptions="profile_options.lv_electric_vehicle"
            v-model:penValidation="
              v$.profile_options.lv_electric_vehicle.penetration.$errors
            "
            title="Electric vehicles"
            @change="markCustom"
          ></select-profile>
          <select-profile
            v-model:profileOptions="profile_options.lv_photovoltaic"
            v-model:penValidation="
              v$.profile_options.lv_photovoltaic.penetration.$errors
            "
            title="Solar PV"
            @change="markCustom"
          ></select-profile>
          <select-profile
            v-model:profileOptions="profile_options.lv_heat_pump"
            v-model:penValidation="
              v$.profile_options.lv_heat_pump.penetration.$errors
            "
            title="Heat pumps"
            @change="markCustom"
          ></select-profile>
          <select-profile
            v-model:profileOptions="profile_options.lv_smart_meter"
            title="Household demand"
            @change="markCustom"
          ></select-profile>

          <span class="evt-lbl evt-group-lbl"
            >On the 11&nbsp;kV network (MV connected)</span
          >
          <select-profile
            v-model:profileOptions="profile_options.mv_fcs"
            title="Fast charging station"
            @change="markCustom"
          ></select-profile>
          <select-profile
            v-model:profileOptions="profile_options.mv_solar_pv"
            title="Large solar farm (DG)"
            @change="markCustom"
          ></select-profile>
        </div>

        <!-- ---- Results ---- -->
        <div v-if="responseAvailable" class="evt-card" ref="results">
          <h2 class="evt-step">
            Results<span v-if="ranLabel"> — {{ ranLabel }}</span>
          </h2>

          <!-- Non-convergence warning (P-A) -->
          <div v-if="convergence" class="evt-warn" role="alert">
            <strong>⚠ Some results may be invalid.</strong>
            {{ convergence.n_failed }} of {{ convergence.n_steps }} half-hour
            steps did not reach a valid electrical solution
            <template v-if="convergenceWindows">
              (around {{ convergenceWindows }})</template
            >. This usually means the scenario pushes the network beyond what it
            can physically support — treat the affected time windows with
            caution. The invalid windows are shaded red on the time-series plots
            below.
            <input-details
              inputName="Convergence"
              inputInfo="The simulator solves the power flow independently at each half hour. 'Did not converge' means the equations had no stable solution — typically caused by extreme demand or generation (e.g. very high EV or PV penetration) overwhelming the network. Numbers plotted for those steps are not physically meaningful."
            />
          </div>

          <!-- KPI verdict cards (P2) -->
          <div class="evt-kpis">
            <div class="evt-kpi">
              <div class="evt-kpi-k">
                {{
                  verdicts.lvVoltage.driver === "max"
                    ? "Highest customer voltage"
                    : "Lowest customer voltage"
                }}
              </div>
              <div class="evt-kpi-v evt-mono">
                {{ fmt(verdicts.lvVoltage.value, 3) }} pu
              </div>
              <span class="evt-pill" :class="verdicts.lvVoltage.pillClass">{{
                verdicts.lvVoltage.label
              }}</span>
            </div>
            <div class="evt-kpi">
              <div class="evt-kpi-k">Peak transformer loading</div>
              <div class="evt-kpi-v evt-mono">
                {{ fmt(verdicts.transformer.peak, 0) }}%
              </div>
              <span class="evt-pill" :class="verdicts.transformer.pillClass">{{
                verdicts.transformer.label
              }}</span>
            </div>
            <div class="evt-kpi">
              <div class="evt-kpi-k">MV voltage range</div>
              <div class="evt-kpi-v evt-mono">
                {{ fmt(verdicts.mvVoltage.min, 3) }}–{{
                  fmt(verdicts.mvVoltage.max, 3)
                }}
                pu
              </div>
              <span class="evt-pill" :class="verdicts.mvVoltage.pillClass">{{
                verdicts.mvVoltage.label
              }}</span>
            </div>
          </div>
          <p class="evt-interpret">{{ verdicts.interpretation }}</p>

          <!-- Grouped figures (P2.4) -->
          <div class="evt-groups">
            <div v-for="g in figureGroups" :key="g.name" class="evt-group">
              <button
                type="button"
                class="evt-group-head"
                @click="toggleGroup(g.name)"
              >
                <span
                  >{{ openGroups.includes(g.name) ? "▾" : "▸" }}
                  {{ g.name }}</span
                >
                <span v-if="g.badge" class="evt-pill" :class="g.badge.cls">{{
                  g.badge.text
                }}</span>
              </button>
              <div v-if="openGroups.includes(g.name)" class="evt-group-body">
                <div
                  v-for="fig in g.figures"
                  :key="fig.name"
                  class="evt-figure"
                >
                  <div class="evt-figure-head">
                    <span
                      >{{ fig.name }}
                      <input-details
                        v-if="fig.info"
                        :inputName="fig.name"
                        :inputInfo="fig.info"
                        :inputInfo2="fig.info2"
                        :inputValues="fig.values"
                      />
                    </span>
                    <a
                      v-if="fig.data_url"
                      :href="fig.data_url"
                      :download="fig.data_filename"
                      class="evt-csv-link"
                    >
                      <i class="bi bi-download"></i> csv
                    </a>
                  </div>
                  <!-- Native interactive charts (P5) when the figure's CSV
                       parsed; otherwise the matplotlib image below. -->
                  <template
                    v-if="fig.chart && fig.chart.type === 'quantile-grid'"
                  >
                    <div class="evt-chart-grid">
                      <div v-for="p in fig.chart.panels" :key="p.net">
                        <div class="evt-chart-title">
                          LV network {{ p.net }}
                        </div>
                        <quantile-band-chart
                          :quantiles="p.quantiles"
                          :limits="fig.chart.limits"
                          :failed-hours="fig.chart.failedHours"
                          :height="220"
                        />
                      </div>
                    </div>
                  </template>
                  <quantile-band-chart
                    v-else-if="fig.chart && fig.chart.type === 'quantile'"
                    :quantiles="fig.chart.quantiles"
                    :limits="fig.chart.limits"
                    :failed-hours="fig.chart.failedHours"
                    :height="280"
                  />
                  <multi-line-chart
                    v-else-if="fig.chart && fig.chart.type === 'lines'"
                    :series="fig.chart.series"
                    :limits="fig.chart.limits"
                    :failed-hours="fig.chart.failedHours"
                    :unit="fig.chart.unit"
                    :decimals="fig.chart.decimals"
                    :height="280"
                  />
                  <!-- Per-phase figure: user picks which LV network to show. -->
                  <template v-else-if="fig.phaseSelector">
                    <label class="evt-phase-select">
                      LV network
                      <select v-model="phaseNet">
                        <option v-for="id in phaseNetIds" :key="id" :value="id">
                          {{ id }}
                        </option>
                      </select>
                    </label>
                    <img
                      v-if="phaseNet && phasePngs[phaseNet]"
                      :src="'data:image/jpeg;base64,' + phasePngs[phaseNet]"
                      :alt="
                        'Per-phase customer voltages for LV network ' + phaseNet
                      "
                      class="evt-figure-img"
                    />
                  </template>
                  <img
                    v-else
                    :src="'data:image/jpeg;base64,' + fig.plot"
                    :alt="fig.name"
                    class="evt-figure-img"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ---- Sticky scenario summary + Run (P3.2) ---- -->
      <aside class="evt-side">
        <div class="evt-card evt-summary">
          <h3 class="evt-eyebrow">Your scenario</h3>
          <div class="evt-sumline">
            <span>Network</span
            ><b>{{
              network_options.n_id === 1060
                ? "Urban 11 kV"
                : "Urban–rural 11 kV"
            }}</b>
          </div>
          <div class="evt-sumline">
            <span>LV areas</span
            ><b
              >{{ lv_options.lv_selected.length }} ·
              {{ lvLabel(lv_options.lv_default) }}</b
            >
          </div>
          <div class="evt-sumline">
            <span>Electric vehicles</span
            ><b>{{ techSummary("lv_electric_vehicle") }}</b>
          </div>
          <div class="evt-sumline">
            <span>Solar PV</span><b>{{ techSummary("lv_photovoltaic") }}</b>
          </div>
          <div class="evt-sumline">
            <span>Heat pumps</span><b>{{ techSummary("lv_heat_pump") }}</b>
          </div>
          <div class="evt-sumline">
            <span>Household demand</span
            ><b>{{ isOn("lv_smart_meter") ? "on" : "—" }}</b>
          </div>
          <div class="evt-sumline">
            <span>Fast charging</span><b>{{ isOn("mv_fcs") ? "on" : "—" }}</b>
          </div>
          <div class="evt-sumline">
            <span>Solar farm</span><b>{{ isOn("mv_solar_pv") ? "on" : "—" }}</b>
          </div>

          <button
            type="submit"
            class="evt-run"
            :disabled="v$.$errors.length || isLoading"
            @click="fetchAPIData"
          >
            <span v-if="!isLoading">Run simulation</span>
            <span v-else>Simulating…</span>
          </button>
          <div class="evt-run-sub">
            <template v-if="isLoading"
              >In progress · usually under a minute</template
            >
            <template v-else>Typically finishes in under a minute</template>
          </div>

          <!-- Error banner (P1.6) -->
          <div v-if="hasErrors" class="evt-errors" role="alert">
            <strong
              ><i class="bi bi-exclamation-octagon-fill"></i> Cannot run
              yet</strong
            >
            <ul>
              <li v-for="error of v$.$errors" :key="error.$uid">
                {{ prettyProp(error.$property) }}: {{ error.$message }}
              </li>
              <li v-for="csv of invalid_csvs" :key="csv">
                A CSV file is required for {{ csv }}
              </li>
              <li v-for="m of error_messages" :key="m">{{ m }}</li>
            </ul>
          </div>

          <!-- Previous-run memory (P4) -->
          <div v-if="previousRun" class="evt-prev">
            <h3 class="evt-eyebrow">Previous run</h3>
            <div class="evt-sumline">
              <span>{{ previousRun.label }}</span>
              <span class="evt-pill" :class="previousRun.pillClass">{{
                previousRun.verdict
              }}</span>
            </div>
          </div>
        </div>
      </aside>
    </form>

    <div class="evt-logos">
      <img
        class="logo"
        src="../assets/logos/supergen.png"
        alt="Supergen Energy Networks Hub"
      />
      <img
        class="logo"
        src="../assets/logos/turing.png"
        alt="The Alan Turing Institute"
      />
      <img
        class="logo"
        src="../assets/logos/newcastle.png"
        alt="Newcastle University"
      />
      <img
        class="logo"
        src="../assets/logos/lrf.svg"
        alt="Lloyd's Register Foundation"
      />
    </div>
  </div>
</template>

<script>
import SelectProfile from "../components/SelectProfile.vue";
import InputDetails from "../components/InputDetails.vue";
import NetworkExplorer from "../components/NetworkExplorer.vue";
import QuantileBandChart from "../components/charts/QuantileBandChart.vue";
import MultiLineChart from "../components/charts/MultiLineChart.vue";
import {
  parseFigureCsv,
  lvQuantilePanels,
  mvQuantiles,
  lineSeries,
  prettyTransformerName,
  prettyVufName
} from "../components/charts/figureSeries.js";
import useVuelidate from "@vuelidate/core";
import {
  required,
  requiredIf,
  between,
  minLength,
  maxLength
} from "@vuelidate/validators";

// Scenario presets (front-end constants). Numbers are penetration %, booleans on/off.
const PRESETS = {
  today: {
    label: "Today's network",
    techs: {
      lv_electric_vehicle: 10,
      lv_photovoltaic: 10,
      lv_heat_pump: 0,
      lv_smart_meter: true,
      mv_fcs: false,
      mv_solar_pv: false
    }
  },
  ev2030: {
    label: "2030 · high EV",
    techs: {
      lv_electric_vehicle: 60,
      lv_photovoltaic: 30,
      lv_heat_pump: 20,
      lv_smart_meter: true,
      mv_fcs: true,
      mv_solar_pv: false
    }
  },
  solar: {
    label: "Solar suburb",
    techs: {
      lv_photovoltaic: 70,
      lv_electric_vehicle: 20,
      lv_heat_pump: 0,
      lv_smart_meter: true,
      mv_fcs: false,
      mv_solar_pv: true
    }
  },
  heat: {
    label: "Electric heating winter",
    techs: {
      lv_heat_pump: 60,
      lv_electric_vehicle: 10,
      lv_photovoltaic: 0,
      lv_smart_meter: true,
      mv_fcs: false,
      mv_solar_pv: false
    }
  },
  blank: { label: "Blank / custom", techs: {} }
};

export default {
  components: {
    SelectProfile,
    InputDetails,
    NetworkExplorer,
    QuantileBandChart,
    MultiLineChart
  },
  setup() {
    return { v$: useVuelidate({ $autoDirty: true }) };
  },
  data() {
    return {
      presets: PRESETS,
      activePreset: "blank",
      showAdvanced: false,
      network_options: {
        n_id: 1060,
        xfmr_scale: 1.0,
        oltc_setpoint: 1.04,
        oltc_bandwidth: 0.013,
        rs_pen: 0.8
      },
      lv_options: { lv_default: "near-sub", lv_list: [], lv_selected: [] },
      profile_options: {
        mv_solar_pv: { list: [], profile: "None", units: "kW", csv: null },
        mv_fcs: { list: [], profile: "None", units: "kW", csv: null },
        lv_smart_meter: { list: [], profile: "None", units: "kW", csv: null },
        lv_electric_vehicle: {
          list: [],
          profile: "None",
          units: "kW",
          csv: null,
          penetration: 60
        },
        lv_photovoltaic: {
          list: [],
          profile: "None",
          units: "kW",
          csv: null,
          penetration: 30
        },
        lv_heat_pump: {
          list: [],
          profile: "None",
          units: "kW",
          csv: null,
          penetration: 0
        }
      },
      invalid_csvs: [],
      error_messages: [],
      isLoading: false,
      responseAvailable: false,
      verdicts: null,
      figureGroups: [],
      openGroups: ["Voltages"],
      ranLabel: "",
      previousRun: null,
      convergence: null,
      topology: null,
      // Per-phase figures keyed by LV network id, plus the currently shown id.
      phasePngs: {},
      phaseNet: null
    };
  },
  validations() {
    return {
      network_options: {
        xfmr_scale: { required, between: between(0.5, 4) },
        oltc_setpoint: { required, between: between(0.95, 1.1) },
        oltc_bandwidth: { required, between: between(0.01, 0.05) },
        rs_pen: { required, between: between(0, 1) }
      },
      lv_options: {
        lv_selected: {
          required: requiredIf(function() {
            return this.lv_options.lv_default === "custom";
          }),
          maxLength: maxLength(5),
          minLength: minLength(2)
        }
      },
      profile_options: {
        // Penetration is a percentage (0–100) in the UI; converted to a 0–1
        // decimal when the request is built (see appendProfileParams).
        lv_electric_vehicle: { penetration: { between: between(0, 100) } },
        lv_photovoltaic: { penetration: { between: between(0, 100) } },
        lv_heat_pump: { penetration: { between: between(0, 100) } }
      }
    };
  },
  computed: {
    hasErrors() {
      return (
        this.v$.$errors.length ||
        this.invalid_csvs.length ||
        this.error_messages.length
      );
    },
    // Human-readable list of the non-converged time windows, e.g.
    // "18:30, 19:00". Each failed step is a half-hour clock time in hours.
    convergenceWindows() {
      if (!this.convergence) return "";
      return this.convergence.failed_hours
        .map(h => {
          const hh = Math.floor(h);
          const mm = Math.round((h - hh) * 60);
          return (
            String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0")
          );
        })
        .join(", ");
    },
    // LV network ids that have a per-phase figure (the simulated networks).
    phaseNetIds() {
      return Object.keys(this.phasePngs);
    }
  },
  mounted() {
    const jobs = [
      ["mv-solar-pv", "mv_solar_pv"],
      ["mv-fcs", "mv_fcs"],
      ["lv-smartmeter", "lv_smart_meter"],
      ["lv-ev", "lv_electric_vehicle"],
      ["lv-pv", "lv_photovoltaic"],
      ["lv-hp", "lv_heat_pump"]
    ].map(([opt, key]) =>
      this.getProfileOptions(opt).then(list => {
        this.profile_options[key].list = list || [];
      })
    );
    Promise.all(jobs).then(() => this.applyPreset("today"));
    this.updateLVNetworksList();
    this.updateTopology();
  },
  methods: {
    // -------- scenario helpers --------
    lvLabel(opt) {
      return (
        {
          "near-sub": "Near substation",
          "near-edge": "Near edge",
          mixed: "Mixed",
          custom: "Custom"
        }[opt] || opt
      );
    },
    firstReal(key) {
      return (
        (this.profile_options[key].list || []).filter(o => o !== "None")[0] ||
        "None"
      );
    },
    isOn(key) {
      const p = this.profile_options[key].profile;
      return p !== "None" && p != null;
    },
    techSummary(key) {
      if (!this.isOn(key)) return "—";
      const pen = this.profile_options[key].penetration;
      return pen !== undefined ? pen + "%" : "on";
    },
    // A genuine user edit (not an async data load) drops the named preset.
    markCustom() {
      this.activePreset = "blank";
    },
    applyPreset(key) {
      const preset = this.presets[key];
      Object.keys(this.profile_options).forEach(tkey => {
        const spec = preset.techs[tkey];
        const opts = this.profile_options[tkey];
        if (spec === undefined || spec === false || spec === 0) {
          opts.profile = "None";
          if (opts.penetration !== undefined) opts.penetration = 0;
        } else {
          opts.profile = this.firstReal(tkey);
          if (opts.penetration !== undefined)
            opts.penetration = spec === true ? 100 : spec;
        }
      });
      this.activePreset = key;
    },
    setNetwork(nid) {
      this.markCustom();
      this.network_options.n_id = nid;
      this.updateLVNetworksList();
      this.updateTopology();
    },
    setLvDefault(opt) {
      this.markCustom();
      this.lv_options.lv_default = opt;
      this.updatePreselectedLVNetworksList();
    },
    toggleLvId(id) {
      this.markCustom();
      // Clicking a map node while a preset is active hands the preset's
      // selection over to "custom" so the user can tweak it directly.
      // (Assigned directly rather than via setLvDefault, which would refetch
      // and overwrite the current selection.)
      if (this.lv_options.lv_default !== "custom")
        this.lv_options.lv_default = "custom";
      const sel = this.lv_options.lv_selected.slice();
      const i = sel.indexOf(id);
      if (i >= 0) {
        // Already selected: plain deselect.
        sel.splice(i, 1);
      } else {
        // CHANGE(round2-2): at the 5-network cap, selecting a new network no
        // longer blocks the click — it drops the earliest-selected network
        // (FIFO) and adds the new one. sel[0] is always the oldest because
        // every addition below pushes to the end.
        if (sel.length >= 5) sel.shift();
        sel.push(id);
      }
      this.lv_options.lv_selected = sel;
    },
    prettyProp(prop) {
      return (
        {
          xfmr_scale: "Transformer scaling",
          oltc_setpoint: "MV transformer OLTC set point",
          oltc_bandwidth: "MV transformer OLTC bandwidth",
          rs_pen: "Residential share",
          lv_selected: "LV areas",
          penetration: "Penetration",
          // API query-parameter names (422 validation errors)
          lv_ev_profile: "Electric vehicles",
          lv_ev_pen: "EV penetration",
          lv_pv_profile: "Solar PV",
          lv_pv_pen: "Solar PV penetration",
          lv_hp_profile: "Heat pumps",
          lv_hp_pen: "Heat-pump penetration",
          mv_fcs_profile: "Fast charging station",
          mv_solar_pv_profile: "Large solar farm",
          lv_list: "LV areas"
        }[prop] || prop
      );
    },
    fmt(v, d) {
      return v == null || isNaN(v) ? "–" : Number(v).toFixed(d);
    },
    toggleGroup(name) {
      const i = this.openGroups.indexOf(name);
      if (i >= 0) this.openGroups.splice(i, 1);
      else this.openGroups.push(name);
    },

    // -------- request building & fetch (P1.6: robust errors) --------
    fetchAPIData() {
      this.invalid_csvs = [];
      this.error_messages = [];
      this.isLoading = true;

      // Base falls back to same-origin so an empty VUE_APP_API_URL (dev proxy)
      // works; production uses the absolute URL from .env.production.
      const url = new URL(
        "/simulate",
        process.env.VUE_APP_API_URL || window.location.origin
      );
      const url_params = { ...this.network_options };
      if (this.lv_options.lv_default === "custom")
        url_params.lv_list = this.lv_options.lv_selected;
      else url_params.lv_default = this.lv_options.lv_default;

      const formData = new FormData();
      const append = (name, key) =>
        this.appendProfileParams(
          url_params,
          formData,
          name,
          this.profile_options[key]
        );
      append("mv_solar_pv", "mv_solar_pv");
      append("mv_fcs", "mv_fcs");
      append("lv_smart_meter", "lv_smart_meter");
      append("lv_ev", "lv_electric_vehicle");
      append("lv_pv", "lv_photovoltaic");
      append("lv_hp", "lv_heat_pump");

      if (this.invalid_csvs.length > 0) {
        this.isLoading = false;
        return;
      }

      url_params.dry_run = false;
      url.search = new URLSearchParams(url_params).toString();
      const hasCsv = Object.values(this.profile_options).some(
        p => p.profile === "csv"
      );

      fetch(url, { method: "POST", body: hasCsv ? formData : null })
        .then(response => {
          if (response.ok || response.status === 422) return response.text();
          throw new Error(
            "Server returned " + response.status + " " + response.statusText
          );
        })
        .then(text => {
          const json = JSON.parse(text);
          if ("detail" in json) {
            // One human-readable message per validation error. d.loc is like
            // ["query", "lv_smart_meter_profile"] — only the field name (last
            // element) is meaningful to the user, and API field names are
            // translated to the labels used in the form.
            for (const d of json.detail) {
              const field = d.loc[d.loc.length - 1];
              if (String(field).startsWith("lv_smart_meter")) {
                this.error_messages.push(
                  "Household demand is required — switch it on and choose a demand profile."
                );
              } else {
                this.error_messages.push(this.prettyProp(field) + ": " + d.msg);
              }
            }
            this.error_messages = [...new Set(this.error_messages)];
            this.responseAvailable = false;
            return;
          }
          this.buildResults(json);
        })
        .catch(err => {
          // P1.6: a failed request no longer leaves the spinner spinning.
          this.error_messages.push(
            err.message || "Could not reach the simulation server."
          );
          this.responseAvailable = false;
        })
        .finally(() => {
          this.isLoading = false;
        });
    },
    appendProfileParams(url_params, form_data, name, params) {
      url_params[name + "_profile"] = params.profile;
      if (params.profile === "csv") {
        url_params[name + "_units"] = params.units;
        if (params.csv == null || params.csv.length !== 1)
          this.invalid_csvs.push(name);
        else form_data.set(name + "_csv", params.csv[0]);
      }
      // Penetration UI is 0–100 %; the API expects a 0–1 decimal.
      if (params.penetration !== undefined && params.profile !== "None") {
        url_params[name + "_pen"] = params.penetration / 100;
      }
    },

    // -------- results & KPI verdicts (P2) --------
    buildResults(json) {
      // Convergence warning (P-A): if any of the 48 half-hourly power flows
      // failed to converge, those windows' results are not physically
      // meaningful. Surface it rather than silently plotting invalid numbers.
      this.convergence =
        json.convergence && json.convergence.n_failed > 0
          ? json.convergence
          : null;
      this.verdicts = this.computeVerdicts(json);
      // Per-phase figures (one per selected network); default to the first.
      this.phasePngs = json.lv_phase_pngs || {};
      const phaseIds = Object.keys(this.phasePngs);
      this.phaseNet = phaseIds.length ? phaseIds[0] : null;
      const blob = s =>
        s == null
          ? undefined
          : URL.createObjectURL(new Blob([s], { type: "text/csv" }));

      // Native interactive charts (P5): built from the SAME CSVs as the
      // download links / verdicts. Each builder returns null if its CSV is
      // missing or oddly shaped, and the figure then falls back to the
      // matplotlib image — older API deployments keep working.
      const failedHours = json.convergence
        ? json.convergence.failed_hours || []
        : [];
      const lvPanels = lvQuantilePanels(
        parseFigureCsv(json.lv_comparison_data)
      );
      const mvQs = mvQuantiles(parseFigureCsv(json.mv_voltages_data));
      const vufSeries = lineSeries(
        parseFigureCsv(json.lv_unbalance_data),
        prettyVufName
      );
      const trnSeries = lineSeries(
        parseFigureCsv(json.trn_powers_data),
        prettyTransformerName
      );
      const fdrSeries = lineSeries(parseFigureCsv(json.primary_loadings_data));
      const ratingLimit = [{ value: 100, label: "rating" }];

      this.figureGroups = [
        {
          name: "Voltages",
          figures: [
            {
              name: "LV customer voltages",
              plot: json.lv_comparison,
              chart: lvPanels && {
                type: "quantile-grid",
                panels: lvPanels,
                limits: [
                  { value: 0.94, label: "0.94 pu" },
                  { value: 1.1, label: "1.10 pu" }
                ],
                failedHours
              },
              info:
                "Each panel is one modelled LV network. The centre line is the median customer's voltage; the shaded band spans all simulated customers (outer edge = min–max, inner = 25–75%). Hover for exact values.",
              info2:
                "Voltages are per-unit (×230 gives volts). Dashed red lines mark the statutory limits (0.94–1.10 pu).",
              data_filename: "lv_comparison.csv",
              data_url: blob(json.lv_comparison_data)
            },
            {
              name: "MV network voltages",
              plot: json.mv_voltages,
              chart: mvQs && {
                type: "quantile",
                quantiles: mvQs,
                limits: [
                  { value: 0.94, label: "0.94 pu" },
                  { value: 1.06, label: "1.06 pu" }
                ],
                failedHours
              },
              info:
                "Range, interquartile range and median voltage on the MV network. Hover for exact values.",
              info2: "MV limits are narrower: 0.94 to 1.06 pu.",
              data_filename: "mv_voltages.csv",
              data_url: blob(json.mv_voltages_data)
            },
            {
              name: "Phase unbalance",
              plot: json.lv_unbalance,
              chart: vufSeries && {
                type: "lines",
                series: vufSeries,
                limits: [
                  { value: 1.3, label: "1.3% ER P29" },
                  { value: 2, label: "2% EN 50160" }
                ],
                failedHours,
                unit: "%",
                decimals: 2
              },
              info:
                "The voltage unbalance factor (VUF) at each LV substation — how unevenly the three phases are loaded — against the 1.3% (ER P29) and 2% (EN 50160) planning levels.",
              info2:
                "Single-phase EV or heat-pump clusters on one phase drive the phases apart.",
              data_filename: "lv_unbalance.csv",
              data_url: blob(json.lv_unbalance_data)
            },
            {
              name: "Per-phase customer voltages",
              phaseSelector: true,
              info:
                "Solid line = average voltage of the customers on that phase; shaded band = the min–max spread across those customers. The three colours are the three phases; diverging phases indicate unbalance.",
              info2:
                "Choose which LV network to inspect. Dashed red lines mark the 0.94–1.10 pu limits."
            }
          ],
          badge: this.groupBadge([
            this.verdicts.lvVoltage,
            this.verdicts.mvVoltage
          ])
        },
        {
          name: "Transformer & feeder loadings",
          figures: [
            {
              name: "Transformer powers",
              plot: json.trn_powers,
              chart: trnSeries && {
                type: "lines",
                series: trnSeries,
                limits: ratingLimit,
                failedHours,
                unit: "%",
                decimals: 1
              },
              info:
                "Utilisation (%) of the primary (HV→MV) and secondary (MV→LV) substations.",
              info2: "100% = the substation's rating (dashed line).",
              data_filename: "transformer_powers.csv",
              data_url: blob(json.trn_powers_data)
            },
            {
              name: "Primary feeders' loadings",
              plot: json.pmry_loadings,
              chart: fdrSeries && {
                type: "lines",
                series: fdrSeries,
                limits: ratingLimit,
                failedHours,
                unit: "%",
                decimals: 1
              },
              info:
                "The primary substation supplies the town through several 11 kV feeders — the main cables leaving the substation busbar, each serving a different part of the network. One line per feeder, measured at the point it leaves the substation.",
              info2:
                "Values are apparent power as % of each feeder's rating; above 100% (dashed line) the cable is overloaded.",
              data_filename: "primary_loadings.csv",
              data_url: blob(json.primary_loadings_data)
            }
          ],
          badge: this.groupBadge([
            this.verdicts.transformer,
            this.verdicts.feeder
          ])
        },
        // "Network maps" group removed — the interactive map in step 1
        // already shows the network topology.
        {
          name: "Profiles used",
          figures: [
            {
              name: "Average of LV profiles",
              plot: json.profile_options,
              info:
                "Mean power (kW) of the LV profiles. Negative values imply generation.",
              info2:
                "Individual profiles, not this average, are used in the simulation."
            },
            {
              name: "MV distributed generation profile",
              plot: json.profile_options_dgs,
              info: "Mean power (kW) of the MV solar (DG) profile."
            },
            {
              name: "MV fast charging profile",
              plot: json.profile_options_fcs,
              info: "Mean power (kW) of the MV fast-charging profile."
            }
          ]
        }
      ];
      this.openGroups = ["Voltages"];
      this.responseAvailable = true;
      this.ranLabel = this.presets[this.activePreset]
        ? this.presets[this.activePreset].label
        : "custom scenario";
      this.previousRun = {
        label: this.ranLabel,
        verdict: this.verdicts.overall.label,
        pillClass: this.verdicts.overall.pillClass
      };
      this.$nextTick(() => {
        if (this.$refs.results)
          this.$refs.results.scrollIntoView({
            behavior: "smooth",
            block: "start"
          });
      });
    },

    // ===================================================================
    // PASS/FAIL VERDICT LOGIC  ✔ FABLE-REVIEWED 2026-07-08
    // Statutory limits — LV: 0.94–1.10 pu, MV: 0.94–1.06 pu (GB ESQCR:
    // 230 V +10%/−6% and 11 kV ±6%), matching the simulation's dashed limit
    // lines. Loading (transformers and MV feeders) is a % of rating; 100% =
    // rated. CSV columns per azure_mockup.py + fillplot():
    //   lv_comparison_data   : 48 rows × (5 quantiles per LV network), pu.
    //     Quantiles are [0,25,50,75,100]%, so the 0%/100% columns are the
    //     exact per-timestep min/max over customers.
    //   mv_voltages_data     : 48 rows × 5 quantiles, pu.
    //   trn_powers_data      : 48 rows × (primary util%, then secondary util% per LV).
    //   primary_loadings_data: 48 rows × (% of rating per MV feeder).
    // Time axis: row i = the half-hour starting at i·0.5 h (tt = arange(0,24,0.5)).
    // The voltage verdict identifies the *driving* extreme (min or max, whichever
    // violates / sits nearest a limit) so overvoltage (solar) scenarios report
    // the max — its value, time and network — not the day's minimum.
    // ===================================================================
    computeVerdicts(json) {
      const LV = [0.94, 1.1];
      const MV = [0.94, 1.06];
      const lv = this.parseCsv(json.lv_comparison_data);
      const mvv = this.parseCsv(json.mv_voltages_data);
      const trn = this.parseCsv(json.trn_powers_data);
      const fdr = this.parseCsv(json.primary_loadings_data);

      // Loading verdict shared by transformers and MV feeders (% of rating).
      const loadVerdict = peak => {
        if (peak == null)
          return { label: "No data", pillClass: "warn", ok: false };
        if (peak > 100)
          return { label: "Over rating", pillClass: "crit", ok: false };
        if (peak >= 80)
          return { label: "Approaching rating", pillClass: "warn", ok: false };
        return { label: "Within rating", pillClass: "ok", ok: true };
      };

      const lvVoltage = this.voltageVerdict(lv, LV);
      const mvVoltage = this.voltageVerdict(mvv, MV);
      const trnPeak = this.extreme(trn, "max");
      const fdrPeak = this.extreme(fdr, "max");
      const transformer = { peak: trnPeak, ...loadVerdict(trnPeak) };
      const feeder = { peak: fdrPeak, ...loadVerdict(fdrPeak) };

      // overall = worst of the four checks
      const all = [lvVoltage, mvVoltage, transformer, feeder];
      let overall = { label: "All clear", pillClass: "ok" };
      if (all.some(v => v.pillClass === "crit"))
        overall = { label: "Limit breach", pillClass: "crit" };
      else if (all.some(v => v.pillClass === "warn"))
        overall = { label: "Watch", pillClass: "warn" };

      return {
        lvVoltage,
        mvVoltage,
        transformer,
        feeder,
        overall,
        interpretation: this.interpret(
          lvVoltage,
          mvVoltage,
          transformer,
          feeder
        )
      };
    },
    // Voltage verdict that identifies the driving extreme (the one that
    // violates a limit, or — if none does — the one nearest a limit), so the
    // headline value, time and network reflect the actual worst case.
    voltageVerdict(matrix, [lo, hi]) {
      const minLoc = this.argExtreme(matrix, "min");
      const maxLoc = this.argExtreme(matrix, "max");
      const min = minLoc.value;
      const max = maxLoc.value;
      if (min == null)
        return {
          min: null,
          max: null,
          value: null,
          driver: "min",
          ok: false,
          label: "No data",
          pillClass: "warn",
          when: null,
          net: null
        };
      const nRows = matrix.rows.length;
      const pack = (loc, driver, label, pillClass, ok) => ({
        min,
        max,
        value: loc.value,
        driver,
        label,
        pillClass,
        ok,
        when: this.timeOfRow(loc.row, nRows),
        net: this.networkOfColumn(matrix.header, loc.col)
      });
      const underBy = lo - min; // > 0 → undervoltage breach
      const overBy = max - hi; // > 0 → overvoltage breach
      if (underBy > 0 || overBy > 0) {
        // Both may breach; report the larger exceedance.
        return underBy >= overBy
          ? pack(minLoc, "min", "Below limit", "crit", false)
          : pack(maxLoc, "max", "Above limit", "crit", false);
      }
      // No breach — warn if within 0.005 pu of either limit.
      const marginMin = min - lo;
      const marginMax = hi - max;
      if (marginMin < 0.005 || marginMax < 0.005) {
        return marginMin <= marginMax
          ? pack(minLoc, "min", "Near lower limit", "warn", false)
          : pack(maxLoc, "max", "Near upper limit", "warn", false);
      }
      return pack(minLoc, "min", "Within limits", "ok", true);
    },
    interpret(lvV, mvV, trn, fdr) {
      const parts = [];
      if (!lvV.ok && lvV.value != null) {
        const where = `around ${lvV.when}${
          lvV.net ? " on LV network " + lvV.net : ""
        }`;
        if (lvV.driver === "min")
          parts.push(
            lvV.pillClass === "crit"
              ? `The lowest simulated customer voltage reaches ${lvV.value.toFixed(
                  3
                )} pu ${where}, below the 0.94 pu limit.`
              : `The lowest simulated customer voltage reaches ${lvV.value.toFixed(
                  3
                )} pu ${where}, close to the 0.94 pu lower limit.`
          );
        else
          parts.push(
            lvV.pillClass === "crit"
              ? `The highest simulated customer voltage reaches ${lvV.value.toFixed(
                  3
                )} pu ${where}, above the 1.10 pu limit.`
              : `The highest simulated customer voltage reaches ${lvV.value.toFixed(
                  3
                )} pu ${where}, close to the 1.10 pu upper limit.`
          );
      }
      if (!trn.ok && trn.peak != null) {
        parts.push(
          trn.peak > 100
            ? `Peak transformer loading reaches ${trn.peak.toFixed(
                0
              )}%, over its rating.`
            : `Peak transformer loading reaches ${trn.peak.toFixed(
                0
              )}%, approaching its rating.`
        );
      }
      if (!fdr.ok && fdr.peak != null) {
        parts.push(
          fdr.peak > 100
            ? `An MV feeder reaches ${fdr.peak.toFixed(
                0
              )}% of its rating, over the limit.`
            : `An MV feeder reaches ${fdr.peak.toFixed(
                0
              )}% of its rating, approaching the limit.`
        );
      }
      // MV voltage breach is independent — always surface it if it breaches.
      if (mvV.pillClass === "crit" && mvV.min != null) {
        parts.push(
          `MV voltage reaches ${mvV.min.toFixed(3)}–${mvV.max.toFixed(
            3
          )} pu, outside the 0.94–1.06 pu MV band.`
        );
      }
      if (parts.length === 0)
        return "All monitored limits are satisfied for this scenario — the network copes.";
      return parts.join(" ");
    },
    groupBadge(verdicts) {
      if (verdicts.some(v => v.pillClass === "crit"))
        return { text: "breach", cls: "crit" };
      if (verdicts.some(v => v.pillClass === "warn"))
        return { text: "watch", cls: "warn" };
      return { text: "ok", cls: "ok" };
    },

    // -------- CSV parsing helpers --------
    parseCsv(str) {
      if (!str || typeof str !== "string") return { header: [], rows: [] };
      const lines = str
        .trim()
        .split("\n")
        .filter(l => l.length);
      if (!lines.length) return { header: [], rows: [] };
      const header = lines[0].split(",");
      // Keep every data row (non-numeric cells become NaN and are skipped in
      // the extremes) so row index stays aligned to the half-hourly clock.
      const rows = lines.slice(1).map(l => l.split(",").map(Number));
      return { header, rows };
    },
    extreme(parsed, kind) {
      let best = null;
      for (const row of parsed.rows)
        for (const x of row) {
          if (!isFinite(x)) continue;
          if (best == null) best = x;
          else best = kind === "min" ? Math.min(best, x) : Math.max(best, x);
        }
      return best;
    },
    argExtreme(parsed, kind) {
      let best = null,
        loc = { value: null, row: -1, col: -1 };
      parsed.rows.forEach((row, ri) =>
        row.forEach((x, ci) => {
          if (!isFinite(x)) return;
          if (best == null || (kind === "min" ? x < best : x > best)) {
            best = x;
            loc = { value: x, row: ri, col: ci };
          }
        })
      );
      return loc;
    },
    timeOfRow(row, nRows) {
      if (row < 0 || !nRows) return "the day";
      const hours = (row / nRows) * 24;
      const h = Math.floor(hours),
        m = Math.round((hours - h) * 60);
      return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
    },
    networkOfColumn(header, col) {
      const h = header[col] || "";
      const m = h.match(/(\d{3,})\s*$/);
      return m ? m[1] : null;
    },

    // -------- API calls --------
    getProfileOptions(profile_name) {
      return fetch(
        process.env.VUE_APP_API_URL + "/get-options?option_type=" + profile_name
      )
        .then(r =>
          r.ok ? r.text() : Promise.reject(new Error("get-options " + r.status))
        )
        .then(t => JSON.parse(t))
        .catch(() => []);
    },
    updateTopology() {
      // Pre-built network map for the interactive explorer/selector.
      this.topology = null;
      return fetch(
        process.env.VUE_APP_API_URL +
          "/network-topology?n_id=" +
          this.network_options.n_id
      )
        .then(r =>
          r.ok
            ? r.text()
            : Promise.reject(new Error("network-topology " + r.status))
        )
        .then(t => {
          this.topology = JSON.parse(t);
        })
        .catch(() => {
          this.topology = null;
        });
    },
    updateLVNetworksList() {
      return fetch(
        process.env.VUE_APP_API_URL +
          "/lv-network?n_id=" +
          this.network_options.n_id
      )
        .then(r =>
          r.ok ? r.text() : Promise.reject(new Error("lv-network " + r.status))
        )
        .then(t => {
          this.lv_options.lv_list = JSON.parse(t).networks;
          this.updatePreselectedLVNetworksList();
        })
        .catch(() => {});
    },
    updatePreselectedLVNetworksList() {
      if (this.lv_options.lv_default === "custom") return;
      return fetch(
        process.env.VUE_APP_API_URL +
          "/lv-network-defaults?n_id=" +
          this.network_options.n_id +
          "&lv_default=" +
          this.lv_options.lv_default
      )
        .then(r =>
          r.ok
            ? r.text()
            : Promise.reject(new Error("lv-network-defaults " + r.status))
        )
        .then(t => {
          this.lv_options.lv_selected = JSON.parse(t).networks;
        })
        .catch(() => {});
    }
  }
};
</script>

<style scoped>
.evt-wrap {
  max-width: 1080px;
  margin: 0 auto;
}
.evt-header {
  margin-bottom: 20px;
}
.evt-header h1 {
  font-size: 1.6rem;
  font-weight: 600;
  line-height: 1.2;
  text-wrap: balance;
  margin: 4px 0 8px;
}
.evt-lede {
  color: var(--muted);
  max-width: 60ch;
}

.evt-layout {
  display: grid;
  grid-template-columns: 1fr 290px;
  gap: 20px;
  align-items: start;
}
.evt-main {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}
.evt-side {
  position: sticky;
  top: 16px;
}
@media (max-width: 820px) {
  .evt-layout {
    grid-template-columns: 1fr;
  }
  .evt-side {
    position: static;
  }
}

.evt-step {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0 0 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.evt-step-n {
  display: inline-flex;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--ink);
  color: var(--paper);
  font-size: 0.75rem;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex: none;
}
.evt-field {
  margin-bottom: 16px;
}
.evt-group-lbl {
  margin-top: 14px;
}
.evt-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.evt-presets-card {
  padding: 14px 20px;
}

.evt-thumb-explorer {
  margin-top: 4px;
}
.evt-map-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.evt-map-lbl {
  font-weight: 600;
  color: var(--ink);
}
.evt-map-cta {
  display: block;
  font-size: 0.75rem;
  color: var(--accent);
  font-weight: 600;
}
.evt-map-hint {
  font-size: 0.76rem;
  color: var(--muted);
  margin: 8px 0 0;
}

.evt-lvchips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.evt-lvchips-scroll {
  max-height: 132px;
  overflow-y: auto;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  align-content: flex-start;
}
.evt-lvcount {
  font-size: 0.78rem;
  color: var(--muted);
  margin-top: 6px;
}
.evt-inline-err {
  font-size: 0.78rem;
}

.evt-advanced {
  border-top: 1px dashed var(--line);
  margin-top: 10px;
  padding-top: 12px;
}
/* A real button, not a whisper of text — users kept missing this. */
.evt-adv-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  background: var(--wire-soft);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--ink);
  cursor: pointer;
}
/* CHANGE(round2-3): the title is a fixed-width two-line block (see the <br>
   in the template) instead of one long nowrap string — that's what frees up
   the row for .evt-adv-summary to fit on one line. 140px is wide enough that
   neither "MV advanced" nor "network parameters" wraps a second time (the
   longer of the two measures ~133px at the button's font). */
.evt-adv-toggle .evt-adv-label {
  flex: 0 0 auto;
  width: 140px;
  line-height: 1.15;
}
.evt-adv-toggle .bi {
  color: var(--wire);
}
.evt-adv-chevron {
  color: var(--wire);
  font-size: 0.78rem;
  font-weight: 600;
  flex: 0 0 auto;
}
/* CHANGE(round2-3): one line, no horizontal scrollbar. The two-line title
   (above) frees enough width that this fits at normal widths; at very narrow
   widths (~360 px) it truncates with an ellipsis instead of scrolling. */
.evt-adv-summary {
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--muted);
  margin-left: auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1 1 auto;
  text-align: right;
}
.evt-adv-body {
  margin-top: 10px;
}
.evt-slider-row {
  display: grid;
  grid-template-columns: 1fr 150px 70px;
  gap: 12px;
  align-items: center;
  padding: 6px 0;
  font-size: 0.85rem;
}
.evt-slider-row input[type="range"] {
  width: 100%;
  accent-color: var(--accent);
}
.evt-slider-row .evt-mono {
  font-size: 0.82rem;
  text-align: right;
}
@media (max-width: 560px) {
  .evt-slider-row {
    grid-template-columns: 1fr 1fr;
  }
}

/* KPI cards */
.evt-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 640px) {
  .evt-kpis {
    grid-template-columns: 1fr;
  }
}
.evt-kpi {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
}
.evt-kpi-k {
  font-size: 0.72rem;
  color: var(--muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.evt-kpi-v {
  font-size: 1.4rem;
  font-weight: 600;
  margin: 3px 0;
}
.evt-interpret {
  margin-top: 12px;
  font-size: 0.9rem;
  color: var(--ink);
}

.evt-groups {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.evt-group {
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}
.evt-group-head {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--card);
  border: none;
  padding: 11px 14px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--ink);
  cursor: pointer;
}
.evt-group-body {
  padding: 4px 14px 14px;
}
.evt-figure {
  padding-top: 12px;
}
.evt-figure-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  margin-bottom: 6px;
}
.evt-figure-img {
  max-width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
}
/* Native charts (P5): the LV comparison renders one panel per modelled
   network, two-up where the card is wide enough. */
.evt-chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2px 18px;
}
.evt-chart-title {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--ink);
  margin-top: 6px;
}
.evt-phase-select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--muted);
  margin-bottom: 8px;
}
.evt-phase-select select {
  font-size: 0.8rem;
  padding: 2px 6px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--card);
  color: var(--ink);
}
.evt-csv-link {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--wire);
  text-decoration: none;
}

/* Sidebar summary */
.evt-summary {
  padding: 16px 18px;
}
.evt-sumline {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.82rem;
  padding: 5px 0;
  border-bottom: 1px solid var(--line);
}
.evt-sumline b {
  font-weight: 600;
}
.evt-run {
  width: 100%;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 0.95rem;
  font-weight: 700;
  margin-top: 14px;
  cursor: pointer;
}
.evt-run:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.evt-run-sub {
  font-size: 0.72rem;
  color: var(--muted);
  text-align: center;
  margin-top: 6px;
}
.evt-errors {
  margin-top: 12px;
  border: 1px solid var(--crit);
  background: var(--crit-soft);
  color: var(--crit);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.8rem;
}
.evt-errors ul {
  margin: 6px 0 0;
  padding-left: 18px;
}
.evt-prev {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.evt-warn {
  margin: 4px 0 16px;
  border: 1px solid var(--warn);
  background: var(--warn-soft);
  color: var(--warn);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.82rem;
  line-height: 1.4;
}

/* Partner logos are full-colour brand marks (dark wordmarks, transparent
   PNGs) that cannot be recoloured with the theme, so they sit on a white
   plinth in BOTH themes — otherwise they vanish against the dark paper. */
.evt-logos {
  display: flex;
  flex-wrap: wrap;
  gap: 24px 40px;
  justify-content: center;
  align-items: center;
  margin: 32px 0 12px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 28px;
}
.evt-logos .logo {
  max-height: 64px;
}
</style>
