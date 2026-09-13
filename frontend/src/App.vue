<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const tripId = computed(() => (route.params.id as string) || "");
const isHome = computed(() => route.path === "/");

const nav = [
  { view: "trip", label: "行程", icon: "🗺️", to: () => `/trips/${tripId.value}` },
  { view: "proposals", label: "提议", icon: "📋", to: () => `/trips/${tripId.value}/proposals` },
  { view: "new", label: "新建", icon: "＋", to: () => `/trips/${tripId.value}/new`, plus: true },
  { view: "history", label: "版本", icon: "🕘", to: () => `/trips/${tripId.value}/history` },
  { view: "notify", label: "通知", icon: "🔔", to: () => `/trips/${tripId.value}/notify` },
];

function activeView(): string {
  if (route.path.includes("/proposals")) return "proposals";
  if (route.path.includes("/new")) return "new";
  if (route.path.includes("/history")) return "history";
  if (route.path.includes("/notify")) return "notify";
  return "trip";
}
</script>

<template>
  <div id="toastRoot"></div>
  <router-view />
  <nav v-if="!isHome" class="bottom-nav">
    <button
      v-for="n in nav"
      :key="n.view"
      class="nav-item"
      :class="{ active: activeView() === n.view }"
      @click="router.push(n.to())"
    >
      <span class="nav-ico">{{ n.icon }}</span>
      <span>{{ n.label }}</span>
    </button>
  </nav>
</template>
