"""定稿行程状态：事件回放的目标结构。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .events import EVENT_CREATED, EVENT_DELETED, EVENT_UPDATED


@dataclass
class Item:
    """行程条目：归属某天，带排序位、标题、显式依赖引用、预算预留字段。"""

    id: str
    day: int
    position: int
    title: str
    refs: list[str] = field(default_factory=list)  # 显式依赖：本条目依赖的其它条目 id
    amount: float | None = None  # MVP 仅预留字段，不做自动计算
    note: str = ""


def item_to_dict(item: Item) -> dict:
    return {
        "id": item.id,
        "day": item.day,
        "position": item.position,
        "title": item.title,
        "refs": list(item.refs),
        "amount": item.amount,
        "note": item.note,
    }


def dict_to_item(data: dict) -> Item:
    return Item(
        id=data["id"],
        day=data["day"],
        position=data["position"],
        title=data["title"],
        refs=list(data.get("refs") or []),
        amount=data.get("amount"),
        note=data.get("note") or "",
    )


@dataclass
class TripState:
    items: dict[str, Item] = field(default_factory=dict)

    def items_by_day(self) -> dict[int, list[Item]]:
        days: dict[int, list[Item]] = {}
        for item in sorted(self.items.values(), key=lambda it: (it.day, it.position, it.id)):
            days.setdefault(item.day, []).append(item)
        return days


def apply_event(state: TripState, event) -> None:
    """把一条事件应用到定稿状态（原地修改）。"""
    if event.kind == EVENT_CREATED:
        if event.item_id in state.items:
            raise ValueError(f"条目已存在: {event.item_id}")
        state.items[event.item_id] = dict_to_item(event.payload)
    elif event.kind == EVENT_UPDATED:
        item = state.items.get(event.item_id)
        if item is None:
            raise ValueError(f"条目不存在: {event.item_id}")
        for key, value in (event.payload or {}).items():
            setattr(item, key, value)
    elif event.kind == EVENT_DELETED:
        if event.item_id not in state.items:
            raise ValueError(f"条目不存在: {event.item_id}")
        del state.items[event.item_id]
    else:
        raise ValueError(f"未知事件类型: {event.kind}")
