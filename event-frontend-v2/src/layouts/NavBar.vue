<template>
  <nav class="evt-nav">
    <!-- CHANGE(round2-4): the acronym expansion now sits as a small tagline
         UNDER the wordmark (a stacked block) instead of same-line next to
         it — the previous side-by-side layout read as cluttered. This is
         the ONLY place it appears (no duplicate in the page body). -->
    <router-link class="evt-brand" :to="{ name: 'SimulateNetworkAPI' }">
      <span class="evt-brand-word"
        ><i class="bi bi-lightning-charge-fill"></i> EVENT</span
      >
      <span class="evt-brand-sub">Electric Vehicle Network analysis Tool</span>
    </router-link>
    <div class="evt-nav-links">
      <router-link :to="{ name: 'SimulateNetworkAPI' }">Simulate</router-link>
      <router-link :to="{ name: 'HowItWorks' }">How it works</router-link>
    </div>
  </nav>
  <div class="evt-page">
    <router-view></router-view>
  </div>
</template>

<script>
export default { name: "NavBar" };
</script>

<style scoped>
.evt-nav {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--line);
  background: var(--card);
}
.evt-brand {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--ink);
  text-decoration: none;
  font-size: 1.05rem;
  line-height: 1.2;
}
.evt-brand-word {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.evt-brand .bi {
  color: var(--accent);
}
/* Small tagline under the wordmark, not a same-line subtitle. */
.evt-brand-sub {
  font-weight: 400;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--muted);
  font-size: 0.62rem;
}
/* Drop the long-form name when the nav gets tight. */
@media (max-width: 560px) {
  .evt-brand-sub {
    display: none;
  }
}
.evt-nav-links {
  display: flex;
  gap: 20px;
}
.evt-nav-links a {
  color: var(--muted);
  text-decoration: none;
  font-size: 0.9rem;
  padding-bottom: 2px;
}
.evt-nav-links a.router-link-exact-active {
  color: var(--ink);
  font-weight: 600;
  border-bottom: 2px solid var(--accent);
}
.evt-page {
  padding: 24px;
}
</style>
