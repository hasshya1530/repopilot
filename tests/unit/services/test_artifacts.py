from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from apps.api.app.core.database import async_session_factory
from apps.api.app.models.agent_run import AgentRun, AgentRunStatus
from apps.api.app.models.file_change import FileChange, FileChangeOperation
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
from apps.api.app.models.tool_call import ToolCall, ToolCallStatus
from apps.api.app.services.artifacts import (
    complete_agent_run,
    complete_task_step,
    complete_test_run,
    complete_tool_call,
    create_agent_run,
    create_file_change,
    create_task_step,
    create_test_run,
    create_tool_call,
    fail_agent_run,
    fail_task_step,
    fail_tool_call,
    get_task_step,
)


def _repository() -> Repository:
    repository_name = f"artifact-{uuid4().hex[:8]}"

    return Repository(
        id=uuid4(),
        owner="artifact-test-owner",
        name=repository_name,
        full_name=f"artifact-test-owner/{repository_name}",
        github_repo_id=abs(uuid4().int) % 2_000_000_000,
        default_branch="main",
        clone_url="https://github.com/artifact-test-owner/test.git",
    )


async def _create_task() -> tuple[Repository, Task]:
    repository = _repository()

    task = Task(
        id=uuid4(),
        repository_id=repository.id,
        title="Artifact persistence test",
        description="Verify persisted agent artifacts.",
        status=TaskStatus.PENDING,
    )

    async with async_session_factory() as session:
        session.add(repository)
        session.add(task)
        await session.commit()

    return repository, task


async def _cleanup(repository_id: UUID) -> None:
    async with async_session_factory() as session:
        repository = await session.get(
            Repository,
            repository_id,
        )

        if repository is not None:
            await session.delete(repository)
            await session.commit()


@pytest.mark.asyncio
async def test_task_step_lifecycle() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="implementation",
                agent_type=AgentType.CODING,
                input_data="Implement the approved plan.",
            )

            assert step.task_id == task.id
            assert step.step_number == 1
            assert step.agent_type == AgentType.CODING
            assert step.status == TaskStepStatus.RUNNING
            assert step.input_data == "Implement the approved plan."

        async with async_session_factory() as session:
            stored = await get_task_step(
                session,
                step.id,
            )

            assert stored is not None
            assert stored.status == TaskStepStatus.RUNNING

            completed = await complete_task_step(
                session,
                step.id,
                output_data="Implementation completed.",
            )

            assert completed is not None
            assert completed.status == TaskStepStatus.COMPLETED
            assert completed.output_data == "Implementation completed."

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_failed_task_step_persists_error() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="testing",
                agent_type=AgentType.TESTING,
            )

            failed = await fail_task_step(
                session,
                step.id,
                error_message="Tests failed.",
            )

            assert failed is not None
            assert failed.status == TaskStepStatus.FAILED
            assert failed.error_message == "Tests failed."

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_agent_run_lifecycle() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="planning",
                agent_type=AgentType.ARCHITECTURE,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.ARCHITECTURE,
                attempt_number=1,
                model_provider="ollama",
                model_name="qwen2.5-coder:3b",
                input_data="Plan the requested change.",
            )

            assert run.task_step_id == step.id
            assert run.agent_type == AgentType.ARCHITECTURE.value
            assert run.status == AgentRunStatus.RUNNING
            assert run.attempt_number == 1
            assert run.model_provider == "ollama"
            assert run.model_name == "qwen2.5-coder:3b"

            completed = await complete_agent_run(
                session,
                run.id,
                output_data='{"steps": []}',
                input_tokens=100,
                output_tokens=50,
            )

            assert completed is not None
            assert completed.status == AgentRunStatus.COMPLETED
            assert completed.output_data == '{"steps": []}'
            assert completed.input_tokens == 100
            assert completed.output_tokens == 50

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_failed_agent_run_persists_error() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="planning",
                agent_type=AgentType.ARCHITECTURE,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.ARCHITECTURE,
            )

            failed = await fail_agent_run(
                session,
                run.id,
                error_message="Model generation failed.",
            )

            assert failed is not None
            assert failed.status == AgentRunStatus.FAILED
            assert failed.error_message == "Model generation failed."

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_file_change_persists_implementation_artifact() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="implementation",
                agent_type=AgentType.CODING,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.CODING,
            )

            change = await create_file_change(
                session,
                agent_run_id=run.id,
                file_path="src/example.py",
                operation=FileChangeOperation.MODIFIED,
                before_content="return 1\n",
                after_content="return 2\n",
                diff="-return 1\n+return 2\n",
                before_hash="before",
                after_hash="after",
                line_additions=1,
                line_deletions=1,
            )

            assert change.agent_run_id == run.id
            assert change.file_path == "src/example.py"
            assert change.operation == FileChangeOperation.MODIFIED
            assert change.before_content == "return 1\n"
            assert change.after_content == "return 2\n"
            assert change.diff == "-return 1\n+return 2\n"
            assert change.before_hash == "before"
            assert change.after_hash == "after"
            assert change.line_additions == 1
            assert change.line_deletions == 1

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_test_run_lifecycle() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="testing",
                agent_type=AgentType.TESTING,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.TESTING,
            )

            test_run = await create_test_run(
                session,
                agent_run_id=run.id,
                command="pytest tests/unit",
                working_directory="/workspace",
            )

            assert test_run.agent_run_id == run.id
            assert test_run.command == "pytest tests/unit"
            assert test_run.status == TestRunStatusModel.RUNNING
            assert test_run.working_directory == "/workspace"

            completed = await complete_test_run(
                session,
                test_run.id,
                status=TestRunStatusModel.PASSED,
                exit_code=0,
                stdout="10 passed",
                stderr="",
                duration_ms=1200,
            )

            assert completed is not None
            assert completed.status == TestRunStatusModel.PASSED
            assert completed.exit_code == 0
            assert completed.stdout == "10 passed"
            assert completed.stderr == ""
            assert completed.duration_ms == 1200

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_tool_call_lifecycle() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="implementation",
                agent_type=AgentType.CODING,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.CODING,
            )

            tool_call = await create_tool_call(
                session,
                agent_run_id=run.id,
                tool_name="read_file",
                tool_server="filesystem",
                sequence_number=1,
                input_data='{"path":"src/example.py"}',
            )

            assert tool_call.agent_run_id == run.id
            assert tool_call.tool_name == "read_file"
            assert tool_call.tool_server == "filesystem"
            assert tool_call.sequence_number == 1
            assert tool_call.status == ToolCallStatus.RUNNING

            completed = await complete_tool_call(
                session,
                tool_call.id,
                output_data='{"content":"example"}',
                duration_ms=35,
            )

            assert completed is not None
            assert completed.status == ToolCallStatus.COMPLETED
            assert completed.output_data == '{"content":"example"}'
            assert completed.duration_ms == 35

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_failed_tool_call_persists_error() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="implementation",
                agent_type=AgentType.CODING,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.CODING,
            )

            tool_call = await create_tool_call(
                session,
                agent_run_id=run.id,
                tool_name="run_tests",
                sequence_number=1,
            )

            failed = await fail_tool_call(
                session,
                tool_call.id,
                error_message="Sandbox unavailable.",
                duration_ms=100,
            )

            assert failed is not None
            assert failed.status == ToolCallStatus.FAILED
            assert failed.error_message == "Sandbox unavailable."
            assert failed.duration_ms == 100

    finally:
        await _cleanup(repository.id)


