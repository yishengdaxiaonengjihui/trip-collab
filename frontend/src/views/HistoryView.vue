<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { api } from "@/api";
import { toast } from "@/store";
import type { VersionInfo } from "@/types";

const route = useRoute();
const tripId = route.params.id as string;

const versions = ref<VersionInfo[]>([]);
const currentVersion = ref(0);
const loading = ref(true);
const confirmSheet = ref<{ version: number } | null>(null);
const acting = ref(false);

const kindLabel: Record<string, string> = {
  adopt: "采纳",
  emergency: "临时备选",
  rollback: "回滚",
  revoke: "撤销",
};

async function load() {
  loading.value = true;
  try {
    const [vs, trip] = await Promise.all([api.listVersions(tripId), api.getTrip(tripId)]);
    versions.value = vs;
    currentVersion.value = trip.version;
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    loading.value = false;
  }
}

async function doRollback() {
  if (!confirmSheet.value || acting.value) return;
  acting.value = true;
  try {
    const res = await api.rollback(tripId, confirmSheet.value.version);
    toast(`已回滚到 v${res.target_version}（新版本 v${res.new_version}）`);
    confirmSheet.value = null;
    await load();
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    acting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <header class="topbar">
    <button class="back" @click="$router.back()">‹</button>
    <div class="tb-title">
      <div class="tb-name">版本历史</div>
      <div class="tb-meta">每次采纳/回滚生成一个版本，可一键回到过去</div>
    </div>
  </header>

  <main class="view">
    <div v-if="loading" class="empty">加载中…</div>
    <template v-else>
      <div class="section-title">当前定稿 · v{{ currentVersion }}</div>
      <div
        v-for="v in [...versions].reverse()"
        :key="v.version"
        class="card v-card"
        :class="{ current: v.version === currentVersion }"
      >
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div>
            <span class="v-ver">v{{ v.version }}</span>
            <span class="pill" style="margin-left: 6px" :class="{
              'pill-adopted': v.kind === 'adopt',
              'pill-emergency': v.kind === 'emergency',
              'pill-rejected': v.kind === 'rollback' || v.kind === 'revoke',
            }">{{ kindLabel[v.kind] }}</span>
          </div>
          <span class="item-sub">{{ v.item_count }} 条安排</span>
        </div>
        <div class="p-reason" v-if="v.title">「{{ v.title }}」</div>
        <div class="btn-row" v-if="v.version !== currentVersion">
          <button class="btn btn-ghost btn-sm" @click="confirmSheet = { version: v.version }">
            回滚到 v{{ v.version }}
          </button>
        </div>
        <div v-else class="item-sub" style="margin-top: 6px">✓ 当前定稿</div>
      </div>
      <div v-if="!versions.length" class="empty">还没有版本记录</div>
    </template>
  </main>

  <div v-if="confirmSheet" class="mask" @click.self="confirmSheet = null">
    <div class="sheet">
      <h3>回滚到 v{{ confirmSheet.version }}？</h3>
      <div class="sub">
        定稿将恢复到 v{{ confirmSheet.version }} 的状态，之后采纳的改动会被补偿回去（历史保留），受影响的人会收到通知。
      </div>
      <div class="btn-row">
        <button class="btn btn-ghost" :disabled="acting" @click="confirmSheet = null">取消</button>
        <button class="btn btn-danger" :disabled="acting" @click="doRollback">
          {{ acting ? "回滚中…" : "确认回滚" }}
        </button>
      </div>
    </div>
  </div>
</template>
