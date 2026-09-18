from pathlib import Path
from uuid import UUID

import pytest

from agents.debugger.analyzer import FailureAnalyzer
from agents.debugger.models import DebuggerStatus
from agents.debugger.repair_generator import RepairGenerator
from agents.debugger.service import DebuggerService
from agents.implementer.applier.service import ChangeApplier
from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextFile,
)
from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider
from agents.testing import runner as testing_runner

BROKEN_APP = """\
def add(a: int, b: int) -> int:
    return a - b
"""


TEST_FILE = """\
from app import add


def test_add():
    assert add(2, 3) == 5
"""


FIXED_APP = """\
def add(a: int, b: int) -> int:
    return a + b
"""


class FakeLLMProvider(LLMProvider):
    """Deterministic provider returning the known repair for this E2E test."""

    @property
    def model_name(self) -> str:
        return "fake-repair-model"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        return LLMResponse(
            content="""\
{
  "summary": "Fix add() to perform addition instead of subtraction.",
  "changes": [
    {
      "file_path": "app.py",
      "operation": "modify",
      "content": "def add(a: int, b: int) -> int:\\n    return a + b\\n",
      "reason": "The implementation subtracts b instead of adding b."
    }
  ]
}
""",
            model=self.model_name,
        )


def make_context(repository_path: Path) -> ImplementationContext:
    return ImplementationContext(
        repository_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        task_description="Fix the failing add function.",
        files=(
            ImplementationContextFile(
                file_path="app.py",
                content=(repository_path / "app.py").read_text(
                    encoding="utf-8"
                ),
                reason="File contains the failing implementation.",
            ),
        ),
        symbols=(),
        dependencies=(),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_self_repair_fixes_real_failing_repository(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    (repository / "app.py").write_text(
        BROKEN_APP,
        encoding="utf-8",
    )

    tests_directory = repository / "tests"
    tests_directory.mkdir()

    (tests_directory / "test_app.py").write_text(
        TEST_FILE,
        encoding="utf-8",
    )

    runner = testing_runner.TestRunner()

    initial_result = runner.run(repository)

    assert initial_result.succeeded is False
    assert initial_result.exit_code != 0

    context = make_context(repository)

    provider = FakeLLMProvider()
    generator = RepairGenerator(provider)

    service = DebuggerService(
        analyzer=FailureAnalyzer(),
        repair_generator=generator,
        change_applier_factory=ChangeApplier,
        test_runner=runner,
        max_attempts=1,
    )

    result = await service.debug(
        repository,
        context,
    )

    assert result.status == DebuggerStatus.FIXED
    assert result.succeeded is True

    assert len(result.attempts) == 1
    assert result.attempts[0].test_result.succeeded is True

    assert (repository / "app.py").read_text(
        encoding="utf-8"
    ) == FIXED_APP

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert request.temperature == 0.0
    assert "Fix the failing add function." in request.messages[1].content
    assert "AssertionError" in request.messages[1].content


@pytest.mark.integration
def test_real_test_runner_detects_python_repository(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    (repository / "tests").mkdir()

    (repository / "tests" / "test_example.py").write_text(
        "def test_example():\n    assert True\n",
        encoding="utf-8",
    )

    runner = testing_runner.TestRunner()

    result = runner.run(repository)

    assert result.succeeded is True
    assert result.exit_code == 0
