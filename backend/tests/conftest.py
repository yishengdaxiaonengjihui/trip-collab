"""测试共享工具。"""

import pytest

from backend.engine.engine import TripEngine
from backend.engine.events import EVENT_CREATED, ChangeEvent


@pytest.fixture
def engine():
    return TripEngine(trip_id="test-trip")


def make_item(item_id: str, day: int, position: int, title: str, refs=None, amount=None, note="", time="", tag=""):
    """构造 created 事件 payload（id 必须与事件 item_id 一致）。"""
    return {
        "id": item_id,
        "day": day,
        "position": position,
        "title": title,
        "refs": list(refs or []),
        "amount": amount,
        "note": note,
        "time": time,
        "tag": tag,
    }


def adopt_base(engine, actor="admin"):
    """建立基线定稿：D1 车次 + D2 酒店（D2 显式依赖 D1）。"""
    p = engine.create_proposal(
        "初始定稿",
        "基线行程",
        [
            ChangeEvent(EVENT_CREATED, "d1_train", make_item("d1_train", 1, 1, "D1 高铁 G1001")),
            ChangeEvent(
                EVENT_CREATED, "d2_hotel", make_item("d2_hotel", 1, 2, "D2 全季酒店", refs=["d1_train"])
            ),
        ],
        created_by="u1",
    )
    engine.submit(p.id, "u1")
    engine.adopt(p.id, actor=actor, confirmed=True)
    return p
