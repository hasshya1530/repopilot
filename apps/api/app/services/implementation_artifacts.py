from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.implementer.applier.models import ChangeApplicationResult
from agents.implementer.models import ChangeOperation, ImplementationResult
from apps.api.app.models.file_change import FileChange, FileChangeOperation
from apps.api.app.services.artifacts import create_file_change


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    file_path: str
    exists: bool
    content: str | None
    content_hash: str | None


def _hash_content(content: str | None) -> str | None:
    if content is None:
        return None

    return hashlib.sha256(
        content.encode("utf-8"),
    ).hexdigest()


def _snapshot_file(
    workspace_path: Path,
    file_path: str,
) -> FileSnapshot:
    target = workspace_path / file_path

    if not target.exists() or not target.is_file():
        return FileSnapshot(
            file_path=file_path,
            exists=False,
            content=None,
            content_hash=None,
        )

    content = target.read_text(encoding="utf-8")

    return FileSnapshot(
        file_path=file_path,
        exists=True,
        content=content,
        content_hash=_hash_content(content),
    )


def capture_implementation_snapshots(
    workspace_path: Path,
    implementation: ImplementationResult,
) -> dict[str, FileSnapshot]:
    """Capture workspace state before implementation changes are applied."""
    return {
        change.file_path: _snapshot_file(
            workspace_path,
            change.file_path,
        )
        for change in implementation.changes
    }


def _to_file_change_operation(
    operation: ChangeOperation,
) -> FileChangeOperation:
    mapping = {
        ChangeOperation.CREATE: FileChangeOperation.CREATED,
        ChangeOperation.MODIFY: FileChangeOperation.MODIFIED,
        ChangeOperation.DELETE: FileChangeOperation.DELETED,
    }

    return mapping[operation]


def _line_counts(diff: str) -> tuple[int, int]:
    additions = 0
    deletions = 0

    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    return additions, deletions


async def persist_applied_changes(
    session: AsyncSession,
    *,
    agent_run_id: UUID,
    implementation: ImplementationResult,
    application_result: ChangeApplicationResult,
    snapshots: dict[str, FileSnapshot],
    workspace_path: Path,
) -> list[FileChange]:
    """Persist actual implementation changes after execution."""
    persisted_changes: list[FileChange] = []

    applied_by_path = {
        change.file_path: change
        for change in application_result.changes
    }

    for implementation_change in implementation.changes:
        file_path = implementation_change.file_path
        snapshot = snapshots[file_path]
        applied_change = applied_by_path.get(file_path)

        target = workspace_path / file_path

        if target.exists() and target.is_file():
            after_content = target.read_text(
                encoding="utf-8",
            )
        else:
            after_content = None

        if applied_change is not None:
            diff = applied_change.diff
            additions, deletions = _line_counts(diff)
        else:
            diff = None
            additions = 0
            deletions = 0

        persisted_change = await create_file_change(
            session,
            agent_run_id=agent_run_id,
            file_path=file_path,
            operation=_to_file_change_operation(
                implementation_change.operation,
            ),
            before_content=snapshot.content,
            after_content=after_content,
            diff=diff,
            before_hash=snapshot.content_hash,
            after_hash=_hash_content(after_content),
            line_additions=additions,
            line_deletions=deletions,
        )

        persisted_changes.append(persisted_change)

    return persisted_changes
