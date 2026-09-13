<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api } from "@/api";
import { toast } from "@/store";
import type { ChangeEventIn, Item } from "@/types";

const route = useRoute();
const router = useRouter();
const tripId = route.params.id as string;

const items = ref<Item[]>([]);
const title = ref("");
const reason = ref("");
const submitting = ref(false);

interface EventRow {
  kind: "updated" | "created" | "deleted";
  item_id: string;
  title?: string;
  day?: number;
  position?: number;
  note?: string;
  refs?: string;
}

const rows = reactive<EventRow[]>([{ kind: "updated", item_id: "" }]);

onMounted(async () => {
  try {
    const trip = await api.getTrip(tripId);
    items.value = Object.values(trip.days).flat();
  } catch (e) {
    toast((e as Error).message, "err");
  }
});

function addRow() {
  rows.push({ kind: "updated", item_id: "" });
}

function removeRow(i: number) {
  rows.splice(i, 1);
}

function toEvents(): ChangeEventIn[] {
  const events: ChangeEventIn[] = [];
  for (const r of rows) {
    if (r.kind === "deleted") {
      if (r.item_id) events.push({ kind: "deleted", item_id: r.item_id });
    } else if (r.kind === "created") {
      if (r.title?.trim()) {
        events.push({
          kind: "created",
          item_id: `new_${Date.now()}_${events.length}`,
          payload: {
            id: `new_${Date.now()}_${events.length}`,
            day: r.day || 1,
            position: r.position ?? 0,
            title: r.title.trim(),
            note: r.note || "",
            refs: (r.refs || "").split(/[，,]/).map((s) => s.trim()).filter(Boolean),
            amount: null,
          },
        });
      }
    } else {
      const payload: Record<string, unknown> = {};
      if (r.title !== undefined && r.title !== "") payload.title = r.title;
      if (r.note !== undefined && r.note !== "") payload.note = r.note;
      if (Object.keys(payload).length && r.item_id) events.push({ kind: "updated", item_id: r.item_id, payload });
    }
  }
  return events;
}

async function submit() {
  const events = toEvents();
  if (!title.value.trim() || !events.length) {
    toast("请填写标题和至少一条有效修改", "err");
    return;
  }
  submitting.value = true;
  try {
    const p = await api.createProposal(tripId, {
      title: title.value.trim(),
      reason: reason.value.trim(),
      events,
    });
    await api.submitProposal(tripId, p.id);
    toast("提议已提交，等待审核");
    router.push(`/trips/${tripId}/proposals`);
  } catch (e) {
    toast((e as Error).message, "err");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <header class="topbar">
    <button class="back" @click="$router.back()">‹</button>
    <div class="tb-title">
      <div class="tb-name">提交修改提议</div>
      <div class="tb-meta">审核通过前不影响定稿</div>
    </div>
  </header>

  <main class="view">
    <div class="card form">
      <label>提议标题</label>
      <input v-model="title" placeholder="如：D2 上午改去博物馆" />

      <label>理由（大家讨论时看）</label>
      <textarea v-model="reason" placeholder="为什么这么改？"></textarea>

      <label>修改内容（可多条）</label>
      <div v-for="(r, i) in rows" :key="i" class="event-row">
        <div class="row-top">
          <select v-model="r.kind">
            <option value="updated">修改现有</option>
            <option value="created">新增条目</option>
            <option value="deleted">删除条目</option>
          </select>
          <button class="del-btn" @click="removeRow(i)">删除</button>
        </div>

        <template v-if="r.kind === 'updated'">
          <select v-model="r.item_id">
            <option value="" disabled>选择要修改的条目…</option>
            <option v-for="it in items" :key="it.id" :value="it.id">{{ it.title }}</option>
          </select>
          <input v-model="r.title" placeholder="新标题（留空则不改）" />
        </template>

        <template v-else-if="r.kind === 'created'">
          <input v-model="r.title" placeholder="新条目标题，如：陕西历史博物馆" />
          <input v-model="r.note" placeholder="备注/时间，如：14:00" />
          <input v-model.number="r.day" type="number" min="1" placeholder="第几天" />
        </template>

        <template v-else>
          <select v-model="r.item_id">
            <option value="" disabled>选择要删除的条目…</option>
            <option v-for="it in items" :key="it.id" :value="it.id">{{ it.title }}</option>
          </select>
        </template>
      </div>

      <button class="btn btn-ghost" style="width: 100%; margin-top: 8px" @click="addRow">＋ 再加一条修改</button>

      <div class="btn-row">
        <button class="btn btn-primary" :disabled="submitting" @click="submit">
          {{ submitting ? "提交中…" : "提交提议" }}
        </button>
      </div>
      <div class="sub" style="margin-top: 8px">💡 依赖提示：若你修改的条目被其它条目引用，采纳时会要求确认。</div>
    </div>
  </main>
</template>
