<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { api, HttpError } from "@/api";
import { toast } from "@/store";
import type { Proposal } from "@/types";

const route = useRoute();
const tripId = route.params.id as string;

const tab = ref<"pending" | "adopted" | "closed">("pending");
const proposals = ref<Proposal[]>([]);
const loading = ref(true);

const confirmSheet = ref<{
  title: string;
  body: string;
  danger: boolean;
  onOk: () => Promise<void>;
} | null>(null);
const note = ref("");
const acting = ref(false);

const kindLabel: Record<string, string> = {
  created: "新增",
  updated: "修改",
  deleted: "删除",
};

async function load() {
  loading.value = true;
  try {
    const list = await api.listProposals(tripId);
    proposals.value = list;
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    loading.value = false;
  }
}

function visible(): Proposal[] {
  const byStatus: Record<string, Proposal[]> = { pending: [], adopted: [], closed: [] };
  for (const p of proposals.value) {
    if (p.status === "pending") byStatus.pending.push(p);
    else if (p.status === "adopted") byStatus.adopted.push(p);
    else byStatus.closed.push(p);
  }
  return byStatus[tab.value];
}

function itemLabel(itemId: string): string {
  return itemId;
}

async function adopt(p: Proposal) {
  acting.value = true;
  try {
    await api.adoptProposal(tripId, p.id, {});
    toast("已采纳，定稿已更新");
    await load();
  } catch (e) {
    if (e instanceof HttpError && e.code === "ConfirmationRequiredError") {
      confirmSheet.value = {
        title: "确认采纳这条提议？",
        body: String(e.detail || e.message) + "\n\n这是一组需要人工复核的改动，确认后合并进定稿。",
        danger: false,
        onOk: async () => {
          await api.adoptProposal(tripId, p.id, { confirmed: true });
          toast("已采纳，定稿已更新");
          await load();
        },
      };
    } else if (e instanceof HttpError && e.code === "HardConflictError") {
      note.value = "";
      confirmSheet.value = {
        title: "硬冲突：无法自动合并",
        body: String(e.detail || e.message) + "\n\n它和另一条待审核提议/当前定稿冲突，需要人工判定。填一句判定记录后强制放行：",
        danger: true,
        onOk: async () => {
          await api.adoptProposal(tripId, p.id, { force: true, resolution_note: note.value || "人工判定放行" });
          toast("已人工判定并采纳");
          await load();
        },
      };
    } else {
      toast((e as Error).message, "err");
    }
  } finally {
    acting.value = false;
  }
}

async function reject(p: Proposal) {
  note.value = "";
  confirmSheet.value = {
    title: "拒绝这条提议？",
    body: "拒绝后不会改动定稿，记录保留在历史里。",
    danger: false,
    onOk: async () => {
      await api.rejectProposal(tripId, p.id, note.value || "未填写理由");
      toast("已拒绝");
      await load();
    },
  };
}

async function revoke(p: Proposal) {
  confirmSheet.value = {
    title: "撤销临时备选？",
    body: `「${p.title}」将恢复为采纳前的定稿状态（v${p.adopted_version ?? "?"} 之前），历史保留。`,
    danger: true,
    onOk: async () => {
      await api.revokeProposal(tripId, p.id);
      toast("已撤销，恢复原计划");
      await load();
    },
  };
}

async function formalize(p: Proposal) {
  await api.formalizeProposal(tripId, p.id);
  toast("已正式化（转为普通已采纳）");
  await load();
}

async function doConfirm() {
  if (!confirmSheet.value || acting.value) return;
  acting.value = true;
  try {
    await confirmSheet.value.onOk();
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    acting.value = false;
    confirmSheet.value = null;
  }
}

onMounted(load);
</script>

