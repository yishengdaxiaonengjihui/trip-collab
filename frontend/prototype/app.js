/* ============================================================
 * 交互原型（UX 测试用）—— 模拟事件溯源引擎语义的前端 mock。
 * 纯前端内存状态，无后端。直接双击 index.html 即可在手机/电脑打开。
 * 术语全部面向普通用户：定稿行程 / 提议 / 采纳 / 拒绝 / 回滚 / 临时备选。
 * ============================================================ */

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
const clone = (o) => JSON.parse(JSON.stringify(o));
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const uid = () => "p" + Math.random().toString(36).slice(2, 8);

/* ---------------- 全局状态（模拟引擎） ---------------- */
let state = {
  version: 1,               // 定稿版本号 = 事件流长度（简化）
  items: {},                // 当前定稿 {id -> item}
  snapshots: {},            // version -> items 深拷贝（版本快照）
  history: [],              // [{version,label,type,time}]
  proposals: [],            // 提议列表
  notifications: [],
  unread: 0,
  myRole: "创建者·管理员",
};

/* ---------------- 引擎语义工具 ---------------- */
function applyEvents(events, items) {
  for (const e of events) {
    if (e.op === "update") {
      Object.assign(items[e.id], e.changes);
    } else if (e.op === "add") {
      items[e.id] = clone(e.item);
    } else if (e.op === "delete") {
      delete items[e.id];
    }
  }
}
function touchedIds(events) { return events.map(e => e.id); }
/* 依赖告警：被修改条目被其它定稿条目显式引用（refs） */
function warningsOf(proposal) {
  const touched = touchedIds(proposal.events);
  const warns = [];
  for (const it of Object.values(state.items)) {
    for (const t of touched) {
      if (it.refs.includes(t)) {
        warns.push(`「${it.title}」引用了被修改的「${titleById(t)}」，请人工核对衔接`);
      }
    }
  }
  return warns;
}
function titleById(id) { return state.items[id] ? state.items[id].title : "该安排"; }
/* 硬冲突：其它待审核提议同时修改同一条目 */
function hardConflictsOf(proposal) {
  const mine = new Set(touchedIds(proposal.events));
  const out = [];
  for (const p of state.proposals) {
    if (p.id === proposal.id || p.status !== "pending") continue;
    for (const id of touchedIds(p.events)) {
      if (mine.has(id)) out.push({ item: titleById(id), other: p.title });
    }
  }
  return out;
}
function pushVersion(label, type) {
  state.version += 1;
  state.snapshots[state.version] = clone(state.items);
  state.history.push({ version: state.version, label, type, time: nowStr() });
}
function notify(kind, text) {
  state.notifications.push({ kind, text, time: nowStr() });
  state.unread += 1;
  renderBadges();
}
function nowStr() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/* ---------------- 初始化 ---------------- */
function init() {
  state.items = {};
  for (const it of window.BASE_ITEMS) state.items[it.id] = clone(it);
  state.snapshots[1] = clone(state.items);
  state.history.push({ version: 1, label: "初始定稿", type: "init", time: "10-01 19:30" });

  // 采纳种子提议 p_baomo -> 版本 2
  const baomo = clone(window.SEED_PROPOSALS[0]);
  state.proposals.push(baomo);
  applyEvents(baomo.events, state.items);
  pushVersion(`采纳「${baomo.title}」`, "adopt");

  // 待审核种子提议
  state.proposals.push(clone(window.SEED_PROPOSALS[1]));
  state.proposals.push(clone(window.SEED_PROPOSALS[2]));

  state.notifications.push(
    { kind: "adopted", text: "小雨的提议「D1 晚餐改吃羊肉泡馍」已采纳，定稿已更新", time: "10-01 20:25" },
    { kind: "proposal", text: "老王提交了提议「D2 上午华清宫，下午兵马俑」", time: "10-01 21:02" },
    { kind: "proposal", text: "阿杰提交了提议「D1 改乘中午的高铁」", time: "10-01 21:40" },
    { kind: "comment", text: "小雨在「D1 改乘中午的高铁」下发表了评论", time: "10-01 21:45" },
  );
  state.unread = 0;

  $("#tripName").textContent = window.TRIP.name;
  $("#tripMeta").textContent = `${window.TRIP.members.length} 人 · 10/2–10/4 · 你 = ${state.myRole}`;
  render();
}

