"""冲突判定：发生在采纳动作执行时，基于当前已回放的定稿状态，而非提交时快照。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .events import EVENT_CREATED, EVENT_DELETED, EVENT_UPDATED


@dataclass
class ConflictReport:
    hard: list[str] = field(default_factory=list)  # 禁止自动合并，强制人工判定
    warnings: list[str] = field(default_factory=list)  # 软冲突/依赖告警，需人工复核确认

    @property
    def is_clean(self) -> bool:
        return not self.hard and not self.warnings


def detect_conflicts(events, state, pending_proposals) -> ConflictReport:
    """判定采纳冲突。

    events:            被采纳提议的修改事件列表
    state:             当前已回放的定稿状态（采纳时刻）
    pending_proposals: 其它处于待审核状态的提议（与本提议并发修改同一条目即硬冲突）
    """
    report = ConflictReport()
    touched = {e.item_id for e in events}

    # 1) 目标状态冲突：基于当前定稿，而非提交时快照
    for e in events:
        exists = e.item_id in state.items
        if e.kind == EVENT_CREATED and exists:
            report.hard.append(f"新增条目 {e.item_id} 在当前定稿中已存在")
        elif e.kind in (EVENT_UPDATED, EVENT_DELETED) and not exists:
            report.hard.append(f"条目 {e.item_id} 在当前定稿中不存在或已被删除")

    # 2) 并发提议冲突：多个待审核提议同时修改同一条目 -> 硬冲突
    pending_touched: dict[str, str] = {}
    for p in pending_proposals:
        for e in p.events:
            pending_touched.setdefault(e.item_id, p.id)
    overlap = touched & set(pending_touched)
    for item_id in sorted(overlap):
        report.hard.append(f"条目 {item_id} 被待审核提议 {pending_touched[item_id]} 同时修改")

    # 3) 隐性依赖告警：被修改条目被其它条目显式引用（如 D2 酒店依赖 D1 车次）
    for item_id in sorted(touched):
        for other in state.items.values():
            if item_id in other.refs:
                report.warnings.append(
                    f"条目 {other.id}（{other.title}）显式依赖被修改的条目 {item_id}，请人工判断"
                )

    return report
