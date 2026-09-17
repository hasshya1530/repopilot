from pathlib import Path

from agents.sandbox.models import SandboxExecutionResult
from agents.testing.models import TestStatus as Status
from agents.testing.runner import TestRunner as Runner


class FakeSandboxExecutor:
    def __init__(self, result: SandboxExecutionResult) -> None:
        self.result = result
        self.commands: list[list[str]] = []

    def execute(
        self,
        workspace_path: Path,
        command: list[str],
    ) -> SandboxExecutionResult:
        self.commands.append(command)
        return self.result


def test_runner_reports_passed_tests(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")

    executor = FakeSandboxExecutor(
        SandboxExecutionResult(
            command=("python", "-m", "pytest"),
            exit_code=0,
            stdout="3 passed\n",
            stderr="",
            timed_out=False,
            duration_seconds=1.2,
        )
    )

    result = Runner(executor).run(tmp_path)

    assert result.status == Status.PASSED
    assert result.succeeded
    assert result.exit_code == 0
    assert result.stdout == "3 passed\n"
    assert executor.commands == [["python", "-m", "pytest"]]


def test_runner_reports_failed_tests(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")

    executor = FakeSandboxExecutor(
        SandboxExecutionResult(
            command=("python", "-m", "pytest"),
            exit_code=1,
            stdout="1 failed\n",
            stderr="AssertionError\n",
            timed_out=False,
            duration_seconds=1.0,
        )
    )

    result = Runner(executor).run(tmp_path)

    assert result.status == Status.FAILED
    assert not result.succeeded
    assert result.exit_code == 1


def test_runner_reports_timeout(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")

    executor = FakeSandboxExecutor(
        SandboxExecutionResult(
            command=("python", "-m", "pytest"),
            exit_code=-1,
            stdout="",
            stderr="",
            timed_out=True,
            duration_seconds=2.0,
        )
    )

    result = Runner(executor).run(tmp_path)

    assert result.status == Status.TIMEOUT
    assert not result.succeeded
