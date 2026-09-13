"""事件溯源引擎原型（第 0 周 Spike）。

核心不变量：
- 事件流 append-only，绝不改写历史；
- 定稿状态 = 事件流回放结果；
- 回滚 = 追加补偿事件，而非删除历史事件；
- 冲突检测发生在采纳动作执行时（基于当前已回放定稿），而非提交时；
- 临时备选 = 提交即采纳的紧急提议（emergency），可事后正式化或撤销。
"""

from .engine import (
    STATUS_ADOPTED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_REVOKED,
    AdoptionResult,
    Proposal,
    RollbackResult,
    TripEngine,
)

__all__ = [
    "TripEngine",
    "Proposal",
    "AdoptionResult",
    "RollbackResult",
    "STATUS_DRAFT",
    "STATUS_PENDING",
    "STATUS_ADOPTED",
    "STATUS_REJECTED",
    "STATUS_REVOKED",
]
