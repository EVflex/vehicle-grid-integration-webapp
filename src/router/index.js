import { createRouter, createWebHistory } from "vue-router";
import NavBar from "@/layouts/NavBar.vue";

const routes = [
  {
    path: "/",
    component: NavBar,
    children: [
      {
        path: "",
        name: "Home",
        // route level code-splitting
        // this generates a separate chunk (about.[hash].js) for this route
        // which is lazy-loaded when the route is visited.
        component: () =>
          import(/* webpackChunkName: "home" */ "../views/Home.vue")
      },
      {
        path: "simulate_network",
        name: "SimulateNetworkAPI",
        component: () =>
          import(
            /* webpackChunkName: "simulate_network" */ "../views/SimulateNetworkAPI.vue"
          )
      },
      {
        path: "resources",
        name: "Resources",
        component: () =>
          import(
            /* webpackChunkName: "resources" */ "../views/Resources.vue"
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
