"""API 请求/响应模型（pydantic v2）。"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ---------- 行程条目 ----------


class ItemIn(BaseModel):
    id: str = Field(min_length=1)
    day: int = Field(ge=1)
    position: int = Field(ge=0)
    title: str = Field(min_length=1)
    refs: list[str] = Field(default_factory=list)
    amount: Optional[float] = None
    note: str = ""
    time: str = ""  # 展示时间，如 "09:30"
    tag: str = ""  # 条目类型：景区/饭店/酒店/交通/购物/其他（空=其他）


class ItemOut(ItemIn):
    pass


# ---------- 提议 ----------

_KIND = Literal["created", "updated", "deleted"]


class ChangeEventIn(BaseModel):
    kind: _KIND
    item_id: str = Field(min_length=1)
    # created: 完整条目字段；updated: 变更字段；deleted: 忽略
    payload: Any = None


class ProposalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    reason: str = Field(default="", max_length=500)
    events: list[ChangeEventIn] = Field(min_length=1)
    emergency: bool = False


class ProposalOut(BaseModel):
    id: str
    title: str
    reason: str
    created_by: str
    status: str
    emergency: bool
    created_at: Optional[int]
    submitted_at: Optional[int] = None
    adopted_at: Optional[int] = None
    adopted_version: Optional[int] = None
    reject_reason: Optional[str] = None
    resolution_note: Optional[str] = None
    events: list[dict]
    warnings: list[str] = Field(default_factory=list)
    hard_conflicts: list[str] = Field(default_factory=list)


class AdoptIn(BaseModel):
    confirmed: bool = False
    force: bool = False
    resolution_note: Optional[str] = None


class RejectIn(BaseModel):
    reason: str = Field(default="", max_length=200)


# ---------- 行程 ----------


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class TripOut(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: str
    version: int
    days: dict[int, list[ItemOut]]
    members: list[dict]
    pending_count: int
    notify_count: int


class TripBrief(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: str
    version: int
    item_count: int
    pending_count: int


# ---------- 版本 / 回滚 ----------


class VersionOut(BaseModel):
    version: int
    kind: str  # adopt | emergency | rollback | revoke
    proposal_id: Optional[str]
    title: Optional[str]
    adopted_at: int
    item_count: int


class RollbackIn(BaseModel):
    version: int = Field(ge=0)
    reason: Optional[str] = None


class RollbackOut(BaseModel):
    target_version: int
    new_version: int
    affected_proposals: list[str]
    compensating_event_count: int


# ---------- 成员 ----------


class MemberIn(BaseModel):
    user_id: str = Field(min_length=1)
    role: Literal["owner", "editor", "member"] = "member"


class MemberRoleIn(BaseModel):
    role: Literal["owner", "editor", "member"]


# ---------- 通用 ----------


class ErrorOut(BaseModel):
    code: str
    message: str
    detail: Any = None
