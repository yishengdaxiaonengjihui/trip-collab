"""联调/演示数据播种：建行程 + 3 天定稿（带时间与类型标签）+ 一条带依赖告警的待审核提议。

幂等说明：每次运行会新建一个行程（不清理旧数据）。
"""

import httpx

BASE = "http://127.0.0.1:8000"
H = {"X-User-Id": "u_demo"}


def item(item_id, day, pos, title, time, tag, note="", refs=None):
    return {
        "kind": "created",
        "item_id": item_id,
        "payload": {
            "id": item_id,
            "day": day,
            "position": pos,
            "title": title,
            "time": time,
            "tag": tag,
            "note": note,
            "refs": refs or [],
            "amount": None,
        },
    }


ITEMS = [
    # 第 1 天
    item("d1_train", 1, 1, "抵达西安 · 高铁 G1001", "09:30", "交通", "西安北站"),
    item("d1_yan", 1, 2, "大雁塔", "11:00", "景区", "提前公众号预约"),
    item("d1_lunch", 1, 3, "老孙家羊肉泡馍", "12:30", "饭店", "回民街总店"),
    item("d1_night", 1, 4, "大唐不夜城", "19:00", "景区", "夜景灯光"),
    item("d1_hotel", 1, 5, "全季酒店（大雁塔店）", "21:30", "酒店"),
    # 第 2 天
    item("d2_terra", 2, 1, "秦始皇兵马俑", "09:00", "景区", "需提前订票", refs=["d1_train"]),
    item("d2_lunch", 2, 2, "临潼大盘鸡", "12:30", "饭店"),
    item("d2_hua", 2, 3, "华清池", "14:30", "景区", "长恨歌表演可选"),
    item("d2_hotel", 2, 4, "全季酒店（大雁塔店）", "20:30", "酒店"),
    # 第 3 天
    item("d3_museum", 3, 1, "陕西历史博物馆", "09:00", "景区", "需提前抢票"),
    item("d3_lunch", 3, 2, "长安大排档", "12:00", "饭店"),
    item("d3_train", 3, 3, "返程 · 高铁 G6666", "15:30", "交通", "西安北站"),
]

trip = httpx.post(BASE + "/api/trips", json={"name": "西安 3 日游 · 完整演示"}, headers=H).json()
tid = trip["id"]
print("trip:", tid, "v", trip["version"])

p = httpx.post(
    f"{BASE}/api/trips/{tid}/proposals",
    json={"title": "初始定稿", "reason": "基线行程", "events": ITEMS},
    headers=H,
).json()
httpx.post(f"{BASE}/api/trips/{tid}/proposals/{p['id']}/submit", headers=H)
r = httpx.post(f"{BASE}/api/trips/{tid}/proposals/{p['id']}/adopt", json={"confirmed": True}, headers=H)
print("adopt base:", r.status_code)

# 待审核提议：改 D1 高铁（兵马俑依赖它 -> 采纳时会要求人工确认）
p2 = httpx.post(
    f"{BASE}/api/trips/{tid}/proposals",
    json={
        "title": "D1 改乘中午的高铁",
        "reason": "早上起不来，想晚点出发",
        "events": [
            {
                "kind": "updated",
                "item_id": "d1_train",
                "payload": {"title": "抵达西安 · 高铁 G1003", "time": "12:40"},
            }
        ],
    },
    headers=H,
).json()
httpx.post(f"{BASE}/api/trips/{tid}/proposals/{p2['id']}/submit", headers=H)
print("pending proposal:", p2["id"])

t = httpx.get(f"{BASE}/api/trips/{tid}").json()
print("final version:", t["version"], "days:", list(t["days"].keys()), "条目:", sum(len(v) for v in t["days"].values()))

with open(r"D:\dsh\tour\trip-collab\frontend\.trip_id.txt", "w") as f:
    f.write(tid)
print("trip_id written:", tid)
