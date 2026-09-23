from __future__ import annotations

import shlex
from pathlib import Path
from typing import Protocol

from agents.sandbox.executor import DockerSandboxExecutor
from agents.sandbox.models import SandboxExecutionResult
from agents.testing.detector import TestDetector
from agents.testing.errors import TestDetectionError
from agents.testing.models import TestResult, TestStatus


class SandboxExecutorProtocol(Protocol):
    def execute(
        self,
        workspace_path: Path,
        command: list[str],
    ) -> SandboxExecutionResult:
        ...


class TestRunner:
    """Detect and execute repository tests inside the sandbox."""

    def __init__(
        self,
        sandbox_executor: SandboxExecutorProtocol | None = None,
        detector: TestDetector | None = None,
    ) -> None:
        self._sandbox_executor = (
            sandbox_executor
            if sandbox_executor is not None
            else DockerSandboxExecutor()
        )
        self._detector = detector or TestDetector()

    def run(
        self,
        repository_path: Path,
        validation_command: str | None = None,
    ) -> TestResult:
        command = self._resolve_command(
            repository_path,
            validation_command,
        )

        result = self._sandbox_executor.execute(
            repository_path,
            command,
        )

        if result.timed_out:
            status = TestStatus.TIMEOUT
        elif result.exit_code == 0:
            status = TestStatus.PASSED
        else:
            status = TestStatus.FAILED

        return TestResult(
            status=status,
            command=result.command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=result.duration_seconds,
        )

    def _resolve_command(
        self,
        repository_path: Path,
        validation_command: str | None,
    ) -> list[str]:
        if validation_command is None:
            return self._detector.detect(repository_path)

        command = self._parse_validation_command(validation_command)

        if not command:
            raise TestDetectionError(
                "Approved validation command cannot be empty."
            )

        return command

    @staticmethod
    def _parse_validation_command(validation_command: str) -> list[str]:
        try:
            return shlex.split(validation_command)
        except ValueError as exc:
            raise TestDetectionError(
                f"Invalid validation command: {validation_command!r}"
            ) from exc
