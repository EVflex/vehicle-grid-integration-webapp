<template>
  <!-- REDESIGN: technology row = on/off toggle + inline profile + % slider + csv.
       Replaces the old plain dropdown + 0-1 decimal penetration input. -->
  <div class="tech-row" :class="{ off: !enabled }">
    <div class="tech-main">
      <button
        type="button"
        class="evt-toggle"
        :class="{ on: enabled }"
        role="switch"
        :aria-checked="enabled ? 'true' : 'false'"
        :aria-label="'Enable ' + title"
        @click="enabled = !enabled"
      ></button>

      <span class="tech-name">{{ title }}</span>

      <select
        v-if="enabled"
        class="form-control form-control-sm tech-select"
        v-model="profile"
        :aria-label="title + ' profile'"
      >
        <option v-for="opt in realOptions" :key="opt" :value="opt">
          {{ opt === "csv" ? "Upload your own (CSV)" : opt }}
        </option>
      </select>
      <span v-else class="tech-off-note">Off</span>

      <!-- Penetration % slider (LV technologies only) -->
      <div v-if="enabled && hasPenetration" class="tech-pen">
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          v-model.number="penetration"
          :aria-label="title + ' penetration percent'"
        />
        <span class="evt-mono tech-pen-val">{{ penetration }}%</span>
      </div>
    </div>

    <!-- CSV upload + units, shown when 'Upload your own' is chosen -->
    <div v-if="enabled && profile === 'csv'" class="tech-csv">
      <div class="custom-file">
        <input
          type="file"
          accept=".csv"
          @change="onCsvUpload"
          class="custom-file-input"
          :id="'csv_' + uid"
        />
        <label class="custom-file-label" :for="'csv_' + uid">{{
          csvNameText
        }}</label>
      </div>
      <select
        v-model="units"
        class="form-control form-control-sm tech-units"
        aria-label="CSV units"
      >
        <option>kW</option>
        <option>kWh</option>
      </select>
    </div>

    <!-- Expected CSV format (the API rejects anything else, so say so up
         front): one day of half-hourly values; diversity comes from columns. -->
    <p v-if="enabled && profile === 'csv'" class="tech-csv-hint">
      Format: a header row, then 48 half-hour rows (00:00:00–23:30:00). Column 1
      is the time; every further column is one daily profile in kW (or kWh per
      half-hour).
      <a href="#" @click.prevent="downloadTemplate">Download a template</a>
    </p>

    <!-- Penetration validation errors -->
    <div
      v-for="error of penValidation"
      :key="error.$uid"
      class="text-danger tech-err"
    >
      {{ error.$message }}
    </div>
  </div>
</template>

<script>
export default {
  props: ["profileOptions", "title", "penValidation"],
  // "change" signals a genuine user edit (distinct from programmatic updates
  // like the parent loading profile lists), so the parent can drop the preset.
  emits: ["update:profileOptions", "change"],
  data() {
    return {
      csvNameText: "Choose a CSV file",
      // Remember the last real profile so toggling back on restores the choice.
      lastReal: null
    };
  },
  computed: {
    uid() {
      // Stable-enough id for the file input label association.
      return (this.title || "row").replace(/\s+/g, "_").toLowerCase();
    },
    hasPenetration() {
      return this.profileOptions.penetration !== undefined;
    },
    realOptions() {
      // Everything except "None" — the toggle handles the None case.
      return (this.profileOptions.list || []).filter(o => o !== "None");
    },
    enabled: {
      get() {
        return (
          this.profileOptions.profile !== "None" &&
          this.profileOptions.profile != null
        );
      },
      set(on) {
        const opts = { ...this.profileOptions };
        if (on) {
          const target = this.lastReal || this.realOptions[0] || "None";
          opts.profile = target;
        } else {
          if (
            this.profileOptions.profile !== "None" &&
            this.profileOptions.profile != null
          ) {
            this.lastReal = this.profileOptions.profile;
          }
          opts.profile = "None";
          if (opts.penetration !== undefined) opts.penetration = 0;
        }
        this.commit(opts);
      }
    },
    profile: {
      get() {
        return this.profileOptions.profile;
      },
      set(profile) {
        if (profile !== "None" && profile !== "csv") this.lastReal = profile;
        const opts = { ...this.profileOptions, profile };
        this.commit(opts);
      }
    },
    units: {
      get() {
        return this.profileOptions.units;
      },
      set(units) {
        this.commit({ ...this.profileOptions, units });
      }
    },
    penetration: {
      get() {
        return this.profileOptions.penetration;
      },
      set(penetration) {
        this.commit({ ...this.profileOptions, penetration });
      }
    }
  },
  methods: {
    commit(opts) {
      this.$emit("update:profileOptions", opts);
      this.$emit("change");
    },
    onCsvUpload(event) {
      const files =
        event.target.files || (event.dataTransfer && event.dataTransfer.files);
      if (!files || !files.length) return;
      this.csvNameText = files[0].name;
      this.commit({ ...this.profileOptions, csv: files });
    },
    downloadTemplate() {
      // 48 half-hour rows, three example profile columns — matches the API's
      // validate_csv contract (header + 48 rows, 30-min steps, floats).
      const rows = ["Time,profile_1,profile_2,profile_3"];
      for (let i = 0; i < 48; i++) {
        const h = String(Math.floor(i / 2)).padStart(2, "0");
        const m = i % 2 ? "30" : "00";
        rows.push(`${h}:${m}:00,0.0,0.0,0.0`);
      }
      const blob = new Blob([rows.join("\n") + "\n"], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = this.uid + "-profile-template.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    }
  }
};
</script>

<style scoped>
.tech-row {
  padding: 9px 0;
  border-top: 1px solid var(--line);
}
.tech-row:first-child {
  border-top: none;
}
.tech-row.off {
  opacity: 0.55;
}
.tech-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.tech-name {
  font-size: 0.9rem;
  min-width: 130px;
  flex: 1 1 130px;
}
.tech-select {
  max-width: 190px;
  flex: 0 1 190px;
}
.tech-off-note {
  font-size: 0.8rem;
  color: var(--muted);
  flex: 0 1 190px;
}
.tech-pen {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tech-pen input[type="range"] {
  width: 130px;
  accent-color: var(--accent);
}
.tech-pen-val {
  font-size: 0.82rem;
  min-width: 40px;
  text-align: right;
}
.tech-csv {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
  padding-left: 46px;
}
.tech-csv .custom-file {
  max-width: 240px;
}
.tech-units {
  max-width: 90px;
}
.tech-err {
  font-size: 0.78rem;
  padding-left: 46px;
  margin-top: 4px;
}
.tech-csv-hint {
  font-size: 0.75rem;
  color: var(--muted);
  padding-left: 46px;
  margin: 6px 0 0;
  max-width: 60ch;
}
.tech-csv-hint a {
  white-space: nowrap;
}
</style>
