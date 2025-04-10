import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import GarsvielasView from "../views/GarsvielasView.vue";
import CikadeView from "../views/CikadeView.vue";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
  },
  {
    path: "/garsvielas",
    name: "garsvielas",
    component: GarsvielasView,
  },
  {
    path: "/cikade",
    name: "cikade",
    component: CikadeView,
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router;
