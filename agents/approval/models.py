from dataclasses import dataclass
from uuid import UUID

from apps.api.app.models.pull_request import ApprovalStatus


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    pull_request_id: UUID


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    pull_request_id: UUID
    status: ApprovalStatus
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    pull_request_id: UUID
    status: ApprovalStatus
    reason: str | None = None

    @property
    def approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    @property
    def rejected(self) -> bool:
        return self.status == ApprovalStatus.REJECTED

    @property
    def pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING
