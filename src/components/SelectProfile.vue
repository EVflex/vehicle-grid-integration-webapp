<template>

    <!-- Dropdown box to select preselected/csv profile -->
    <div class="form-group row">
        <label for="profile_option_dropdown" class="col-md-6 col-form-label">
            {{ title }}
            <!-- <input-details :inputName="title"
                            inputInfo="Choose from available profiles or upload your own data. More information on the available profiles can be found in the project repositories."
                            inputValues="If uploading your own profile, please upload a csv file with a header and 48 rows corresponding to 1 day at 30-minute resolution data. There is no limit on the number of columns that can be uploaded (i.e. several days of data)."
                            inputExampleLink="https://github.com/alan-turing-institute/vehicle-grid-integration-webapp-private/blob/main/vgi_api/vgi_api/data/example_profile.csv"/> -->
        </label>
        <div class="col-md-6" name="profile_option_dropdown">
            <select class="form-control" v-model="profile">
                <option v-for="profile in this.profileOptions.list" :key="profile">{{ profile }}</option>
            </select>
        </div>
    </div>

    <!-- If custom csv, provide file and units -->
    <template v-if="this.profileOptions.profile == 'csv'">
        <div class="form-group row">
            <div class="col-md-6 offset-md-6">
                <div class="custom-file" id="customFile" lang="es">
                    <input type="file" v-on:change="onCsvUpload" class="custom-file-input" id="profile_csv">
                    <label class="custom-file-label" for="profile_csv">
                        {{ csv_name_text }}
                    </label>
                </div>
            </div>
        </div>
        <div class="form-group row">
            <label for="profile_units" class="col-md-3 offset-md-6 col-form-label">Units</label>
            <div class="col-md-3">
                <select name="profile_units" v-model="units" class="form-control">
                    <option>kW</option>
                    <option>kWh</option>
                </select>
            </div>
        </div>
    </template>

    <!-- Penetration is only needed for LV networks where a profile has been provided -->
    <div v-if="profileOptions.penetration !== undefined && profileOptions.profile !== 'None'" class="form-group row">
        <label for="profile_pen" class="col-md-3 offset-md-6 col-form-label">
            Penetration
            <input-details inputName="Penetration" inputValues="Value should be between 0 and 1"/>
        </label>
        <div class="col-md-3">
            <input
            v-model="penetration"
            type="float"
            class="form-control"
            id="profile_pen"
            />
        </div>
        <div v-for="error of penValidation" :key="error.$uid" class="col-md-6 offset-md-6 col-form-label text-danger">
            {{ error.$message }}
        </div>
    </div>

</template>

<script>
import InputDetails from "./InputDetails.vue"
    export default {
        components: { InputDetails },
        props: ["profileOptions", "title", "penValidation"],
        emits: ["update:profileOptions"],
        computed: {
            profile: {
                get() {
                    return this.profileOptions.profile
                },
                set(profile) {
                    let profile_options = this.profileOptions
                    profile_options.profile = profile
                    if (profile == "None") {
                        profile_options.penetration = 1
                    }
                    this.$emit("update:profileOptions", profile_options)
                }
            },
            units: {
                get() {
                    return this.profileOptions.units
                },
                set(units) {
                    let profile_options = this.profileOptions
                    profile_options.units = units
                    this.$emit("update:profileOptions", profile_options)
                }
            },
            penetration: {
                get() {
                    return this.profileOptions.penetration
                },
                set(penetration) {
                    let profile_options = this.profileOptions
                    profile_options.penetration = penetration
                    this.$emit("update:profileOptions", profile_options)
                }
            },
        },
        methods: {
            onCsvUpload(event) {
                let incoming_csv = event.target.files || event.dataTransfer.files
                let profile_options = this.profileOptions
                profile_options.csv = incoming_csv
                this.csv_name_text = profile_options.csv[0].name
                this.$emit("update:profileOptions", profile_options)
            }
        },
        data() {
            return { csv_name_text: "Upload a profile" }
        }
    }
</script>