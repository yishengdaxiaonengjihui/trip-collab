"""领域异常定义。"""


class TripCollabError(Exception):
    """引擎领域错误基类。"""


class ProposalNotFoundError(TripCollabError):
    def __init__(self, proposal_id: str):
        super().__init__(f"提议不存在: {proposal_id}")
        self.proposal_id = proposal_id


class InvalidStatusError(TripCollabError):
    """提议状态与操作不匹配。"""


class HardConflictError(TripCollabError):
    """硬冲突：多个提议同时修改同一条目，或目标条目已不存在，禁止自动合并，强制人工判定。"""

    def __init__(self, conflicts: list[str]):
        super().__init__("存在硬冲突，禁止自动合并，需人工判定: " + "; ".join(conflicts))
        self.conflicts = conflicts


class ConfirmationRequiredError(TripCollabError):
    """软冲突/依赖告警：自动合并需要人工复核确认。"""

    def __init__(self, warnings: list[str]):
        super().__init__("存在需要人工复核确认的变更: " + "; ".join(warnings))
        self.warnings = warnings


class SnapshotNotFoundError(TripCollabError):
    """目标版本没有快照。"""