@pytest.mark.asyncio
async def test_artifact_rows_are_persisted_in_database() -> None:
    repository, task = await _create_task()

    try:
        async with async_session_factory() as session:
            step = await create_task_step(
                session,
                task_id=task.id,
                step_number=1,
                name="implementation",
                agent_type=AgentType.CODING,
            )

            run = await create_agent_run(
                session,
                task_step_id=step.id,
                agent_type=AgentType.CODING,
            )

            change = await create_file_change(
                session,
                agent_run_id=run.id,
                file_path="src/example.py",
                operation=FileChangeOperation.CREATED,
                after_content="print('hello')\n",
            )

            test_run = await create_test_run(
                session,
                agent_run_id=run.id,
                command="pytest",
                status=TestRunStatusModel.PASSED,
                exit_code=0,
                stdout="passed",
            )

            tool_call = await create_tool_call(
                session,
                agent_run_id=run.id,
                tool_name="write_file",
                sequence_number=1,
            )

        async with async_session_factory() as session:
            stored_steps = await session.execute(
                select(TaskStep).where(TaskStep.id == step.id)
            )
            stored_runs = await session.execute(
                select(AgentRun).where(AgentRun.id == run.id)
            )
            stored_changes = await session.execute(
                select(FileChange).where(FileChange.id == change.id)
            )
            stored_tests = await session.execute(
                select(TestRunModel).where(
                    TestRunModel.id == test_run.id,
                )
            )
            stored_tools = await session.execute(
                select(ToolCall).where(ToolCall.id == tool_call.id)
            )

            assert stored_steps.scalar_one().id == step.id
            assert stored_runs.scalar_one().id == run.id
            assert stored_changes.scalar_one().id == change.id
            assert stored_tests.scalar_one().id == test_run.id
            assert stored_tools.scalar_one().id == tool_call.id

    finally:
        await _cleanup(repository.id)
