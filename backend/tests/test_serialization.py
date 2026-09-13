"""引擎序列化往返测试：to_dict -> from_dict 必须还原等价状态。"""

from backend.engine.engine import STATUS_ADOPTED, STATUS_DRAFT, STATUS_PENDING, TripEngine
from backend.engine.events import EVENT_CREATED, EVENT_DELETED, EVENT_UPDATED, ChangeEvent

from conftest import adopt_base, make_item


def build_busy_engine() -> TripEngine:
    """构造一个状态丰富的引擎：已采纳提议、待审核、草稿、临时备选、撤销。"""
    engine = TripEngine(trip_id="ser-trip")
    adopt_base(engine)

    # 待审核提议（多改动）
    p2 = engine.create_proposal(
        "D2 调整",
        "换酒店并加景点",
        [
            ChangeEvent(EVENT_UPDATED, "d2_hotel", {"title": "亚朵酒店"}),
            ChangeEvent(EVENT_CREATED, "d2_museum", make_item("d2_museum", 2, 3, "陕西历史博物馆")),
        ],
        created_by="u2",
    )
    engine.submit(p2.id, "u2")

    # 草稿提议（未提交）
    engine.create_proposal(
        "草稿中的想法",
        "还没想好",
        [ChangeEvent(EVENT_UPDATED, "d1_train", {"time": "07:00"})],
        created_by="u3",
    )

    # 临时备选：应用并撤销
    p3 = engine.create_proposal(
        "临时闭园改道",
        "兵马俑闭园",
        [ChangeEvent(EVENT_DELETED, "d2_hotel")],
        created_by="u4",
    )
    engine.submit_emergency(p3.id, "u4")
    emergency_id = p3.id

    # 撤销临时备选（恢复酒店）
    engine.revoke(emergency_id, "u5")

    return engine


def test_round_trip_full_state():
    engine = build_busy_engine()
    data = engine.to_dict()
    restored = TripEngine.from_dict(data)

    # 版本 / 状态等价
    assert restored.version == engine.version
    assert restored.trip_id == engine.trip_id
    assert {iid: (it.day, it.position, it.title) for iid, it in restored.state().items.items()} == {
        iid: (it.day, it.position, it.title) for iid, it in engine.state().items.items()
    }

    # 提议集合等价（数量、状态、紧急标记）
    assert set(restored.proposals) == set(engine.proposals)
    for pid, p in engine.proposals.items():
        rp = restored.proposals[pid]
        assert rp.status == p.status
        assert rp.emergency == p.emergency
        assert rp.title == p.title
        assert [e.item_id for e in rp.events] == [e.item_id for e in p.events]

    # 快照与事件流等价
    assert set(restored.snapshots) == set(engine.snapshots)
    for version in engine.snapshots:
        assert {
            iid: (it.title, it.day)
            for iid, it in restored.snapshots[version].items.items()
        } == {iid: (it.title, it.day) for iid, it in engine.snapshots[version].items.items()}
    assert [e.item_id for e in restored.stream] == [e.item_id for e in engine.stream]

    # 通知等价
    assert [(n.kind, n.actor) for n in restored.notifications] == [
        (n.kind, n.actor) for n in engine.notifications
    ]


def test_restored_engine_is_fully_functional():
    """反序列化后的引擎必须能继续正常运作（计数器、状态、持久化闭环）。"""
    engine = build_busy_engine()
    restored = TripEngine.from_dict(engine.to_dict())
    before_version = restored.version

    # 采纳一条新提议，验证实时状态与快照继续工作
    p = restored.create_proposal(
        "再采纳一条",
        "验证功能",
        [ChangeEvent(EVENT_UPDATED, "d1_train", {"title": "D1 高铁 G8888"})],
        created_by="u6",
    )
    restored.submit(p.id, "u6")
    restored.adopt(p.id, actor="u6", confirmed=True)

    assert restored.version == before_version + 1
    assert restored.state().items["d1_train"].title == "D1 高铁 G8888"

    # 再次序列化仍是完整闭环
    data2 = restored.to_dict()
    assert data2["stream"][-1]["item_id"] == "d1_train"
    assert TripEngine.from_dict(data2).version == restored.version


def test_empty_engine_round_trip():
    engine = TripEngine(trip_id="empty")
    restored = TripEngine.from_dict(engine.to_dict())
    assert restored.version == 0
    assert restored.state().items == {}
    # 空引擎重建后仍可正常创建提议
    p = restored.create_proposal(
        "第一条", "r", [ChangeEvent(EVENT_CREATED, "x", make_item("x", 1, 1, "X"))], "u1"
    )
    assert p.status == STATUS_DRAFT
