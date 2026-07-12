<template>
  <!-- REDESIGN (P3): content moved here from the retired WalkthroughModal. -->
  <div class="hiw">
    <h1>How it works</h1>
    <p class="hiw-lede">
      Three steps to build and simulate an electricity distribution network with
      EVs, PVs and heat pumps.
    </p>

    <ol class="hiw-steps">
      <li>
        <b>Choose the network.</b>
        Keep the defaults or change them. The integrated MV–LV 11&nbsp;kV urban
        network represents a town of around 20,000 households. You can simulate
        up to five LV networks in detail — the equivalent of five
        neighbourhoods.
      </li>
      <li>
        <b>Add technologies and data.</b>
        Use the built-in demand and generation profiles or upload your own. Add
        distributed generation (e.g. commercial solar) and fast-charging
        stations on the 11&nbsp;kV network, then set the mix and penetration of
        green technologies in homes.
      </li>
      <li>
        <b>Run the simulation.</b>
        Results usually arrive in under a minute. They lead with a verdict —
        voltage and transformer loading against their statutory limits —
        followed by the detailed figures, which you can download as CSV.
      </li>
    </ol>

    <p class="hiw-note">
      To learn more about the network models and the methodology, see the
      open-access paper
      <a
        href="https://www.cambridge.org/core/journals/data-centric-engineering/article/democratizing-electricity-distribution-network-analysis/DB2B110FF185C5CC20A4E5B28B85449B"
        target="_blank"
        rel="noopener"
        >Democratizing electricity distribution network analysis</a
      >
      (<i>Data-Centric Engineering</i>) and the
      <a
        href="https://github.com/deakinmt/uk-mvlv-models"
        target="_blank"
        rel="noopener"
        >UK MV–LV network models on GitHub</a
      >.
    </p>

    <img
      class="hiw-img"
      src="../assets/images/overview_urban.png"
      alt="Urban network overview"
    />
    <img
      class="hiw-img"
      src="../assets/images/networks_v3.png"
      alt="Example LV networks"
    />
  </div>
</template>

<script>
export default { name: "HowItWorks" };
</script>

<style scoped>
.hiw {
  max-width: 760px;
  margin: 0 auto;
}
.hiw h1 {
  font-size: 1.6rem;
  font-weight: 600;
  margin-bottom: 6px;
}
.hiw-lede {
  color: var(--muted);
  margin-bottom: 20px;
}
.hiw-steps {
  padding-left: 1.1rem;
}
.hiw-steps li {
  margin: 0.7rem 0;
  line-height: 1.55;
}
.hiw-note {
  margin-top: 18px;
  color: var(--muted);
}
.hiw-img {
  max-width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  margin: 16px 0;
}
</style>
