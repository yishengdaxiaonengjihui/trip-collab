"""事件溯源的事件模型：不可变操作事件。

- ChangeEvent: 提议内的修改事件（增/改/删一条行程条目），未采纳前不进入定稿。
- StreamEvent: 已进入定稿事件流的事件（带序号、提议来源、采纳时间、元信息），append-only。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EVENT_CREATED = "created"
EVENT_UPDATED = "updated"
EVENT_DELETED = "deleted"

EVENT_KINDS = (EVENT_CREATED, EVENT_UPDATED, EVENT_DELETED)


@dataclass(frozen=True)
class ChangeEvent:
    """提议内的单条修改。payload 语义随 kind：

    - created: 完整条目字段 dict（Item 的可序列化形式）
    - updated: 变更字段 dict（字段名 -> 新值）
    - deleted: None
    """

    kind: str
    item_id: str
    payload: Any = None


@dataclass(frozen=True)
class StreamEvent:
    """定稿事件流中的一条已生效事件（不可变）。"""

    seq: int
    kind: str
    item_id: str
    payload: Any
    proposal_id: str
    adopted_at: int
    meta: dict = field(default_factory=dict)