/* ---------------- 路由 ---------------- */
function route() { return (location.hash || "#/trip").replace(/^#\/?/, ""); }
window.addEventListener("hashchange", render);

function render() {
  renderBadges();
  setActiveNav(route());
  const view = $("#view");
  if (route() === "trip") renderTrip(view);
  else if (route() === "proposals") renderProposals(view);
  else if (route() === "new") renderNew(view);
  else if (route() === "history") renderHistory(view);
  else if (route() === "notify") { renderNotify(view); state.unread = 0; renderBadges(); }
}
function renderBadges() {
  const pending = state.proposals.filter(p => p.status === "pending").length;
  const pn = $("#navPendingBadge");
  pn.classList.toggle("hidden", pending === 0);
  if (pending) pn.textContent = pending;
  const bn = $("#bellBadge");
  bn.classList.toggle("hidden", state.unread === 0);
  if (state.unread) bn.textContent = state.unread > 9 ? "9+" : state.unread;
}
function setActiveNav(view) {
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  $("#fab").classList.toggle("hidden", view !== "trip");
}

/* ---------------- 视图：定稿行程 ---------------- */
function renderTrip(v) {
  v.innerHTML = "";
  const pending = state.proposals.filter(p => p.status === "pending");
  if (pending.length) {
    const b = el("div", "p-warn");
    b.textContent = `有 ${pending.length} 条提议待处理，尚未合并进定稿`;
    b.style.cursor = "pointer";
    b.onclick = () => (location.hash = "#/proposals");
    v.appendChild(b);
  }
  v.appendChild(el("div", "section-title", `📌 最终定稿行程 · 版本 v${state.version}`));

  for (const d of window.TRIP.days) {
    const card = el("div", "day-card");
    const head = el("div", "day-head");
    head.appendChild(el("span", "", `第 ${d.day} 天 · ${d.label}`));
    head.appendChild(el("span", "day-date", d.date));
    card.appendChild(head);

    const items = Object.values(state.items).filter(i => i.day === d.day)
      .sort((a, b) => a.time.localeCompare(b.time));
    for (const it of items) {
      card.appendChild(itemRow(it));
    }
    v.appendChild(card);
  }
  const tip = el("div", "empty");
  tip.innerHTML = `<div class="big">💡</div>改动行程不用直接改定稿：点下方「＋」提一条提议，或按「旅途应急」现场处理`;
  v.appendChild(tip);
}
function itemRow(it) {
  const row = el("div", "item");
  row.appendChild(el("div", "item-time", it.time));
  const body = el("div", "item-body");
  body.appendChild(el("div", "item-title", it.title));
  if (it.note) body.appendChild(el("div", "item-note", it.note));
  const tags = el("div", "item-tags");
  if (it.tag) tags.appendChild(el("span", "tag", it.tag));
  if (it.amount) tags.appendChild(el("span", "tag amount", `约 ¥${it.amount}`));
  if (it.emergency) tags.appendChild(el("span", "tag emergency", "临时备选"));
  body.appendChild(tags);
  row.appendChild(body);
  return row;
}

/* ---------------- 视图：提议中心 ---------------- */
function renderProposals(v) {
  v.innerHTML = "";
  const tabs = [["pending", "待审核"], ["adopted", "已生效"], ["rejected", "已拒绝/撤销"]];
  const bar = el("div", "section-title");
  for (const [key, label] of tabs) {
    const n = state.proposals.filter(p => p.status === key || (key === "rejected" && (p.status === "rejected" || p.status === "revoked"))).length;
    const t = el("button", "btn btn-ghost btn-sm", `${label} ${n}`);
    t.style.flex = "none"; t.style.padding = "6px 14px";
    t.onclick = () => filterProposals(v, key, label);
    bar.appendChild(t);
  }
  v.appendChild(bar);
  filterProposals(v, "pending", "待审核");
}
function filterProposals(v, statusKey, label) {
  v.querySelectorAll(".p-card").forEach(n => n.remove());
  v.querySelectorAll(".p-empty-note").forEach(n => n.remove());
  const list = state.proposals.filter(p =>
    statusKey === "pending" ? p.status === "pending" :
    statusKey === "adopted" ? p.status === "adopted" :
    (p.status === "rejected" || p.status === "revoked")
  );
  if (!list.length) {
    const e = el("div", "empty p-empty-note");
    e.innerHTML = `<div class="big">📭</div>这里空空如也`;
    v.appendChild(e);
    return;
  }
  for (const p of list) v.appendChild(proposalCard(p));
}
function proposalCard(p) {
  const card = el("div", "p-card");
  const head = el("div", "p-head");
  head.appendChild(el("div", "p-title", p.title));
  const badge = el("span", "p-badge " + (p.status === "pending" ? "pending" : p.emergency && p.status === "adopted" ? "emergency" : p.status));
  badge.textContent = p.status === "pending" ? "待审核" : p.emergency && p.status === "adopted" ? "临时备选" : p.status === "adopted" ? "已生效" : p.status === "rejected" ? "已拒绝" : "已撤销";
  head.appendChild(badge);
  card.appendChild(head);
  card.appendChild(el("div", "p-meta", `${p.author} 提出 · ${p.time}${p.emergency ? " · ⚡现场应急" : ""}`));
  card.appendChild(el("div", "p-reason", p.reason));

  // 变更明细
  const ch = el("div", "p-changes");
  for (const e of p.events) {
    const t = state.items[e.id] || { title: "(已删除)" };
    const line = e.op === "delete" ? `🗑 取消「${titleById(e.id)}」` :
      e.op === "add" ? `➕ 新增「${e.item.title}」` :
      `✏️ 修改「${titleById(e.id)}」：` + Object.entries(e.changes).map(([k, val]) => `${k === "time" ? "时间" : k === "title" ? "名称" : k === "note" ? "备注" : k}→${val}`).join("，");
    ch.appendChild(el("div", "p-change", line));
  }
  card.appendChild(ch);

  // 依赖告警
  const warns = warningsOf(p);
  if (warns.length && p.status !== "adopted") {
    card.appendChild(el("div", "p-warn", "⚠️ " + warns.join("；")));
  }
  // 硬冲突
  const hards = hardConflictsOf(p);
  if (hards.length && p.status === "pending") {
    card.appendChild(el("div", "p-warn", `🚫 与提议「${hards[0].other}」都在修改「${hards[0].item}」，需人工判断`));
  }

  // 评论
  if (p.comments.length || p.status === "pending") {
    const c = el("div", "comments");
    for (const cm of p.comments) {
      const row = el("div", "comment");
      row.appendChild(el("span", "who", cm.who));
      row.appendChild(document.createTextNode(cm.text));
      row.appendChild(el("span", "c-time", ` · ${cm.time}`));
      c.appendChild(row);
    }
    if (p.status === "pending") {
      const box = el("div", "comment-input");
      const inp = document.createElement("input");
      inp.placeholder = "发表意见…";
      const btn = el("button", "", "发送");
      btn.onclick = () => {
        if (!inp.value.trim()) return;
        p.comments.push({ who: "阿杰", text: inp.value.trim(), time: nowStr() });
        notify("comment", `你在「${p.title}」下发表了评论`);
        render();
      };
      box.appendChild(inp); box.appendChild(btn);
      c.appendChild(box);
    }
    card.appendChild(c);
  }

  // 操作按钮
  if (p.status === "pending") {
    const acts = el("div", "p-actions");
    const bRej = el("button", "btn btn-danger", "拒绝");
    bRej.onclick = () => rejectFlow(p);
    const bAd = el("button", "btn btn-primary", "采纳");
    bAd.onclick = () => adoptFlow(p);
    acts.appendChild(bRej); acts.appendChild(bAd);
    card.appendChild(acts);
  } else if (p.status === "adopted" && p.emergency) {
    const acts = el("div", "p-actions");
    const bF = el("button", "btn btn-ghost", "📌 正式化（转为正常安排）");
    bF.onclick = () => { p.emergency = false; notify("formalized", `临时备选「${p.title}」已正式化`); render(); };
    const bR = el("button", "btn btn-danger", "↩️ 撤销");
    bR.onclick = () => revokeFlow(p);
    acts.appendChild(bF); acts.appendChild(bR);
    card.appendChild(acts);
  }
  return card;
}

/* 采纳流程：依赖告警/多改动需确认；硬冲突需人工判定 */
function adoptFlow(p) {
  const warns = warningsOf(p);
  const hards = hardConflictsOf(p);
  const multi = p.events.length > 1;
  const body = [];
  if (hards.length) body.push(`🚫 另一条提议也在修改「${hards[0].item}」。你可以强制采纳，但需要人工判断哪个优先。`);
  if (warns.length) body.push("⚠️ " + warns.join("<br>⚠️ "));
  if (multi && !warns.length && !hards.length) body.push("这是一组包含多处的改动，请复核后确认合并。");
  if (!body.length) { doAdopt(p); return; }
  sheetConfirm("确认采纳这条提议？", body.join("<br><br>"), "确认合并", () => doAdopt(p));
}
function doAdopt(p) {
  applyEvents(p.events, state.items);
  p.status = "adopted";
  p.emergency = false;
  pushVersion(`采纳「${p.title}」`, "adopt");
  notify("adopted", `「${p.title}」已采纳，定稿已更新为 v${state.version}`);
  toast("✅ 已合并进定稿", "ok");
  render();
}
function rejectFlow(p) {
  sheetConfirm("拒绝这条提议？", "拒绝后变更不会进入定稿，但提议记录会保留。", "确认拒绝", () => {
    p.status = "rejected";
    notify("rejected", `「${p.title}」已被拒绝`);
    toast("已拒绝 · 记录保留", "warn");
    render();
  }, true);
}
function revokeFlow(p) {
  const baseVersion = p.baseVersion || (state.version - 1);
  sheetConfirm("撤销这条临时备选？", "定稿将回到它生效之前的状态，原始安排会恢复。", "确认撤销", () => {
    state.items = clone(state.snapshots[baseVersion]);
    p.status = "revoked";
    pushVersion(`撤销临时备选「${p.title}」`, "rollback");
    notify("revoked", `临时备选「${p.title}」已撤销，定稿恢复`);
    toast("↩️ 已撤销，恢复到之前版本", "warn");
    render();
  }, true);
}

/* ---------------- 视图：新建提议 ---------------- */
function renderNew(v) {
  v.innerHTML = "";
  v.appendChild(el("div", "section-title", "➕ 提交修改提议（不会直接改定稿）"));
  const f = el("div", "form");
  const opField = field("操作", `
    <select id="opType">
      <option value="update">修改现有安排</option>
      <option value="add">新增安排</option>
      <option value="delete">取消一项安排</option>
    </select>`);
  const targetField = field("选择安排", buildItemSelect());
  const addFields = el("div", "field"); addFields.className = "field hidden"; addFields.id = "addFields";
  addFields.innerHTML = `
    <label>新增内容</label>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <select id="addDay">${window.TRIP.days.map(d => `<option value="${d.day}">第${d.day}天</option>`).join("")}</select>
      <input id="addTime" placeholder="时间 如 15:00" style="width:90px">
    </div>
    <input id="addTitle" placeholder="名称，如：壶口瀑布一日游">
    <div class="hint" style="margin-top:6px">新增后同样要经审核才能进入定稿</div>`;
  const updateFields = el("div", "field"); updateFields.id = "updateFields";
  updateFields.innerHTML = `
    <label>修改内容（选填，留空表示不改）</label>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <input id="updTime" placeholder="新时间 如 10:30" style="width:110px">
      <input id="updTitle" placeholder="新名称">
    </div>
    <input id="updNote" placeholder="新备注">
    <div class="hint" id="depHint"></div>`;
  const reasonField = field("理由（给队友看的）", `<textarea id="reason" placeholder="为什么这样改？"></textarea>`);
  f.appendChild(opField); f.appendChild(targetField); f.appendChild(updateFields); f.appendChild(addFields);
  f.appendChild(reasonField);

  const hint = el("div", "hint");
  hint.style.marginBottom = "12px";
  hint.textContent = "💡 演示依赖检测：试试修改「抵达西安」，会提示它被兵马俑引用";
  f.appendChild(hint);

  const submit = el("button", "btn btn-primary", "提交提议，等待审核");
  submit.onclick = () => submitProposal();
  f.appendChild(submit);
  v.appendChild(f);

  const sel = $("#opType"), target = $("#itemTarget");
  const sync = () => {
    $("#updateFields").classList.toggle("hidden", sel.value !== "update");
    $("#addFields").classList.toggle("hidden", sel.value !== "add");
    target.parentElement.classList.toggle("hidden", sel.value === "add");
    if (sel.value === "update") refreshDepHint();
  };
  sel.onchange = sync;
  if (target) target.onchange = refreshDepHint;
  sync();
}
function refreshDepHint() {
  const target = $("#itemTarget");
  const h = $("#depHint");
  if (!target || !h) return;
  const id = target.value;
  const deps = Object.values(state.items).filter(i => i.refs.includes(id));
  h.textContent = deps.length ? `⚠️ 「${deps[0].title}」引用了它，采纳时需人工核对衔接` : "";
}
function submitProposal() {
  const op = $("#opType").value;
  const title = $("#reason").value.trim() ? "" : "";
  if (op === "update") {
    const id = $("#itemTarget").value;
    const changes = {};
    if ($("#updTime").value.trim()) changes.time = $("#updTime").value.trim();
    if ($("#updTitle").value.trim()) changes.title = $("#updTitle").value.trim();
    if ($("#updNote").value.trim()) changes.note = $("#updNote").value.trim();
    const reason = $("#reason").value.trim();
    if (!reason) return toast("请填写理由", "warn");
    if (!Object.keys(changes).length) return toast("请至少填一项修改内容", "warn");
    const p = {
      id: uid(), author: "阿杰", title: `修改「${titleById(id)}」`, reason,
      status: "pending", emergency: false, time: nowStr(),
      events: [{ op: "update", id, changes }], comments: [],
    };
    state.proposals.push(p);
  } else if (op === "add") {
    const reason = $("#reason").value.trim();
    if (!reason) return toast("请填写理由", "warn");
    const addTitle = $("#addTitle").value.trim();
    if (!addTitle) return toast("请填写名称", "warn");
    const id = uid();
    const item = { id, day: Number($("#addDay").value), time: $("#addTime").value.trim() || "09:00", title: addTitle, note: "", refs: [], amount: 0, tag: "景点" };
    const p = { id: uid(), author: "阿杰", title: `新增「${addTitle}」`, reason, status: "pending", emergency: false, time: nowStr(), events: [{ op: "add", id, item }], comments: [] };
    state.proposals.push(p);
  } else {
    const id = $("#itemTarget").value;
    const reason = $("#reason").value.trim();
    if (!reason) return toast("请填写理由", "warn");
    const p = { id: uid(), author: "阿杰", title: `取消「${titleById(id)}」`, reason, status: "pending", emergency: false, time: nowStr(), events: [{ op: "delete", id }], comments: [] };
    state.proposals.push(p);
  }
  notify("proposal", `你提交了提议「${state.proposals[state.proposals.length - 1].title}」`);
  toast("📋 提议已提交，等待管理员审核", "ok");
  location.hash = "#/proposals";
}

/* ---------------- 视图：版本历史 ---------------- */
function renderHistory(v) {
  v.innerHTML = "";
  v.appendChild(el("div", "section-title", "🕘 版本历史（点回滚可一键回到过去）"));
  for (const h of [...state.history].reverse()) {
    const card = el("div", "v-card" + (h.version === state.version ? " v-current" : ""));
    const left = el("div", "v-left");
    const label = el("div", "v-label", `v${h.version} · ${h.label}`);
    left.appendChild(label);
    const meta = el("div", "v-meta", `${h.time}${h.version === state.version ? " · 当前定稿" : ""}`);
    left.appendChild(meta);
    card.appendChild(left);
    if (h.version !== state.version) {
      const b = el("button", "btn btn-ghost btn-sm", "回滚");
      b.style.flex = "0 0 auto"; b.style.padding = "7px 16px";
      b.onclick = () => rollbackTo(h.version);
      card.appendChild(b);
    }
    v.appendChild(card);
  }
  v.appendChild(el("div", "empty", `<div class="big">🛟</div>回滚只会恢复定稿内容，所有提议记录和通知都会保留`));
}
function rollbackTo(version) {
  sheetConfirm(`回滚到 v${version}？`, "之后采纳的变更会被撤销（历史记录保留，相关队友会收到通知）。", "确认回滚", () => {
    state.items = clone(state.snapshots[version]);
    pushVersion(`回滚到 v${version}`, "rollback");
    notify("rollback", `定稿已回滚到 v${version}`);
    toast("🕘 已回滚", "warn");
    render();
  }, true);
}

/* ---------------- 视图：通知 ---------------- */
function renderNotify(v) {
  v.innerHTML = "";
  v.appendChild(el("div", "section-title", "🔔 通知"));
  if (!state.notifications.length) {
    v.appendChild(el("div", "empty", `<div class="big">🔕</div>暂无通知`));
    return;
  }
  const ico = { proposal: "📋", adopted: "✅", rejected: "❌", comment: "💬", emergency: "⚡", revoked: "↩️", formalized: "📌", rollback: "🕘" };
  for (const n of [...state.notifications].reverse()) {
    const c = el("div", "n-card");
    c.appendChild(el("span", "n-ico", ico[n.kind] || "🔔"));
    const body = el("div", "n-body");
    body.appendChild(el("div", "n-text", n.text));
    body.appendChild(el("div", "n-time", n.time));
    c.appendChild(body);
    v.appendChild(c);
  }
}

/* ---------------- 旅途应急（临时备选） ---------------- */
function openQuick() {
  const items = Object.values(state.items).sort((a, b) => a.day - b.day || a.time.localeCompare(b.time));
  let html = `<h3>⚡ 旅途应急</h3><div class="sub">现场出问题时：改完立刻生效、全员可见，事后可正式化或撤销</div>`;
  let lastDay = 0;
  for (const it of items) {
    if (it.day !== lastDay) { lastDay = it.day; html += `<div class="section-title">第 ${it.day} 天</div>`; }
    html += `<div class="quick-item">
      <div><div class="q-title">${esc(it.title)}</div><div class="q-time">${esc(it.time)}</div></div>
      <button onclick="quickAction('${it.id}','close')">出问题了</button>
      <button onclick="quickAction('${it.id}','time')">改时间</button>
    </div>`;
  }
  html += `<div style="margin-top:14px"><button class="btn btn-ghost" onclick="quickAddItem()">➕ 临时加一项</button></div>`;
  openSheet(html);
}
function quickAction(id, action) {
  const it = state.items[id];
  if (!it) return closeSheet();
  if (action === "close") {
    sheetConfirm(`「${it.title}」出问题了？`, "确认后立即生效（临时备选），全员可见；事后可撤销恢复原计划。", "立即生效", () => {
      const p = {
        id: uid(), author: "阿杰", title: `临时取消「${it.title}」`, reason: "现场应急：安排取消/替换",
        status: "adopted", emergency: true, time: nowStr(), baseVersion: state.version,
        events: [{ op: "delete", id }], comments: [],
      };
      state.proposals.push(p);
      applyEvents(p.events, state.items);
      pushVersion(`临时备选「${p.title}」`, "adopt");
      notify("emergency", `临时备选「${p.title}」已生效，全员可见`);
      toast("⚡ 已生效（临时备选）", "emergency");
      render();
    }, true);
  } else {
    sheetConfirm(`修改「${it.title}」的时间？`, "输入新时间后立即生效（临时备选），可事后正式化。", "立即生效", () => {
      openSheet(`<h3>改时间</h3><div class="field"><input id="qTime" placeholder="新时间 如 16:00" value="${esc(it.time)}"></div>
      <div class="btn-row"><button class="btn btn-ghost" onclick="closeSheet()">取消</button>
      <button class="btn btn-primary" onclick="quickApplyTime('${id}')">确定</button></div>`);
    });
  }
}
function quickApplyTime(id) {
  const t = $("#qTime").value.trim();
  if (!t) return;
  const it = state.items[id];
  const oldTime = it.time;
  const p = {
    id: uid(), author: "阿杰", title: `临时改「${it.title}」时间`, reason: "现场应急：时间调整",
    status: "adopted", emergency: true, time: nowStr(), baseVersion: state.version,
    events: [{ op: "update", id, changes: { time: t } }], comments: [],
  };
  state.proposals.push(p);
  applyEvents(p.events, state.items);
  pushVersion(`临时备选「${p.title}」`, "adopt");
  notify("emergency", `临时备选「${p.title}」已生效（${oldTime} → ${t}）`);
  closeSheet();
  toast("⚡ 已生效（临时备选）", "emergency");
  render();
}
function quickAddItem() {
  openSheet(`<h3>➕ 临时加一项</h3>
    <div class="field"><label>第几天</label><select id="qDay">${window.TRIP.days.map(d => `<option value="${d.day}">第${d.day}天</option>`).join("")}</select></div>
    <div class="field"><label>时间</label><input id="qTime" placeholder="如 15:00"></div>
    <div class="field"><label>名称</label><input id="qTitle" placeholder="如：回民街高家大院"></div>
    <div class="btn-row"><button class="btn btn-ghost" onclick="closeSheet()">取消</button>
    <button class="btn btn-primary" onclick="quickApplyAdd()">立即生效</button></div>`);
}
function quickApplyAdd() {
  const t = $("#qTime").value.trim() || "09:00";
  const title = $("#qTitle").value.trim();
  if (!title) return toast("请填写名称", "warn");
  const id = uid();
  const item = { id, day: Number($("#qDay").value), time: t, title, note: "临时新增", refs: [], amount: 0, tag: "景点", emergency: true };
  const p = {
    id: uid(), author: "阿杰", title: `临时新增「${title}」`, reason: "现场应急：临时新增",
    status: "adopted", emergency: true, time: nowStr(), baseVersion: state.version,
    events: [{ op: "add", id, item }], comments: [],
  };
  state.proposals.push(p);
  applyEvents(p.events, state.items);
  pushVersion(`临时备选「${p.title}」`, "adopt");
  notify("emergency", `临时备选「${p.title}」已生效`);
  closeSheet();
  toast("⚡ 已生效（临时备选）", "emergency");
  render();
}

/* ---------------- 通用 UI ---------------- */
function field(label, innerHtml) {
  const f = el("div", "field");
  f.appendChild(el("label", "", label));
  const wrap = document.createElement("div");
  wrap.innerHTML = innerHtml;
  f.appendChild(wrap);
  return f;
}
function buildItemSelect() {
  const opts = [];
  for (const d of window.TRIP.days) {
    const items = Object.values(state.items).filter(i => i.day === d.day).sort((a, b) => a.time.localeCompare(b.time));
    if (!items.length) continue;
    opts.push(`<optgroup label="第 ${d.day} 天">`);
    for (const it of items) opts.push(`<option value="${it.id}">${esc(it.time)} ${esc(it.title)}</option>`);
  }
  return `<select id="itemTarget">${opts.join("")}</select>`;
}
function openSheet(html) {
  $("#modalRoot").innerHTML = `<div class="mask"><div class="sheet">${html}</div></div>`;
  $("#modalRoot .mask").onclick = (e) => { if (e.target === e.currentTarget) closeSheet(); };
}
function closeSheet() { $("#modalRoot").innerHTML = ""; }
function sheetConfirm(title, body, okText, onOk, danger) {
  openSheet(`<h3>${esc(title)}</h3><div class="sub">${body}</div>
    <div class="btn-row">
      <button class="btn btn-ghost" onclick="closeSheet()">取消</button>
      <button class="btn ${danger ? "btn-danger" : "btn-primary"}" onclick="doConfirm()">${esc(okText)}</button>
    </div>`);
  window.doConfirm = () => { closeSheet(); onOk(); };
}
function toast(text, kind) {
  const t = el("div", "toast" + (kind ? " " + kind : ""), text);
  $("#toastRoot").appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

/* ---------------- 事件绑定 ---------------- */
/* 启动错误陷阱：任何初始化错误直接显示在页面上（原型调试用） */
window.addEventListener("error", (e) => {
  const v = document.getElementById("view");
  if (v) v.innerHTML = `<div class="empty" style="color:#dc2626">⚠️ 页面出错：${esc(e.message)}</div>`;
});
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-item").forEach(b => b.onclick = () => (location.hash = "#/" + b.dataset.view));
  $("#btnNotify").onclick = () => (location.hash = "#/notify");
  $("#fab").onclick = openQuick;
  window.quickAction = quickAction; window.quickApplyTime = quickApplyTime;
  window.quickAddItem = quickAddItem; window.quickApplyAdd = quickApplyAdd;
  try { init(); } catch (err) {
    const v = document.getElementById("view");
    if (v) v.innerHTML = `<div class="empty" style="color:#dc2626">⚠️ 启动失败：${esc(err.message)}<br><small>${esc(err.stack || "")}</small></div>`;
  }
});
