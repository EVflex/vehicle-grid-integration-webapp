<template>
  <div class="container">
    <div class="row">
      <div class="col-sm-12">
        <h4>Build and simulate an electricity distribution network with EVs and other green technologies</h4>
        <p>
          <walkthrough-modal></walkthrough-modal>Step-by-Step guide
        </p>
      </div>
    </div>

    <form id="config" ref="config" @submit.prevent>
      <div class="row box-main" style="border-color: #039BE5">
        <div class="col-lg-12 box-title" style="background-color: #B3E5FC">
          <h3>Electricity distribution network parameters</h3>
          
        </div>

        <div class="col-lg-6">
          <h4>Medium voltage (MV)</h4>

          <div class="form-group row">
            <!-- Experiment parameter: n_id, network ID -->
            <label for="n_id" class="col-sm-6 col-form-label">
              Network ID
            </label>
            <div class="col-sm-6">
              <select v-model="network_options.n_id" class="form-control" @change="updateLVNetworksList()">
                <option value="1060">11kV urban network</option>
                <option value="1061">11kV urban - rural network</option>
              </select>
            </div>
          </div>

          <div class="form-group row">
            <!-- Experiment parameter: xfmr_scale, MV transformer scaling -->
            <label for="xfmr_scale" class="col-md-6 col-form-label">
              MV transformer scaling
              <input-details inputName="MV transformer scaling" 
                             inputInfo="Number by which the nominal power rating of the primary (HV/MV) power transformer are multiplied by, to allow an increase in demand before the substation is overloaded. (Affects the primary substation utilization on the 'Transformer Powers' figure that is returned.)"
                             inputValues="Value should be between 0.5 and 4."/>
            </label>
            <div class="col-md-6">
              <input
                v-model.number="network_options.xfmr_scale"
                type="float"
                class="form-control"
                id="xfmr_scale"
              />
              <div v-for="error of v$.network_options.xfmr_scale.$errors" :key="error.$uid" class="text-danger">{{ error.$message }}</div>
            </div>
          </div>

          <div class="form-group row">
            <!-- Experiment parameter: oltc_setpoint -->
            <label for="oltc_setpoint" class="col-md-6 col-form-label">
              MV transformer on-load tap changer (OLTC) set point
              <input-details inputName="MV transformer on-load tap changer (OLTC) set point"
                             inputInfo="Nominal voltage, in 'per-unit', at which the voltage is held on the low-voltage side of the primary substation. The on-load tap changer will aim to keep the voltage close to this value."
                             inputValues="Value should be between 0.95 and 1.1."/>
            </label>
            <div class="col-md-6">
              <input
                v-model.number="network_options.oltc_setpoint"
                type="float"
                class="form-control"
                id="oltc_setpoint"
              />
              <div v-for="error of v$.network_options.oltc_setpoint.$errors" :key="error.$uid" class="text-danger">{{ error.$message }}</div>
            </div>
          </div>

          <div class="form-group row">
            <!-- Experiment parameter: oltc_bandwidth -->
            <label for="oltc_bandwidth" class="col-md-6 col-form-label">
              MV transformer on-load tap changer (OLTC) bandwidth
              <input-details inputName="MV transformer on-load tap changer (OLTC) bandwidth"
                             inputInfo="In 'per-unit', the on-load tap changer at the primary substation will only change when the voltage passes outside of the setpoint plus-or-minus the bandwidth. A wider bandwidth means that the voltage at the primary substation will vary more before the tap changes."
                             inputValues="Value should be between 0.01 and 0.05."/>
            </label>
            <div class="col-md-6">
              <input
                v-model.number="network_options.oltc_bandwidth"
                type="float"
                class="form-control"
                id="oltc_bandwidth"
              />
              <div v-for="error of v$.network_options.oltc_bandwidth.$errors" :key="error.$uid" class="text-danger">{{ error.$message }}</div>
            </div>
          </div>

          <div class="form-group row">
            <!-- Experiment parameter: rs_pen -->
            <label for="rs_pen" class="col-md-6 col-form-label">
              Proportion residential loads
              <input-details inputName="Proportion residential loads"
                             inputInfo="For example 0.8 indicates that 80% of the loads on the network are residential loads and 20% are industrial and commercial loads."
                             inputValues="Value should be between 0 and 1."/>
            </label>
            <div class="col-md-6">
              <input
                v-model.number="network_options.rs_pen"
                type="float"
                class="form-control"
                id="rs_pen"
              />
              <div v-for="error of v$.network_options.rs_pen.$errors" :key="error.$uid" class="text-danger">{{ error.$message }}</div>
            </div>
          </div>
        </div>

        <div class="col-lg-6">
          <h4>Low voltage (LV)</h4>

          <div class="form-group row">
            <!-- Experiment parameter: lv_default (if custom, open lv_list option below) -->
            <label for="lv_options.lv_default" class="col-md-6 col-form-label">
              Selection of LV networks to model in detail
            </label>
            <div class="col-md-6">
              <select v-model="lv_options.lv_default" class="form-control" @change="updatePreselectedLVNetworksList()">
                <option>near-sub</option>
                <option>near-edge</option>
                <option>mixed</option>
                <option>custom</option>
              </select>
            </div>
          </div>

          <div v-if="lv_options.lv_default=='custom'" class="form-group row">
            <label for="lv_list" class="col-md-6 col-form-label">
              LV network IDs
              <input-details inputName="Selected LV network IDs"
                             inputValues="Select between two and five network IDs from the provided list."/>
            </label>
            <div class="col-md-6">
              <select multiple class="form-control" id="lv_list" v-model="lv_options.lv_selected" :disabled="lv_options.lv_default!=='custom'">
                <option v-for="lv_id in lv_options.lv_list" :key="lv_id">{{ lv_id }}</option>
              </select>
              <div v-for="error of v$.lv_options.lv_selected.$errors" :key="error.$uid" class="text-danger">{{ error.$message }}</div>
            </div>
          </div>

          <div class="form group row">
            <label for="lv_selected_output" class="col-md-6 col-form-label">
              Currently selected LV network IDs
            </label>
            <div class="col-md-6 col-form-label">
              {{ lv_options.lv_selected.join(", ") }}
            </div>
          </div>
        </div>
      </div>

      <div class="row box-main" style="border-color: #00ACC1">
        <div class="col-lg-12 box-title" style="background-color: #B2EBF2">
          <h3>Demand and generation profiles
          <input-details inputName="Choose from available profiles or upload your own data."
                         inputInfo= "If uploading your own data, please use a csv file with a header and 48 rows corresponding to 1 day at 30-minute resolution data."
                         inputValues= "There is no limit on the number of columns that can be uploaded (i.e. several days of data)."
                         inputExampleLink="https://github.com/alan-turing-institute/vehicle-grid-integration-webapp-private/blob/main/vgi_api/vgi_api/data/example_profile.csv"/> </h3>
          
        </div>
                            
        <div class="col-lg-6">
          <h4>MV connected
          <input-details inputName="MV connected generation and demand"
                         inputValues= "The walkthrough guide shows the network connection of these sites."
                         inputInfo= "Leave as None or connect DG sites such as commercial solar installations and/or FC sites such a Tesla or Fastned FC stations."/>
          </h4>

          <select-profile v-model:profileOptions="profile_options.mv_solar_pv" title="Large distributed generation (DG) e.g. Commercial solar PV"></select-profile>
          <select-profile v-model:profileOptions="profile_options.mv_fcs" title="Fast charging stations"></select-profile>
        </div>

        <div class="col-lg-6">
          <h4>LV connected
          <input-details inputName="LV connected generation and demand"
                         inputValues= "Change the penetration level from 0% to 100% penetration. The higher the penetration of green technologies, the higher the impact that will be seen on the network."  
                         inputInfo= "Leave empty for no green technologies, use available profiles, or upload your own data."/>
          </h4>
            <select-profile v-model:profileOptions="profile_options.lv_smart_meter" v-model:penValidation="v$.profile_options.lv_smart_meter.penetration.$errors" title="Smart meters"></select-profile>
            <select-profile v-model:profileOptions="profile_options.lv_electric_vehicle" v-model:penValidation="v$.profile_options.lv_electric_vehicle.penetration.$errors" title="Electric vehicles"></select-profile>
            <select-profile v-model:profileOptions="profile_options.lv_photovoltaic" v-model:penValidation="v$.profile_options.lv_photovoltaic.penetration.$errors" title="Solar PV"></select-profile>
            <select-profile v-model:profileOptions="profile_options.lv_heat_pump" v-model:penValidation="v$.profile_options.lv_heat_pump.penetration.$errors" title="Heat pumps"></select-profile>
        </div>
      </div>

      <div class="row box-main" style="border-color: #00897B">
        <div class="col-lg-12 box-title" style="background-color: #B2DFDB">
          <h3>Simulation</h3>
        </div>

        <div class="col-lg-12">
          <div class="form-group row">
            <label for="button_submit" class="col-md-3 col-form-label">
              Run simulation
            </label>
            <div class="col-md-3">
            <button :disabled="v$.$errors.length" type="submit" name="button_submit" class="btn btn-primary btn-block" style="background-color: #00897B; border-color: #00897B" @click="fetchAPIData">
              Submit
              <template v-if="isLoading">
                <div class="spinner-border spinner-border-sm" role="status"></div>
              </template>
            </button>
            </div>
          </div>
          <div class="form-group row">
            <div class="col-md-6">
              <div v-if="v$.$errors.length || invalid_csvs.length || error_messages.length" class="alert alert-danger" role="alert">
                  <i class="bi bi-exclamation-octagon-fill"></i>
                  Invalid inputs
                <hr>
                <div v-for="error of v$.$errors" :key="error.$uid">
                  {{ error.$property }}: {{ error.$message }}
                </div>
                <div v-for="csv_name of invalid_csvs" :key="csv_name.$uid">
                  One csv file required for input {{ csv_name }}
                </div>
                <div v-for="message of error_messages" :key="message.$uid">
                  {{ message }}
                </div>
              </div>
            </div>
          </div>
          <template v-if="isLoading">
            <div class="form-group row col-md-6">
              Simulation in progress...<br>
              Usually complete in less than one minute
            </div>
          </template>
        </div>

        <div class="col-lg-12">

          <template v-if="responseAvailable">
            <h4>Results</h4>
            <div class="accordion" id="accordionResults" style="margin-bottom: 1rem">
              <div v-for="(p, ind) in plots" :key="p.ind">
                <div class="card card-results">
                  <div class="card-header">
                    <div data-toggle="collapse" :data-target="'#plotCollapse' + ind" style="float: left">
                      <i class="bi bi-chevron-down"></i>
                      {{ p.name }}&nbsp;&nbsp;
                    </div>
                    <input-details v-if="p.info" :inputName="p.name" :inputInfo="p.info" :inputInfo2="p.info2"  :inputValues="p.values"/>
                    <button v-if="p.data_url !== undefined" class="btn btn-sm btn-outline-dark" type="button" style="float: right">
                        <a :href=p.data_url :download=p.data_filename>
                          <i class="bi bi-download"></i>
                          csv
                        </a>
                      </button>
                  </div>
                  <div
                    :id="'plotCollapse' + ind"
                    class="collapse"
                    v-bind:class="{ show: !ind }"
                    data-parent="#accordionResults"
                  >
                    <div class="card-body">
                      <img v-bind:src="'data:image/jpeg;base64,' + p.plot" style="max-width: 100%; min-width: 75%"/>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

      </div>
      

    </form>

    <!-- <github-link text="Website and simulation code" link="https://github.com/alan-turing-institute/vehicle-grid-integration-webapp-private"/>
    <br>
    <github-link text="Open profiles data" link="https://github.com/alan-turing-institute/e4Future-opendata"/>
    <br>
    <github-link text="Network models" link="https://github.com/alan-turing-institute/vehicle-grid-integration-opendss-networks"/>
    <br>
    <github-link text="API documentation" :link="docs_url" icon="bi-lightning-fill"/> -->

    <div class="row">
      <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/supergen.png">
      <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/turing.png">
      <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/newcastle.png">
      <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/lrf.svg">
    </div>

  </div>
