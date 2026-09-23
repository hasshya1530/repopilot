from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.debugger.analyzer import FailureAnalysis, FailureAnalyzer
from agents.debugger.models import DebuggerStatus
from agents.debugger.repair_models import RepairProposal
from agents.debugger.service import DebuggerService
from agents.implementer.applier.models import (
    AppliedChange,
    AppliedChangeStatus,
    ChangeApplicationResult,
)
from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.orchestrator.adapters.artifacts import SqlAlchemyArtifactPersistence
from agents.testing.models import TestResult, TestStatus
from apps.api.app.models.agent_run import AgentRun
from apps.api.app.models.file_change import FileChange
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.models.task_step import AgentType, TaskStep, TaskStepStatus
from apps.api.app.models.test_run import TestRun as TestRunModel


def make_context(repository_id: UUID) -> ImplementationContext:
    return ImplementationContext(
        repository_id=repository_id,
        task_description="Fix the failing implementation.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_test_result(
    status: TestStatus,
    *,
    exit_code: int,
) -> TestResult:
    return TestResult(
        status=status,
        command=("pytest", "-q"),
        exit_code=exit_code,
        stdout="1 passed\n" if status == TestStatus.PASSED else "",
        stderr="AssertionError\n" if status == TestStatus.FAILED else "",
        duration_seconds=0.1,
    )


def make_proposal() -> RepairProposal:
    return RepairProposal(
        diagnosis="Fix the failing implementation.",
        changes=(
            CodeChange(
                file_path="example.py",
                operation=ChangeOperation.MODIFY,
                content="print('fixed')\n",
                reason="Fix the failing implementation.",
            ),
        ),
    )


class FakeTestRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, repository_path: Path) -> TestResult:
        self.calls += 1

        if self.calls == 1:
            return make_test_result(
                TestStatus.FAILED,
                exit_code=1,
            )

        return make_test_result(
            TestStatus.PASSED,
            exit_code=0,
        )


class FakeRepairGenerator:
    async def generate(
        self,
        analysis: FailureAnalysis,
        context: ImplementationContext,
        *,
        max_tokens: int = 8192,
    ) -> RepairProposal:
        return make_proposal()


class FakeApplier:
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path

    def apply(
        self,
        implementation: ImplementationResult,
    ) -> ChangeApplicationResult:
        target = self.workspace_path / "example.py"

        target.write_text(
            implementation.changes[0].content,
            encoding="utf-8",
        )

        return ChangeApplicationResult(
            changes=(
                AppliedChange(
                    file_path="example.py",
                    status=AppliedChangeStatus.APPLIED,
                    operation="modify",
                    diff=(
                        "--- a/example.py\n"
                        "+++ b/example.py\n"
                        "-print('broken')\n"
                        "+print('fixed')\n"
                    ),
                ),
            ),
            files_changed=1,
            dry_run=False,
        )


class FakeApplierFactory:
    def __call__(self, workspace_path: Path) -> FakeApplier:
        return FakeApplier(workspace_path)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_debugger_persists_failed_test_repair_and_passed_test(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    repository_id = uuid4()
    task_id = uuid4()

    repository_name = f"debugger-{uuid4().hex[:8]}"

    repository = Repository(
        id=repository_id,
        owner="repopilot-test",
        name=repository_name,
        full_name=f"repopilot-test/{repository_name}",
        github_repo_id=int(uuid4().hex[:8], 16) % 1_000_000_000,
        default_branch="main",
        clone_url=f"https://github.com/repopilot-test/{repository_name}.git",
    )

    db_session.add(repository)
    await db_session.flush()

    task = Task(
        id=task_id,
        repository_id=repository_id,
        external_issue_id=999001,
        issue_number=999001,
        title="Fix failing implementation",
        description="Fix the failing implementation.",
        status=TaskStatus.TESTING,
        branch_name="repopilot/test-debugger-artifacts",
    )

    db_session.add(task)
    await db_session.commit()

    repository_path = tmp_path / "repository"
    repository_path.mkdir()

    (repository_path / "example.py").write_text(
        "print('broken')\n",
        encoding="utf-8",
    )

    artifacts = SqlAlchemyArtifactPersistence(
        session=db_session,
    )

    service = DebuggerService(
        analyzer=FailureAnalyzer(),
        repair_generator=FakeRepairGenerator(),
        change_applier_factory=FakeApplierFactory(),
        test_runner=FakeTestRunner(),
        max_attempts=1,
        artifact_persistence=artifacts,
    )

    result = await service.debug(
        repository_path,
        make_context(repository_id),
        task_id=task_id,
    )

    assert result.status == DebuggerStatus.FIXED
    assert result.succeeded is True
    assert len(result.attempts) == 1
    assert result.final_test_result.status == TestStatus.PASSED

    step_result = await db_session.execute(
        select(TaskStep)
        .where(TaskStep.task_id == task_id)
        .where(TaskStep.agent_type == AgentType.DEBUGGER)
    )
    step = step_result.scalar_one()

    assert step.status == TaskStepStatus.COMPLETED
    assert step.step_number == 5

    run_result = await db_session.execute(
        select(AgentRun)
        .where(AgentRun.task_step_id == step.id)
        .where(AgentRun.agent_type == AgentType.DEBUGGER)
    )
    agent_run = run_result.scalar_one()

    assert agent_run.status == "completed"
    assert agent_run.attempt_number == 1
    assert agent_run.output_data is not None

    test_result = await db_session.execute(
        select(TestRunModel)
        .where(TestRunModel.agent_run_id == agent_run.id)
        .order_by(TestRunModel.created_at)
    )
    test_runs = list(test_result.scalars())

    assert len(test_runs) == 2

    assert test_runs[0].status == "failed"
    assert test_runs[0].exit_code == 1
    assert test_runs[0].command == "pytest -q"

    assert test_runs[1].status == "passed"
    assert test_runs[1].exit_code == 0
    assert test_runs[1].command == "pytest -q"

    file_change_result = await db_session.execute(
        select(FileChange)
        .where(FileChange.agent_run_id == agent_run.id)
    )
    file_changes = list(file_change_result.scalars())

    assert len(file_changes) == 1

    file_change = file_changes[0]

    assert file_change.file_path == "example.py"
    assert file_change.operation == "modified"
    assert file_change.before_content == "print('broken')\n"
    assert file_change.after_content == "print('fixed')\n"
    assert file_change.diff is not None
    assert "-print('broken')" in file_change.diff
    assert "+print('fixed')" in file_change.diff
    assert file_change.before_hash is not None
    assert file_change.after_hash is not None
    assert file_change.before_hash != file_change.after_hash
