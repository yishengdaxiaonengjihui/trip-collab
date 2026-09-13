<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { api } from "@/api";
import { toast } from "@/store";
import type { TripBrief } from "@/types";

const router = useRouter();
const trips = ref<TripBrief[]>([]);
const newName = ref("");
const creating = ref(false);

async function load() {
  trips.value = await api.listTrips();
}

async function create() {
  const name = newName.value.trim();
  if (!name) return;
  creating.value = true;
  try {
    const trip = await api.createTrip(name);
    newName.value = "";
    await load();
    router.push(`/trips/${trip.id}`);
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    creating.value = false;
  }
}

onMounted(load);
</script>

<template>
  <header class="topbar">
    <div class="tb-title">
      <div class="tb-name">🧳 旅行协作规划</div>
      <div class="tb-meta">MVP 骨架 · 多人版本化</div>
    </div>
  </header>
  <main class="view">
    <div class="section-title">我的行程</div>
    <button
      v-for="t in trips"
      :key="t.id"
      class="card trip-card"
      style="width: 100%; text-align: left; border: none; cursor: pointer"
      @click="router.push(`/trips/${t.id}`)"
    >
      <div class="t-name">{{ t.name }}</div>
      <div class="t-meta">
        v{{ t.version }} · {{ t.item_count }} 条安排 · 待审核 {{ t.pending_count }}
      </div>
    </button>
    <div v-if="!trips.length" class="empty">还没有行程，先建一个试试 👇</div>

    <div class="section-title">新建行程</div>
    <div class="card form">
      <input v-model="newName" placeholder="行程名称，如：西安 3 日游" @keyup.enter="create" />
      <div class="btn-row">
        <button class="btn btn-primary" :disabled="creating || !newName.trim()" @click="create">
          {{ creating ? "创建中…" : "创建" }}
        </button>
      </div>
    </div>
  </main>
</template>