</template>

<script>
import SelectProfile from "../components/SelectProfile.vue"
import InputDetails from "../components/InputDetails.vue"
import WalkthroughModal from "../components/WalkthroughModal.vue"
import useVuelidate from '@vuelidate/core'
import { required, requiredIf, between, minLength, maxLength} from '@vuelidate/validators'

export default {
  el: "#main",

  components: {
    SelectProfile,
    InputDetails,
    WalkthroughModal,
  },

  setup () {
    return {
      v$: useVuelidate({ $autoDirty: true })
    }
  },

  data() {
    return {
      network_options: {
        // Electricity distribution network parameters
        // MV
        n_id: 1060,
        xfmr_scale: 1.0,
        oltc_setpoint: 1.04,
        oltc_bandwidth: 0.013,
        rs_pen: 0.8,
      },
      lv_options:{
        lv_default: "near-sub",
        lv_list: [],
        lv_selected: []
      },
      profile_options: {
        mv_solar_pv: {
          list: [],
          profile: null,
          units: "kW",
          csv: null,
        },
        mv_fcs: {
          list: [],
          profile: null,
          units: "kW",
          csv: null,
        },
        lv_smart_meter: {
          list: [],
          profile: null,
          units: "kW",
          csv: null,
        },
        lv_electric_vehicle: {
          list: [],
          profile: null,
          units: "kW",
          csv: null,
          penetration: 1
        },
        lv_photovoltaic: {
          list: [],
          profile: null,
          units: "kW",
          csv: null,
          penetration: 1
        },
        lv_heat_pump: {
          list: [],
          profile: null,
          units: "kW",
          csv: null,
          penetration: 1
        }
      },
      rawJson: "empty",
      invalid_csvs: [],
      error_messages: [],
      isShowJson: false,
      isLoading: false,
      responseAvailable: false,
      docs_url: new URL("/docs", process.env.VUE_APP_API_URL).href
    };
  },

  validations() {
    return {
       network_options: {
        xfmr_scale: { required, between: between(0.5, 4) },
        oltc_setpoint: { required, between: between(0.95, 1.1) },
        oltc_bandwidth: { required, between: between(0.01, 0.05) },
        rs_pen: { required, between: between(0, 1) },
      },
      lv_options: {
        lv_selected: { required: requiredIf( function() { return this.lv_options.lv_default == "custom" }),
                       maxLength: maxLength(5),
                       minLength: minLength(2),
         }
      },
      profile_options: {
        lv_smart_meter: {
          penetration: { required, between: between(0, 1) }
        },
        lv_electric_vehicle: {
          penetration: { required: requiredIf( function() { return this.profile_options.lv_electric_vehicle.profile !== "None" } ),
                         between: between(0, 1) }
        },
        lv_photovoltaic: {
          penetration: { required: requiredIf( function() { return this.profile_options.lv_photovoltaic.profile !== "None" } ),
                         between: between(0, 1) }
        },
        lv_heat_pump: {
          penetration: { required: requiredIf( function() { return this.profile_options.lv_heat_pump.profile !== "None" } ),
                         between: between(0, 1) }
        }
      }
    }
  },

  mounted() {
    // Populate the lists used in the dropdown menus with their options
    this.getProfileOptions("mv-solar-pv").then(p_list => {
      this.profile_options.mv_solar_pv.list = p_list;
      this.profile_options.mv_solar_pv.profile = p_list[0];
    });
    this.getProfileOptions("mv-fcs").then(p_list => {
      this.profile_options.mv_fcs.list = p_list;
      this.profile_options.mv_fcs.profile = p_list[0];
    });
    this.getProfileOptions("lv-smartmeter").then(p_list => {
      this.profile_options.lv_smart_meter.list = p_list;
      this.profile_options.lv_smart_meter.profile = p_list[0];
    });
    this.getProfileOptions("lv-ev").then(p_list => {
      this.profile_options.lv_electric_vehicle.list = p_list;
      this.profile_options.lv_electric_vehicle.profile = p_list[0];
    });
    this.getProfileOptions("lv-pv").then(p_list => {
      this.profile_options.lv_photovoltaic.list = p_list;
      this.profile_options.lv_photovoltaic.profile = p_list[0];
    });
    this.getProfileOptions("lv-hp").then(p_list => {
      this.profile_options.lv_heat_pump.list = p_list;
      this.profile_options.lv_heat_pump.profile = p_list[0];
    });
    this.updateLVNetworksList()   // also updates preselected networks as nested function
  },

  methods: {

    fetchAPIData() {
      // Ask user to wait while API request is formed and made
      this.plots = [];
      this.invalid_csvs = []
      this.error_messages = []
      this.rawJson = "wait...";
      this.isLoading = true;
      this.responseAvailable = false;

      // Initialise URL with parameters from network options (top left panel)
      var url = new URL("/simulate", process.env.VUE_APP_API_URL);
      var url_params = JSON.parse(JSON.stringify(this.network_options));
      
      // Add named set of LV networks or custom list to URL (top right panel)
      var lv_params = JSON.parse(JSON.stringify(this.lv_options));
      if (lv_params.lv_default == "custom") {
        url_params.lv_list = lv_params.lv_selected;
      } else {
        url_params.lv_default = lv_params.lv_default;
      }

      // Add MV and LV profiles to URL (middle panel, left/right for MV/LV)
      let formData = new FormData();
      url_params, formData = this.appendProfileParams(url_params, formData, "mv_solar_pv", this.profile_options.mv_solar_pv)
      url_params, formData = this.appendProfileParams(url_params, formData, "mv_fcs", this.profile_options.mv_fcs)
      url_params, formData = this.appendProfileParams(url_params, formData, "lv_smart_meter", this.profile_options.lv_smart_meter)
      url_params, formData = this.appendProfileParams(url_params, formData, "lv_ev", this.profile_options.lv_electric_vehicle)
      url_params, formData = this.appendProfileParams(url_params, formData, "lv_pv", this.profile_options.lv_photovoltaic)
      url_params, formData = this.appendProfileParams(url_params, formData, "lv_hp", this.profile_options.lv_heat_pump)
      if ( this.invalid_csvs.length > 0 ) {
        this.isLoading = false;
        this.responseAvailable = false;
        return
      }

      url_params.dry_run = false;

      url.search = new URLSearchParams(url_params).toString();

      console.log("URL params", url_params)
      for (let kv of formData.entries()) {
        console.log("formData contains", kv[0], kv[1])
      }
      console.log(url)

      let check_csv_to_upload = Object.values(this.profile_options).reduce((any_csv, {profile}) => any_csv || profile=="csv", false)

      fetch(url, {
        method: "POST",
        body: check_csv_to_upload ? formData : null
      })
        .then(response => {
          if (response.ok || response.status == 422) {
            return response.text();
          } else {
            alert(
              "Server returned " + response.status + " : " + response.statusText
            );
          }
        })
        .then(response => {
          // Populate rawJson
          this.rawJson = response;

          // Parse json repsonse
          var responseJson = JSON.parse(response);

          // Show error message if there was an issue
          if ("detail" in responseJson) {
            for (let d of responseJson.detail) {
              for (let name of d.loc) {
                this.error_messages.push(name + ": " + d.msg)
              }
            }
            this.isLoading = false
            this.responseAvailable = false
            return
          }

          // Parse plot from json to image data
          this.plots = [
            { name: "LV network voltages comparison", 
            info: "Plots the range, interquartile range and median customer voltages, simulated for each time period, and for each of the LV networks that are modelled in detail.",
            info2:"Voltages (on the y-axis) are given in per-unit: multiplying by 230 will give the voltage in volts (e.g., 1.10 per unit is the same as 253 volts).",
            values:"If any part of the plotted graphs passes the dashed red lines (labelled Lower and Upper limit, at 0.94 and 1.10 per unit respectively) then the voltage will have passed outside of the steady-state voltage limits for the UK.",
            plot: responseJson["lv_comparison"], data_filename: "lv_comparison.csv", data_url: URL.createObjectURL(new Blob([responseJson["lv_comparison_data"]], {type: "text/csv"})) },

            { name: "Transformer powers",
            info:"Plots the total utilization, in %, of the primary (HV to MV) and secondary (MV to LV) substations.",
            info2:"The power flow (in kVA) through the modelled secondary substations can be found by multiplying by the rating of that substation (within the legend, inset).",
            values:"NB: the utilization is based on the apparent power, and so the utilization is always positive.", 
            plot: responseJson["trn_powers"], data_filename: "transformer_powers.csv", data_url: URL.createObjectURL(new Blob([responseJson["trn_powers_data"]], {type: "text/csv"})) },

            { name: "Primary feeders' loadings",
            info:"The apparent power, in %, at the top of each of the MV feeders. ",
            info2:"The feeders can be identified by the node to which the feeder is connected from the primary substation (see “MV network overview (detailed)” figure).",
            values:"NB: the power reported is based on the apparent power, and is always positive.",
            plot: responseJson["pmry_loadings"], data_filename: "primary_loadings.csv", data_url: URL.createObjectURL(new Blob([responseJson["primary_loadings_data"]], {type: "text/csv"})) },

            // { name: "Primary feeders' powers", plot: responseJson["pmry_powers"] },
            { name: "MV network voltages",
            info:"Similar to “LV network voltages comparison”: this figure plots the range (max / min), interquartile range and median voltage for nodes on the MV network.",
            info2:"The voltage limits for MV networks are narrower than LV networks. These should be between 0.94 and 1.06 per unit.",
            plot: responseJson["mv_voltages"], data_filename: "mv_voltages.csv", data_url: URL.createObjectURL(new Blob([responseJson["mv_voltages_data"]], {type: "text/csv"})) },

            // { name: "MV network powers", plot: responseJson["mv_powers"] },
            { name: "MV network overview (basic)",
            info:"Plots the topology of the MV network.",
            info2:"Residential and I&C lumped loads are indicated alongside the locations the LV networks which are modelled in detail.",
            values:"The central black and white hexagon indicates the location of the HV-MV (primary) substation.",
            plot: responseJson["mv_highlevel_clean"] },

            { name: "MV network overview (detailed)",
            info:"Plots the topology of the MV network in detail.",
            info2:"This includes: (i) the ID for each node, (ii) the locations of the LV modelled networks (iii) the locations of the modelled EV fast charging stations; (iv) the locations of the large solar (denoted ‘large DG’) (v) the locations of lumped residential and I&C loads.",
            plot: responseJson["mv_highlevel"] },

            { name: "Average of LV profiles",
            info:"Plots the mean power, in kW, for the LV profiles. Individual profiles, not their average which is shown here, are used in the simulations.",
            info2:"Negative values imply generation (e.g., for solar profiles or vehicle-to-grid).",
            plot: responseJson["profile_options"] },

            { name: "MV distributed generation average profile",
            info:"Plots the mean power, in kW, for the MV DG profiles. Individual profiles, not their average which is shown here, are used in the simulations.",
            info2:"If no DG profiles are selected or uploaded, then an empty figure is shown.",
            plot: responseJson["profile_options_dgs"] },

            { name: "MV fast charging stations average profile",
            info:"Plots the mean power, in kW, for the MV FC profiles. Individual profiles, not their average which is shown here, are used in the simulations.",
            info2:"If no FC profiles are selected or uploaded, then an empty figure is shown.",
            plot: responseJson["profile_options_fcs"] },

          ];

          this.responseAvailable = true;
          this.isLoading = false;
        })
        .catch(err => {
          console.log(err);
        });
    },

    appendProfileParams(url_params, form_data, name, params) {
      url_params[name + "_profile"] = params.profile;
      if (params.profile == "csv") {
        url_params[name + "_units"] = params.units;
        if ( (params.csv == null) || (params.csv.length !== 1) ) {
          this.invalid_csvs.push(name)
        }
        else {
          form_data.set(name + "_csv", params.csv[0]);
        }
      }
      if (params.penetration !== undefined && params.profile !== "None") {
        url_params[name + "_pen"] = params.penetration;
      }
      return url_params, form_data
    },

    getProfileOptions(profile_name) {
      return fetch(
        process.env.VUE_APP_API_URL +
          "/get-options?option_type=" +
          profile_name,
        {
          method: "GET"
        }
      )
        .then(response => {
          if (response.ok) {
            return response.text();
          } else {
            alert(
              "Server returned " + response.status + " : " + response.statusText
            );
          }
        })
        .then(response => {
          return JSON.parse(response);
        })
        .catch(err => {
          console.log(err);
        });
    },

    updateLVNetworksList() {
      return fetch(
        process.env.VUE_APP_API_URL + "/lv-network?n_id=" + this.network_options.n_id,
        {
          method: "GET"
        }
      )
        .then(response => {
          if (response.ok) {
            return response.text();
          } else {
            alert(
              "Server returned " + response.status + " : " + response.statusText
            );
          }
        })
        .then(response => {
          this.lv_options.lv_list = JSON.parse(response).networks;
          this.updatePreselectedLVNetworksList()
        })
        .catch(err => {
          console.log(err);
        });
    },

    updatePreselectedLVNetworksList() {
      if (this.lv_options.lv_default != "custom") {
        return fetch(
          process.env.VUE_APP_API_URL + "/lv-network-defaults?n_id=" + this.network_options.n_id + "&lv_default=" + this.lv_options.lv_default,
          {
            method: "GET"
          }
        )
          .then(response => {
            if (response.ok) {
              return response.text();
            } else {
              alert(
                "Server returned " + response.status + " : " + response.statusText
              );
            }
          })
          .then(response => {
            this.lv_options.lv_selected = JSON.parse(response).networks;
          })
          .catch(err => {
            console.log(err);
          });
      }
    }
  }
};
</script>

<style scoped>
.form-check {
  margin-bottom: 15px;
}
#displayBox {
  margin-top: 20px;
}
</style>
