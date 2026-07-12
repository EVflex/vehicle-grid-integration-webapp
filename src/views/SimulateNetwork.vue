<template>
  <div>
    <h3>Build and simulate an electricity distribution network</h3>
    <p>
      You can find more information on OpenDSS parameters below in the
      <a
        href="http://svn.code.sf.net/p/electricdss/code/trunk/Distrib/Doc/OpenDSSManual.pdf"
        >OpenDSS Manual</a
      >.
    </p>
    <form id="config" ref="config">
      <!-- Experiment name -->
      <div class="form-group row">
        <label for="name" class="col-md-2 col-form-label">Config name</label>
        <div class="col-md-3">
          <input
            v-model="config.name"
            type="text"
            class="form-control"
            id="name"
            placeholder="Name"
          />
        </div>
      </div>
      <!-- Max interations -->
      <div class="form-group row">
        <label for="maxIter" class="col-md-2 col-form-label"
          >Max iterations</label
        >
        <div class="col-md-3">
          <input
            v-model="config.maxIter"
            type="number"
            class="form-control"
            id="maxIter"
            aria-describedby="iterHelp"
            placeholder="Iterations"
          />
          <small id="iterHelp" class="form-text text-muted"
            >Solutions can take more than the default 15 iterations.</small
          >
        </div>
      </div>
      <!-- Transformer parameters  -->
      <fieldset class="form-group">
        <div class="row">
          <legend class="col-md-2 col-form-label pt-0">
            Transformer
          </legend>
          <div class="col-md-3">
            <div class="form-group">
              <label for="phases">Number of phases</label>
              <input
                v-model="config.transformer.phases"
                type="number"
                class="form-control"
                id="phases"
              />
            </div>
            <div class="form-group">
              <label for="windings">Number of windings</label>
              <input
                v-model="config.transformer.windings"
                type="number"
                class="form-control"
                id="windings"
              />
            </div>
            <div class="form-group">
              <label for="kva">Base kVA rating of winding(s)</label>
              <input
                v-model="config.transformer.kva"
                type="float"
                class="form-control"
                id="kva"
              />
            </div>
          </div>
        </div>
      </fieldset>
      <!-- Save  -->
      <div class="form-check">
        <input
          v-model="config.save"
          type="checkbox"
          class="form-check-input"
          id="save"
        />
        <label class="form-check-label" for="save">Save configuration</label>
      </div>
      <!-- Submit Button  -->
      <button
        type="submit"
        class="btn btn-primary"
        @click.prevent="this.display = true"
      >
        Submit
      </button>
    </form>
    <p id="displayBox" v-if="display">Parameters submitted: {{ config }}</p>
  </div>
</template>

<script>
export default {
  data() {
    return {
      config: {
        name: "",
        transformer: {
          phases: 3,
          windings: 2,
          kva: 500
        },
        maxIter: 15,
        save: false
      },
      display: false
    };
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
