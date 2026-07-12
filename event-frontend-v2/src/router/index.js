import { createRouter, createWebHistory } from "vue-router";
import NavBar from "@/layouts/NavBar.vue";

// REDESIGN (P3): Home merged into Simulate — Simulate is now the landing page.
// WalkthroughModal retired; its content lives on the How-it-works page.
// Resources page retired; the paper and model-repo links live on How-it-works.
const routes = [
  {
    path: "/",
    component: NavBar,
    children: [
      {
        path: "",
        name: "SimulateNetworkAPI",
        component: () =>
          import(
            /* webpackChunkName: "simulate_network" */ "../views/SimulateNetworkAPI.vue"
          )
      },
      {
        path: "how-it-works",
        name: "HowItWorks",
        component: () =>
          import(
            /* webpackChunkName: "how_it_works" */ "../views/HowItWorks.vue"
          )
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
