// 轻量响应式状态 + toast（骨架级，不引入 pinia）

import { reactive } from "vue";

import type { Trip } from "./types";

export const appState = reactive({
  currentTrip: null as Trip | null,
  user: localStorage.getItem("tc_user") || "u_demo",
});

export function toast(message: string, kind: "ok" | "err" = "ok") {
  const root = document.getElementById("toastRoot");
  if (!root) return;
  const el = document.createElement("div");
  el.className = `toast toast-${kind}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 250);
  }, 2600);
}
