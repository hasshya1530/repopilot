from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.execution.models import ExecutionResult, ExecutionStatus
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
from agents.orchestrator.adapters.artifacts import (
    SqlAlchemyArtifactPersistence,
)
from agents.testing.models import TestResult, TestStatus
from apps.api.app.models.agent_run import AgentRun, AgentRunStatus
from apps.api.app.models.file_change import (
    FileChange,
    FileChangeOperation,
)
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task, TaskStatus
from apps.api.app.models.task_step import (
    AgentType,
    TaskStep,
    TaskStepStatus,
)
from apps.api.app.models.test_run import (
    TestRun as TestRunModel,
)
from apps.api.app.models.test_run import (
    TestRunStatus as TestRunStatusModel,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_implementation_artifacts_persist_complete_execution_lifecycle(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    repository = Repository(
        owner="integration",
        name=f"artifact-{uuid4().hex[:12]}",
        full_name=f"integration/artifact-{uuid4().hex[:12]}",
        github_repo_id=uuid4().int % 1_000_000_000,
        default_branch="main",
        description="Orchestration artifact integration test",
        is_private=False,
        clone_url="https://github.com/integration/artifact-test.git",
    )
    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        title="Persist implementation artifacts",
        description="Verify implementation execution artifacts.",
        status=TaskStatus.IMPLEMENTING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    persistence = SqlAlchemyArtifactPersistence(
        session=db_session,
        model_provider="ollama",
        model_name="qwen2.5-coder:3b",
    )

    task_step, agent_run = await persistence.start_agent(
        task_id=task.id,
        agent_type=AgentType.CODING,
        step_number=1,
        step_name="implementation",
        input_data="Implement the requested change.",
        attempt_number=1,
    )

    assert task_step.status == TaskStepStatus.RUNNING
    assert agent_run.status == AgentRunStatus.RUNNING
    assert agent_run.agent_type == AgentType.CODING
    assert agent_run.model_provider == "ollama"
    assert agent_run.model_name == "qwen2.5-coder:3b"

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    source = workspace / "calculator.py"
    source.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n",
        encoding="utf-8",
    )

    implementation = ImplementationResult(
        summary="Add a multiply helper.",
        changes=(
            CodeChange(
                file_path="calculator.py",
                operation=ChangeOperation.MODIFY,
                content=(
                    "def add(a: int, b: int) -> int:\n"
                    "    return a + b\n\n"
                    "def multiply(a: int, b: int) -> int:\n"
                    "    return a * b\n"
                ),
                reason="Add the requested multiplication helper.",
            ),
        ),
    )

    snapshots = persistence.capture_snapshots(
        workspace_path=workspace,
        implementation=implementation,
    )

    assert snapshots["calculator.py"].exists is True
    assert snapshots["calculator.py"].content == (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    assert snapshots["calculator.py"].content_hash is not None

    source.write_text(
        implementation.changes[0].content,
        encoding="utf-8",
    )

    diff = (
        "--- a/calculator.py\n"
        "+++ b/calculator.py\n"
        "@@ -1,2 +1,5 @@\n"
        " def add(a: int, b: int) -> int:\n"
        "     return a + b\n"
        "+\n"
        "+def multiply(a: int, b: int) -> int:\n"
        "+    return a * b\n"
    )

    application_result = ChangeApplicationResult(
        changes=(
            AppliedChange(
                file_path="calculator.py",
                status=AppliedChangeStatus.APPLIED,
                operation=ChangeOperation.MODIFY.value,
                diff=diff,
            ),
        ),
        files_changed=1,
        dry_run=False,
    )

    test_result = TestResult(
        status=TestStatus.PASSED,
        command=("python", "-m", "pytest", "-q"),
        exit_code=0,
        stdout="1 passed in 0.04s",
        stderr="",
        duration_seconds=0.04,
        test_count=1,
        failure_count=0,
    )

    execution = ExecutionResult(
        status=ExecutionStatus.PASSED,
        changes=application_result,
        tests=test_result,
    )

    file_changes = await persistence.persist_implementation(
        agent_run_id=agent_run.id,
        workspace_path=workspace,
        implementation=implementation,
        application_result=application_result,
        snapshots=snapshots,
    )

    persisted_test = await persistence.persist_test_result(
        agent_run_id=agent_run.id,
        workspace_path=workspace,
        execution=execution,
    )

    await persistence.complete_agent(
        task_step_id=task_step.id,
        agent_run_id=agent_run.id,
        output_data="Implementation completed successfully.",
    )

    stored_changes = (
        await db_session.scalars(
            select(FileChange).where(
                FileChange.agent_run_id == agent_run.id,
            )
        )
    ).all()

    stored_test = await db_session.get(
        TestRunModel,
        persisted_test.id,
    )
    stored_agent_run = await db_session.get(
        AgentRun,
        agent_run.id,
    )
    stored_task_step = await db_session.get(
        TaskStep,
        task_step.id,
    )

    assert len(file_changes) == 1
    assert len(stored_changes) == 1

    change = stored_changes[0]

    assert change.id == file_changes[0].id
    assert change.file_path == "calculator.py"
    assert change.operation == FileChangeOperation.MODIFIED

    assert change.before_content == (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    assert change.after_content == (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def multiply(a: int, b: int) -> int:\n"
        "    return a * b\n"
    )

    assert change.before_hash is not None
    assert change.after_hash is not None
    assert change.before_hash != change.after_hash

    assert change.diff == diff
    assert change.line_additions == 3
    assert change.line_deletions == 0

    assert stored_test is not None
    assert stored_test.agent_run_id == agent_run.id
    assert stored_test.status == TestRunStatusModel.PASSED
    assert stored_test.command == "python -m pytest -q"
    assert stored_test.exit_code == 0
    assert stored_test.stdout == "1 passed in 0.04s"
    assert stored_test.stderr == ""
    assert stored_test.duration_ms == 40
    assert stored_test.working_directory == str(workspace)

    assert stored_agent_run is not None
    assert stored_agent_run.status == AgentRunStatus.COMPLETED
    assert stored_agent_run.output_data == (
        "Implementation completed successfully."
    )

    assert stored_task_step is not None
    assert stored_task_step.status == TaskStepStatus.COMPLETED
    assert stored_task_step.output_data == (
        "Implementation completed successfully."
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_execution_artifacts_are_persisted(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    repository = Repository(
        owner="integration",
        name=f"artifact-failure-{uuid4().hex[:12]}",
        full_name=f"integration/artifact-failure-{uuid4().hex[:12]}",
        github_repo_id=uuid4().int % 1_000_000_000,
        default_branch="main",
        description="Failed execution artifact integration test",
        is_private=False,
        clone_url="https://github.com/integration/artifact-failure.git",
    )
    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)

    task = Task(
        repository_id=repository.id,
        title="Persist failed execution",
        description="Verify failed test artifacts.",
        status=TaskStatus.TESTING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    persistence = SqlAlchemyArtifactPersistence(
        session=db_session,
        model_provider="ollama",
        model_name="qwen2.5-coder:3b",
    )

    task_step, agent_run = await persistence.start_agent(
        task_id=task.id,
        agent_type=AgentType.CODING,
        step_number=1,
        step_name="implementation",
        input_data="Run failing implementation.",
    )

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    implementation = ImplementationResult(
        summary="Introduce a failing change.",
        changes=(
            CodeChange(
                file_path="calculator.py",
                operation=ChangeOperation.CREATE,
                content="raise RuntimeError('intentional failure')\n",
                reason="Integration test failure fixture.",
            ),
        ),
    )

    snapshots = persistence.capture_snapshots(
        workspace_path=workspace,
        implementation=implementation,
    )

    (workspace / "calculator.py").write_text(
        implementation.changes[0].content,
        encoding="utf-8",
    )

    application_result = ChangeApplicationResult(
        changes=(
            AppliedChange(
                file_path="calculator.py",
                status=AppliedChangeStatus.APPLIED,
                operation=ChangeOperation.CREATE.value,
                diff=(
                    "+++ b/calculator.py\n"
                    "+raise RuntimeError('intentional failure')\n"
                ),
            ),
        ),
        files_changed=1,
        dry_run=False,
    )

    test_result = TestResult(
        status=TestStatus.FAILED,
        command=("python", "-m", "pytest", "-q"),
        exit_code=1,
        stdout="",
        stderr="1 failed",
        duration_seconds=0.12,
        test_count=1,
        failure_count=1,
    )

    execution = ExecutionResult(
        status=ExecutionStatus.FAILED,
        changes=application_result,
        tests=test_result,
    )

    await persistence.persist_implementation(
        agent_run_id=agent_run.id,
        workspace_path=workspace,
        implementation=implementation,
        application_result=application_result,
        snapshots=snapshots,
    )

    persisted_test = await persistence.persist_test_result(
        agent_run_id=agent_run.id,
        workspace_path=workspace,
        execution=execution,
    )

    await persistence.fail_agent(
        task_step_id=task_step.id,
        agent_run_id=agent_run.id,
        error_message="Tests failed after implementation.",
    )

    stored_test = await db_session.get(
        TestRunModel,
        persisted_test.id,
    )
    stored_agent_run = await db_session.get(
        AgentRun,
        agent_run.id,
    )
    stored_task_step = await db_session.get(
        TaskStep,
        task_step.id,
    )

    assert stored_test is not None
    assert stored_test.status == TestRunStatusModel.FAILED
    assert stored_test.exit_code == 1
    assert stored_test.stderr == "1 failed"

    assert stored_agent_run is not None
    assert stored_agent_run.status == AgentRunStatus.FAILED
    assert stored_agent_run.error_message == (
        "Tests failed after implementation."
    )

    assert stored_task_step is not None
    assert stored_task_step.status == TaskStepStatus.FAILED
    assert stored_task_step.error_message == (
        "Tests failed after implementation."
    )