<template>
  <header class="topbar">
    <button class="back" @click="$router.back()">‹</button>
    <div class="tb-title">
      <div class="tb-name">提议中心</div>
      <div class="tb-meta">提议 ≠ 直接改定稿</div>
    </div>
  </header>

  <main class="view">
    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'pending' }" @click="tab = 'pending'">待审核</button>
      <button class="tab" :class="{ active: tab === 'adopted' }" @click="tab = 'adopted'">已采纳</button>
      <button class="tab" :class="{ active: tab === 'closed' }" @click="tab = 'closed'">已拒绝/撤销</button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>

    <template v-else>
      <div v-for="p in visible()" :key="p.id" class="card">
        <div class="p-title">
          {{ p.title }}
          <span class="pill pill-pending" v-if="p.status === 'pending'">待审核</span>
          <span class="pill pill-adopted" v-if="p.status === 'adopted' && !p.emergency">已采纳</span>
          <span class="pill pill-emergency" v-if="p.status === 'adopted' && p.emergency">临时备选</span>
          <span class="pill pill-rejected" v-if="p.status === 'rejected'">已拒绝</span>
          <span class="pill pill-revoked" v-if="p.status === 'revoked'">已撤销</span>
        </div>
        <div class="p-reason" v-if="p.reason">{{ p.reason }} · {{ p.created_by }}</div>

        <div v-for="ev in p.events" :key="ev.item_id + ev.kind" class="event-line">
          {{ kindLabel[ev.kind] }}：{{ itemLabel(ev.item_id) }}
          <template v-if="ev.kind === 'updated' && ev.payload && (ev.payload as any).title">
            → {{ (ev.payload as any).title }}
          </template>
        </div>

        <div v-if="p.status === 'pending' || p.status === 'draft'" class="precheck">
          <div class="precheck-title">采纳前预检 · 预测此刻采纳的后果</div>
          <div v-if="p.hard_conflicts.length" class="danger-box">
            ⛔ {{ p.hard_conflicts.join("；") }}<br />
            采纳会被拦下，需填人工判定记录后强制放行。
          </div>
          <div v-if="p.warnings.length" class="warn-box">
            ⚠️ {{ p.warnings.join("；") }}<br />
            采纳时会要求二次确认。
          </div>
          <div v-if="!p.hard_conflicts.length && !p.warnings.length" class="ok-box">
            ✔️ 预检通过：与当前定稿及其它待审核提议均无冲突，可直接采纳。
          </div>
        </div>
        <template v-else>
          <div v-if="p.warnings.length" class="warn-box">⚠️ 采纳时记录：{{ p.warnings.join("；") }}</div>
          <div v-if="p.hard_conflicts.length" class="danger-box">
            ⛔ 采纳时记录：{{ p.hard_conflicts.join("；") }}
          </div>
        </template>

        <div class="btn-row" v-if="p.status === 'pending'">
          <button class="btn btn-primary" :disabled="acting" @click="adopt(p)">采纳</button>
          <button class="btn btn-ghost" :disabled="acting" @click="reject(p)">拒绝</button>
        </div>
        <div class="btn-row" v-if="p.status === 'adopted' && p.emergency">
          <button class="btn btn-primary" :disabled="acting" @click="formalize(p)">正式化</button>
          <button class="btn btn-danger" :disabled="acting" @click="revoke(p)">撤销</button>
        </div>
      </div>
      <div v-if="!visible().length" class="empty">这个标签下还没有提议</div>
    </template>
  </main>

  <div v-if="confirmSheet" class="mask" @click.self="confirmSheet = null">
    <div class="sheet">
      <h3>{{ confirmSheet.title }}</h3>
      <div class="sub">{{ confirmSheet.body }}</div>
      <div v-if="confirmSheet.danger">
        <input v-model="note" placeholder="判定记录（可选）" />
      </div>
      <div v-else>
        <input v-model="note" placeholder="理由（可选）" />
      </div>
      <div class="btn-row">
        <button class="btn btn-ghost" :disabled="acting" @click="confirmSheet = null">取消</button>
        <button
          class="btn"
          :class="confirmSheet.danger ? 'btn-danger' : 'btn-primary'"
          :disabled="acting"
          @click="doConfirm"
        >
          {{ acting ? "处理中…" : "确认" }}
        </button>
      </div>
    </div>
  </div>
</template>
