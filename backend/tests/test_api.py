"""API 层测试：行程/提议/采纳/冲突/回滚/临时备选/成员/插件，覆盖错误映射。

注意：沙箱环境禁止 python 创建/删除目录，测试不依赖 pytest tmp_path；
db 文件写入预先创建的固定目录（backend/tests/.testdbs，已 gitignore）。
版本语义：新行程 = v0（空事件流）；每次采纳/回滚推进版本。
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app

from conftest import make_item

_DB_DIR = os.path.join(os.path.dirname(__file__), ".testdbs")


def _db_path(tag: str) -> str:
    os.makedirs(_DB_DIR, exist_ok=True)
    return os.path.join(_DB_DIR, f"{tag}-{uuid.uuid4().hex}.db")


@pytest.fixture
def client():
    settings = Settings(db_path=_db_path("api"))
    app = create_app(settings)
    with TestClient(app) as c:
        c.headers["X-User-Id"] = "u_alice"
        yield c


def new_trip(client, name="西安 3 日游") -> dict:
    resp = client.post("/api/trips", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


def base_trip(client) -> dict:
    """建基线行程：D1 车次 + D2 酒店（D2 显式依赖 D1）-> 版本 v2。"""
    trip = new_trip(client)
    pid = create_pending(
        client,
        trip["id"],
        title="初始定稿",
        reason="基线行程",
        events=[
            {"kind": "created", "item_id": "d1_train", "payload": make_item("d1_train", 1, 1, "D1 高铁 G1001")},
            {"kind": "created", "item_id": "d2_hotel", "payload": make_item("d2_hotel", 1, 2, "D2 全季酒店", refs=["d1_train"])},
        ],
    )
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={"confirmed": True})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/trips/{trip['id']}").json()["version"] == 2
    return trip


def create_pending(client, trip_id, title="换酒店", events=None, reason="原酒店评价差"):
    if events is None:
        events = [
            {"kind": "updated", "item_id": "d1_train", "payload": {"title": "D1 高铁 G8888"}},
        ]
    resp = client.post(
        f"/api/trips/{trip_id}/proposals",
        json={"title": title, "reason": reason, "events": events},
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    r = client.post(f"/api/trips/{trip_id}/proposals/{pid}/submit")
    assert r.status_code == 200, r.text
    return pid


def all_item_titles(client, trip_id) -> set:
    trip = client.get(f"/api/trips/{trip_id}").json()
    return {i["id"]: i["title"] for day in trip["days"].values() for i in day}


# ---------------- 行程 ----------------

def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_and_get_trip(client):
    trip = new_trip(client)
    assert trip["version"] == 0
    assert trip["days"] == {}
    assert trip["pending_count"] == 0
    assert trip["members"] == [{"user_id": "u_alice", "role": "owner"}]

    resp = client.get(f"/api/trips/{trip['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "西安 3 日游"

    listed = client.get("/api/trips").json()
    assert len(listed) == 1
    assert listed[0]["id"] == trip["id"]


def test_get_missing_trip_404(client):
    resp = client.get("/api/trips/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TripNotFoundError"


# ---------------- 提议全流程 ----------------

def test_create_submit_adopt_flow(client):
    trip = base_trip(client)
    # 改 D2 酒店：无依赖引用它、单事件 -> 无需确认
    pid = create_pending(client, trip["id"], title="换酒店", events=[
        {"kind": "updated", "item_id": "d2_hotel", "payload": {"title": "D2 亚朵酒店"}},
    ])

    # 采纳（单事件无告警，无需确认）
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "adopted"

    # 定稿已更新（v2 -> v3）
    trip2 = client.get(f"/api/trips/{trip['id']}").json()
    assert trip2["version"] == 3
    assert trip2["days"]["1"][1]["title"] == "D2 亚朵酒店"


def test_multi_event_requires_confirmed(client):
    trip = base_trip(client)
    events = [
        {"kind": "updated", "item_id": "d1_train", "payload": {"title": "D1 高铁 G1001 改签"}},
        {"kind": "created", "item_id": "d3_m", "payload": make_item("d3_m", 3, 1, "博物馆")},
    ]
    pid = create_pending(client, trip["id"], title="改车次并加景点", events=events)

    # 未确认 -> 422
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "ConfirmationRequiredError"

    # 确认 -> 成功（v2 -> v4）
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={"confirmed": True})
    assert r.status_code == 200
    assert r.json()["status"] == "adopted"
    assert client.get(f"/api/trips/{trip['id']}").json()["version"] == 4


def test_dependency_warning_needs_confirmed(client):
    trip = base_trip(client)
    # 改车次 -> 依赖告警（D2 酒店 refs D1 车次）-> 必须确认
    pid = create_pending(client, trip["id"], title="改车次", events=[
        {"kind": "updated", "item_id": "d1_train", "payload": {"title": "D1 高铁 G1001 改签"}},
    ])
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={})
    assert r.status_code == 422
    warn_body = r.json()["detail"]
    assert "依赖" in warn_body["message"] or "引用" in warn_body["message"]

    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={"confirmed": True})
    assert r.status_code == 200
    assert all_item_titles(client, trip["id"])["d1_train"] == "D1 高铁 G1001 改签"


def test_hard_conflict_requires_force(client):
    trip = base_trip(client)
    # 两条待审核提议同时改同一条目（d2_hotel：无依赖告警干扰）
    pid1 = create_pending(client, trip["id"], title="改成A", events=[
        {"kind": "updated", "item_id": "d2_hotel", "payload": {"title": "酒店A"}},
    ])
    pid2 = create_pending(client, trip["id"], title="改成B", events=[
        {"kind": "updated", "item_id": "d2_hotel", "payload": {"title": "酒店B"}},
    ])
    # pid1 采纳时 pid2 仍在待审核 -> 并发硬冲突
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid1}/adopt", json={})
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "HardConflictError"

    # force + 记录人工判定 -> 放行
    r = client.post(
        f"/api/trips/{trip['id']}/proposals/{pid1}/adopt",
        json={"force": True, "resolution_note": "全员讨论后决定选A"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["resolution_note"] == "全员讨论后决定选A"

    # pid2 再采纳：并发冲突已消失，单事件无告警 -> 直接过
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid2}/adopt", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "adopted"


def test_reject_keeps_record(client):
    trip = base_trip(client)
    pid = create_pending(client, trip["id"])
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/reject", json={"reason": "预算超了"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "rejected"
    assert body["reject_reason"] == "预算超了"
    # 定稿未被污染（仍 v2）
    assert client.get(f"/api/trips/{trip['id']}").json()["version"] == 2
    # 历史里仍可见
    listed = client.get(f"/api/trips/{trip['id']}/proposals").json()
    assert any(p["id"] == pid and p["status"] == "rejected" for p in listed)


def test_invalid_status_409(client):
    trip = base_trip(client)
    pid = create_pending(client, trip["id"])
    # 已提交的不能再提交
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/submit")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "InvalidStatusError"


# ---------------- 临时备选 ----------------

def test_emergency_flow(client):
    trip = base_trip(client)
    resp = client.post(
        f"/api/trips/{trip['id']}/proposals",
        json={
            "title": "兵马俑临时闭园",
            "reason": "景区公告",
            "emergency": True,
            "events": [
                {"kind": "created", "item_id": "d2_m", "payload": make_item("d2_m", 2, 1, "西安城墙")},
            ],
        },
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    # 提交即采纳（v2 -> v3）
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/emergency")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "adopted" and body["emergency"] is True
    trip2 = client.get(f"/api/trips/{trip['id']}").json()
    assert trip2["version"] == 3
    assert "d2_m" in {i["id"] for day in trip2["days"].values() for i in day}

    # 撤销 -> 恢复（v3 -> v4）
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/revoke")
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"
    trip3 = client.get(f"/api/trips/{trip['id']}").json()
    assert trip3["version"] == 4
    assert "d2_m" not in {i["id"] for day in trip3["days"].values() for i in day}


def test_emergency_formalize(client):
    trip = base_trip(client)
    resp = client.post(
        f"/api/trips/{trip['id']}/proposals",
        json={
            "title": "临时加餐",
            "emergency": True,
            "events": [{"kind": "created", "item_id": "d1_x", "payload": make_item("d1_x", 1, 9, "夜宵")}],
        },
    )
    pid = resp.json()["id"]
    client.post(f"/api/trips/{trip['id']}/proposals/{pid}/emergency")
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/formalize")
    assert r.status_code == 200
    assert r.json()["emergency"] is False


# ---------------- 回滚 ----------------

def test_rollback_restores_state(client):
    trip = base_trip(client)
    pid = create_pending(client, trip["id"], title="换车次", events=[
        {"kind": "updated", "item_id": "d1_train", "payload": {"title": "D1 高铁 G1001 改签"}},
    ])
    # 改 d1_train 触发依赖告警 -> 需确认
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={"confirmed": True})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/trips/{trip['id']}").json()["version"] == 3

    # 回滚到 v2（基线）
    r = client.post(f"/api/trips/{trip['id']}/rollback", json={"version": 2, "reason": "车次不合适"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_version"] == 2
    assert body["new_version"] == 4
    assert body["affected_proposals"] == [pid]

    trip2 = client.get(f"/api/trips/{trip['id']}").json()
    assert trip2["version"] == 4
    assert trip2["days"]["1"][0]["title"] == "D1 高铁 G1001"

    # 版本历史保留且标注 rollback
    versions = client.get(f"/api/trips/{trip['id']}/versions").json()
    kinds = [v["kind"] for v in versions]
    assert kinds == ["adopt", "adopt", "adopt", "rollback"]
    assert versions[3]["title"] is None


def test_rollback_missing_version_404(client):
    trip = base_trip(client)
    r = client.post(f"/api/trips/{trip['id']}/rollback", json={"version": 99})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "SnapshotNotFoundError"


# ---------------- 版本 / 通知 / 成员 / 插件 ----------------

def test_versions_and_notifications(client):
    trip = base_trip(client)
    pid = create_pending(client, trip["id"], title="改车次")
    r = client.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={"confirmed": True})
    assert r.status_code == 200, r.text

    versions = client.get(f"/api/trips/{trip['id']}/versions").json()
    assert [v["version"] for v in versions] == [1, 2, 3]
    assert versions[0]["kind"] == "adopt"
    assert versions[0]["title"] == "初始定稿"
    assert versions[2]["title"] == "改车次"

    notifs = client.get(f"/api/trips/{trip['id']}/notifications").json()
    kinds = [n["kind"] for n in notifs]
    assert "proposal_created" in kinds
    assert "proposal_submitted" in kinds
    assert "proposal_adopted" in kinds


def test_members_crud(client):
    trip = new_trip(client)
    r = client.post(f"/api/trips/{trip['id']}/members", json={"user_id": "u_bob", "role": "editor"})
    assert r.status_code == 201
    members = client.get(f"/api/trips/{trip['id']}/members").json()
    assert {"user_id": "u_bob", "role": "editor"} in members

    r = client.put(f"/api/trips/{trip['id']}/members/u_bob", json={"role": "member"})
    assert r.status_code == 200
    assert r.json()["role"] == "member"


def test_plugins_registry(client):
    data = client.get("/api/plugins").json()
    keys = {p["key"] for p in data["plugins"]}
    assert keys == {"weather", "poi"}
    for p in data["plugins"]:
        assert p["enabled"] is True
        assert p["degraded"] is True


# ---------------- 持久化：重启后状态保留 ----------------

def test_state_persists_across_app_reload():
    db_path = _db_path("persist")
    app1 = create_app(Settings(db_path=db_path))
    with TestClient(app1) as c:
        c.headers["X-User-Id"] = "u_alice"
        trip = base_trip(c)
        pid = create_pending(c, trip["id"], title="改车次")
        r = c.post(f"/api/trips/{trip['id']}/proposals/{pid}/adopt", json={"confirmed": True})
        assert r.status_code == 200, r.text
        assert c.get(f"/api/trips/{trip['id']}").json()["version"] == 3

    # 模拟重启：新 app 实例，同一 db
    app2 = create_app(Settings(db_path=db_path))
    with TestClient(app2) as c:
        trip2 = c.get(f"/api/trips/{trip['id']}").json()
        assert trip2["version"] == 3
        assert trip2["days"]["1"][0]["title"] == "D1 高铁 G8888"
        proposals = c.get(f"/api/trips/{trip['id']}/proposals").json()
        assert proposals[0]["status"] == "adopted"
