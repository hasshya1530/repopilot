from __future__ import annotations

import difflib
import os
import tempfile
from pathlib import Path, PurePosixPath

from agents.implementer.applier.errors import (
    ChangeApplicationConfigurationError,
    ChangeApplicationConflictError,
    ChangeApplicationValidationError,
)
from agents.implementer.applier.models import (
    AppliedChange,
    AppliedChangeStatus,
    ChangeApplicationResult,
)
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)


class ChangeApplier:
    """Safely applies LLM-generated code changes to a workspace."""

    def __init__(self, workspace_path: Path) -> None:
        self._workspace_path = workspace_path.resolve()

        if not self._workspace_path.exists():
            raise ChangeApplicationConfigurationError(
                f"Workspace does not exist: {workspace_path}"
            )

        if not self._workspace_path.is_dir():
            raise ChangeApplicationConfigurationError(
                f"Workspace is not a directory: {workspace_path}"
            )

    def apply(
        self,
        result: ImplementationResult,
        *,
        dry_run: bool = False,
    ) -> ChangeApplicationResult:
        applied_changes: list[AppliedChange] = []

        for change in result.changes:
            target = self._resolve_target(change.file_path)
            self._validate_change(change, target)

            old_content = (
                target.read_text(encoding="utf-8")
                if target.exists()
                else ""
            )

            diff = self._build_diff(
                change.file_path,
                old_content,
                change.content,
                change.operation,
            )

            if not dry_run:
                self._apply_change(change, target)

            applied_changes.append(
                AppliedChange(
                    file_path=change.file_path,
                    status=AppliedChangeStatus.APPLIED,
                    operation=change.operation.value,
                    diff=diff,
                )
            )

        return ChangeApplicationResult(
            changes=tuple(applied_changes),
            files_changed=len(applied_changes),
            dry_run=dry_run,
        )

    def _resolve_target(self, file_path: str) -> Path:
        normalized = file_path.strip().replace("\\", "/")

        if not normalized:
            raise ChangeApplicationValidationError(
                "Change file path cannot be empty."
            )

        relative = PurePosixPath(normalized)

        if relative.is_absolute():
            raise ChangeApplicationValidationError(
                f"Absolute paths are not allowed: {file_path}"
            )

        if ".." in relative.parts:
            raise ChangeApplicationValidationError(
                f"Path traversal is not allowed: {file_path}"
            )

        target = (self._workspace_path / Path(*relative.parts)).resolve()

        try:
            target.relative_to(self._workspace_path)
        except ValueError as exc:
            raise ChangeApplicationValidationError(
                f"Path escapes workspace: {file_path}"
            ) from exc

        return target

    def _validate_change(
        self,
        change: CodeChange,
        target: Path,
    ) -> None:
        if change.operation == ChangeOperation.CREATE:
            if target.exists():
                raise ChangeApplicationConflictError(
                    f"Cannot create existing file: {change.file_path}"
                )

            if not change.content:
                raise ChangeApplicationValidationError(
                    f"Created file cannot be empty: {change.file_path}"
                )

        elif change.operation == ChangeOperation.MODIFY:
            if not target.exists():
                raise ChangeApplicationConflictError(
                    f"Cannot modify missing file: {change.file_path}"
                )

            if not target.is_file():
                raise ChangeApplicationValidationError(
                    f"Target is not a file: {change.file_path}"
                )

        elif change.operation == ChangeOperation.DELETE:
            if not target.exists():
                raise ChangeApplicationConflictError(
                    f"Cannot delete missing file: {change.file_path}"
                )

            if not target.is_file():
                raise ChangeApplicationValidationError(
                    f"Target is not a file: {change.file_path}"
                )

            if change.content:
                raise ChangeApplicationValidationError(
                    f"Delete change must not contain content: {change.file_path}"
                )

    def _apply_change(
        self,
        change: CodeChange,
        target: Path,
    ) -> None:
        if change.operation == ChangeOperation.DELETE:
            target.unlink()
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, change.content)

    @staticmethod
    def _atomic_write(
        target: Path,
        content: str,
    ) -> None:
        fd, temp_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _build_diff(
        file_path: str,
        old_content: str,
        new_content: str,
        operation: ChangeOperation,
    ) -> str:
        if operation == ChangeOperation.DELETE:
            new_content = ""

        if operation == ChangeOperation.CREATE:
            old_content = ""

        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=file_path,
            tofile=file_path,
        )

        return "".join(diff)
