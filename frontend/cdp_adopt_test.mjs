// 前端采纳交互 CDP 验证：点击"采纳" -> 依赖告警确认弹窗 -> 确认 -> 已采纳
const tripId = process.argv[2];
const ws = new WebSocket("ws://127.0.0.1:9222");
let id = 0;
const pending = new Map();

function send(method, params = {}, sessionId) {
  return new Promise((resolve, reject) => {
    const msgId = ++id;
    pending.set(msgId, { resolve, reject });
    ws.send(JSON.stringify({ id: msgId, sessionId, method, params }));
  });
}

ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  }
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = reject;
});

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
const s = (method, params = {}) => send(method, params, sessionId);

await s("Page.enable");
await s("Runtime.enable");
await s("Page.navigate", { url: `http://localhost:5173/trips/${tripId}/proposals` });
await sleep(5000);

const ev = async (expression) => {
  const r = await s("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails.exception || r.exceptionDetails));
  return r.result.value;
};

try {
  const card = await ev(`document.querySelector('.p-title') ? document.querySelector('.p-title').textContent.trim() : 'NO_CARD'`);
  console.log("CARD_TITLE:", card);

  const clicked = await ev(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '采纳');
    if (!b) return false; b.click(); return true;
  })()`);
  console.log("CLICK_ADOPT:", clicked);
  await sleep(900);

  const modalTitle = await ev(`document.querySelector('.sheet h3') ? document.querySelector('.sheet h3').textContent.trim() : 'NO_MODAL'`);
  console.log("MODAL_TITLE:", modalTitle);
  const modalBody = await ev(`document.querySelector('.sheet .sub') ? document.querySelector('.sheet .sub').textContent.slice(0, 100) : ''`);
  console.log("MODAL_BODY:", modalBody);

  const confirmed = await ev(`(() => {
    const b = [...document.querySelectorAll('.sheet button')].find(x => x.textContent.trim() === '确认');
    if (!b) return false; b.click(); return true;
  })()`);
  console.log("CLICK_CONFIRM:", confirmed);
  await sleep(1500);

  const status = await ev(`fetch('/api/trips/${tripId}/proposals').then(r => r.json()).then(l => (l.find(p => p.title.includes('改乘')) || {}).status || 'NOT_FOUND')`);
  console.log("AFTER_ADOPT_STATUS:", status);

  const pendingCount = await ev(`fetch('/api/trips/${tripId}').then(r => r.json()).then(t => t.pending_count)`);
  console.log("PENDING_COUNT:", pendingCount);
} catch (e) {
  console.error("TEST_ERR:", e.message);
}

ws.close();
process.exit(0);
