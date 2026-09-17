from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agents.sandbox.executor import DockerSandboxExecutor
from agents.sandbox.models import SandboxExecutionResult
from agents.testing.detector import TestDetector
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
    ) -> TestResult:
        command = self._detector.detect(repository_path)

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
