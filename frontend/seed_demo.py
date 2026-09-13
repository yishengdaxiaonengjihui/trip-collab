"""联调数据播种：建行程 + 基线提议采纳（幂等：重复运行会建多个行程）。"""
import httpx

BASE = "http://127.0.0.1:8000"
H = {"X-User-Id": "u_demo"}

trip = httpx.post(BASE + "/api/trips", json={"name": "西安 3 日游 · 联调"}, headers=H).json()
tid = trip["id"]
print("trip:", tid, "v", trip["version"])

events = [
    {"kind": "created", "item_id": "d1_train", "payload": {"id": "d1_train", "day": 1, "position": 1, "title": "抵达西安 · 高铁 G1001", "note": "09:30", "refs": [], "amount": None}},
    {"kind": "created", "item_id": "d2_terracotta", "payload": {"id": "d2_terracotta", "day": 2, "position": 1, "title": "秦始皇兵马俑", "note": "09:00", "refs": ["d1_train"], "amount": None}},
]
p = httpx.post(
    f"{BASE}/api/trips/{tid}/proposals",
    json={"title": "初始定稿", "reason": "基线行程", "events": events},
    headers=H,
).json()
print("proposal:", p["id"], p["status"])
httpx.post(f"{BASE}/api/trips/{tid}/proposals/{p['id']}/submit", headers=H)
r = httpx.post(f"{BASE}/api/trips/{tid}/proposals/{p['id']}/adopt", json={"confirmed": True}, headers=H)
print("adopt:", r.status_code, r.json().get("status"))

t = httpx.get(f"{BASE}/api/trips/{tid}").json()
print("final version:", t["version"], "days:", list(t["days"].keys()))

# 追加一条待审核提议（改车次 -> 触发依赖告警）
p2 = httpx.post(
    f"{BASE}/api/trips/{tid}/proposals",
    json={
        "title": "D1 改乘中午的高铁",
        "reason": "早上起不来",
        "events": [
            {"kind": "updated", "item_id": "d1_train", "payload": {"title": "抵达西安 · 高铁 G1003", "note": "12:40"}}
        ],
    },
    headers=H,
).json()
httpx.post(f"{BASE}/api/trips/{tid}/proposals/{p2['id']}/submit", headers=H)
print("pending proposal:", p2["id"], p2["status"])

with open(r"D:\dsh\tour\trip-collab\frontend\.trip_id.txt", "w") as f:
    f.write(tid)
print("trip_id written")
