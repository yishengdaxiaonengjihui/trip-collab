<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { api } from "@/api";
import { toast } from "@/store";
import type { NotificationItem } from "@/types";

const route = useRoute();
const tripId = route.params.id as string;

const items = ref<NotificationItem[]>([]);
const loading = ref(true);

const kindMeta: Record<string, { ico: string; label: string }> = {
  proposal_created: { ico: "📝", label: "提交了提议" },
  proposal_submitted: { ico: "📨", label: "提议进入待审核" },
  proposal_adopted: { ico: "✅", label: "已采纳，定稿已更新" },
  proposal_rejected: { ico: "🚫", label: "拒绝了提议" },
  emergency_applied: { ico: "⚡", label: "临时备选已生效" },
  proposal_formalized: { ico: "📌", label: "临时备选已正式化" },
  proposal_revoked: { ico: "↩️", label: "撤销了临时备选" },
  rollback_affected: { ico: "⚠️", label: "你的改动被回滚覆盖" },
};

function meta(kind: string) {
  return kindMeta[kind] || { ico: "🔔", label: kind };
}

onMounted(async () => {
  try {
    items.value = await api.listNotifications(tripId);
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <header class="topbar">
    <button class="back" @click="$router.back()">‹</button>
    <div class="tb-title">
      <div class="tb-name">通知</div>
      <div class="tb-meta">定稿变化的每一次记录</div>
    </div>
  </header>

  <main class="view">
    <div v-if="loading" class="empty">加载中…</div>
    <template v-else>
      <div v-for="n in [...items].reverse()" :key="n.seq" class="card n-item">
        <span class="n-ico">{{ meta(n.kind).ico }}</span>
        <div>
          <div>{{ meta(n.kind).label }} <span class="item-sub">· {{ n.actor }}</span></div>
          <div class="item-sub" v-if="n.payload.title">「{{ n.payload.title }}」</div>
        </div>
      </div>
      <div v-if="!items.length" class="empty">还没有通知</div>
    </template>
  </main>
</template>
