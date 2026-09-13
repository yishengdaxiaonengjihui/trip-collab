import { createRouter, createWebHistory } from "vue-router";

import HistoryView from "./views/HistoryView.vue";
import NewProposalView from "./views/NewProposalView.vue";
import NotifyView from "./views/NotifyView.vue";
import ProposalsView from "./views/ProposalsView.vue";
import TripView from "./views/TripView.vue";
import TripsView from "./views/TripsView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "trips", component: TripsView },
    { path: "/trips/:id", name: "trip", component: TripView },
    { path: "/trips/:id/proposals", name: "proposals", component: ProposalsView },
    { path: "/trips/:id/new", name: "new-proposal", component: NewProposalView },
    { path: "/trips/:id/history", name: "history", component: HistoryView },
    { path: "/trips/:id/notify", name: "notify", component: NotifyView },
  ],
});
