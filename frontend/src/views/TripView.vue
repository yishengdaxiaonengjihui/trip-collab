<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api } from "@/api";
import { appState, toast } from "@/store";
import type { Item, Trip } from "@/types";

const route = useRoute();
const router = useRouter();
const tripId = route.params.id as string;

const trip = ref<Trip | null>(null);
const loading = ref(true);
const quickOpen = ref(false);
const quickBusy = ref(false);

const days = computed(() => {
  if (!trip.value) return [];
  return Object.entries(trip.value.days)
    .map(([day, items]) => ({ day: Number(day), items: [...items].sort((a, b) => timeKey(a).localeCompare(timeKey(b))) }))
    .sort((a, b) => a.day - b.day);
});

// 时间线排序键：有 HH:MM 时间的按时间排，无时间的按 position 排最后
function timeKey(it: Item): string {
  const m = /^(\d{1,2}):(\d{2})/.exec(it.time || "");
  if (m) return "T" + m[1].padStart(2, "0") + m[2];
  return "Z" + String(it.position).padStart(4, "0");
}

const TAG_CLASS: Record<string, string> = {
  景区: "tag-scenic",
  饭店: "tag-food",
  酒店: "tag-hotel",
  交通: "tag-transport",
  购物: "tag-shopping",
};

function tagClass(tag: string): string {
  return TAG_CLASS[tag] || "tag-other";
}

const DAY_THEMES = ["抵达 · 市区", "东线 · 人文", "市区 · 返程", "远郊 · 自然"];

function dayTheme(day: number): string {
  return DAY_THEMES[(day - 1) % DAY_THEMES.length];
}

async function load() {
  loading.value = true;
  try {
    trip.value = await api.getTrip(tripId);
    appState.currentTrip = trip.value;
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    loading.value = false;
  }
}

function openQuick() {
  quickOpen.value = true;
}

async function quickAction(item: Item, action: "close" | "retime") {
  quickBusy.value = true;
  try {
    const events =
      action === "close"
        ? [{ kind: "deleted" as const, item_id: item.id }]
        : [{ kind: "updated" as const, item_id: item.id, payload: { note: "时间待定（临时）" } }];
    const p = await api.createProposal(tripId, {
      title: action === "close" ? `临时取消「${item.title}」` : `临时改「${item.title}」时间`,
      reason: "旅途应急 · 提交即生效，可事后正式化或撤销",
      events,
      emergency: true,
    });
    await api.applyEmergency(tripId, p.id);
    quickOpen.value = false;
    toast(action === "close" ? "已临时取消，全员可见" : "已临时改期，全员可见");
    await load();
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    quickBusy.value = false;
  }
}

onMounted(load);
</script>

<template>
  <header class="topbar">
    <button class="back" @click="router.push('/')">‹</button>
    <div class="tb-title">
      <div class="tb-name">{{ trip?.name || "行程" }}</div>
      <div class="tb-meta" v-if="trip">版本 v{{ trip.version }} · {{ trip.members.length }} 人</div>
    </div>
    <button class="icon-btn" @click="router.push(`/trips/${tripId}/notify`)">🔔</button>
  </header>

  <main class="view">
    <div v-if="loading" class="empty">加载中…</div>

    <template v-else-if="trip">
      <div class="section-title">📌 最终定稿行程 · 版本 v{{ trip.version }}</div>

      <div v-if="trip.pending_count > 0" class="card warn-box" style="cursor: pointer" @click="router.push(`/trips/${tripId}/proposals`)">
        ⚠️ 有 {{ trip.pending_count }} 条待审核提议：采纳后才会改定稿 →
      </div>

      <div v-for="d in days" :key="d.day" class="timeline">
        <div class="tl-day-head">
          <span class="day-tag">第 {{ d.day }} 天</span>
          <span class="day-title">{{ dayTheme(d.day) }}</span>
        </div>
        <div class="tl-items">
          <div v-for="it in d.items" :key="it.id" class="tl-item">
            <div class="tl-rail">
              <span class="tl-dot" :class="tagClass(it.tag)"></span>
            </div>
            <div class="tl-card" :class="tagClass(it.tag)">
              <div class="tl-top">
                <span class="tl-time">{{ it.time || "—" }}</span>
                <span class="tl-tag">{{ it.tag || "其他" }}</span>
              </div>
              <div class="tl-title">{{ it.title }}</div>
              <div class="tl-sub" v-if="it.refs.length">依赖：{{ it.refs.join("、") }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!days.length" class="empty">定稿还是空的，去「提议」建一条吧</div>
    </template>
  </main>

  <button v-if="trip" class="fab" @click="openQuick">⚡ 旅途应急</button>

  <div v-if="quickOpen" class="mask" @click.self="quickOpen = false">
    <div class="sheet">
      <h3>⚡ 旅途应急</h3>
      <div class="sub">当场遇到突发状况？选一条安排，立即生效（全员可见），事后可撤销。</div>
      <div v-for="d in days" :key="'q' + d.day">
        <div class="section-title">第 {{ d.day }} 天</div>
        <button
          v-for="it in d.items"
          :key="it.id"
          class="card item-row"
          style="width: 100%; border: none; cursor: pointer; text-align: left"
          @click="quickAction(it, 'close')"
        >
          <div style="flex: 1">
            <div class="item-title">🚫 取消「{{ it.title }}」</div>
            <div class="item-sub">点击立即生效</div>
          </div>
        </button>
      </div>
      <div class="btn-row">
        <button class="btn btn-ghost" :disabled="quickBusy" @click="quickOpen = false">关闭</button>
      </div>
    </div>
  </div>
</template>
