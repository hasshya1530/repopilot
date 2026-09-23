from pathlib import Path
from uuid import UUID, uuid4

import pytest

from agents.testing.models import TestResult, TestStatus
from apps.api.app.core.database import async_session_factory
from apps.api.app.models.agent_run import AgentRun, AgentRunStatus
from apps.api.app.models.repository import Repository
from apps.api.app.models.task import Task
from apps.api.app.models.task_step import AgentType, TaskStep, TaskStepStatus
from apps.api.app.models.test_run import TestRunStatus as TestRunStatusModel
from apps.api.app.services.test_artifacts import persist_test_result


async def _create_agent_run() -> tuple[UUID, AgentRun]:
    repository_id = uuid4()
    task_id = uuid4()
    task_step_id = uuid4()
    agent_run_id = uuid4()

    async with async_session_factory() as session:
        repository = Repository(
            id=repository_id,
            owner="test-owner",
            name="test-repository",
            full_name=f"test-owner/test-repository-{uuid4().hex[:8]}",
            github_repo_id=900000000 + (uuid4().int % 1000000),
            default_branch="main",
            description="Test repository",
            is_private=False,
            clone_url="https://github.com/test-owner/test-repository.git",
        )
        session.add(repository)
        await session.commit()

        task = Task(
            id=task_id,
            repository_id=repository.id,
            title="Test task",
            description="Test task description",
            status="pending",
        )
        session.add(task)
        await session.commit()

        task_step = TaskStep(
            id=task_step_id,
            task_id=task.id,
            step_number=1,
            name="Testing",
            agent_type=AgentType.TESTING,
            status=TaskStepStatus.PENDING,
        )
        session.add(task_step)
        await session.commit()

        run = AgentRun(
            id=agent_run_id,
            task_step_id=task_step.id,
            agent_type=AgentType.TESTING,
            status=AgentRunStatus.RUNNING,
            attempt_number=1,
            model_provider="test",
            model_name="test-model",
        )
        session.add(run)
        await session.commit()

        return repository.id, run


async def _delete_repository(repository_id: UUID) -> None:
    async with async_session_factory() as session:
        repository = await session.get(Repository, repository_id)

        if repository is not None:
            await session.delete(repository)
            await session.commit()


@pytest.mark.asyncio
async def test_persist_passed_test_result() -> None:
    repository_id, run = await _create_agent_run()

    try:
        result = TestResult(
            status=TestStatus.PASSED,
            command=("pytest", "tests"),
            exit_code=0,
            stdout="5 passed\n",
            stderr="",
            duration_seconds=1.25,
        )

        async with async_session_factory() as session:
            persisted = await persist_test_result(
                session,
                agent_run_id=run.id,
                result=result,
                working_directory=Path("/workspace"),
            )

            assert persisted.status == TestRunStatusModel.PASSED
            assert persisted.command == "pytest tests"
            assert persisted.exit_code == 0
            assert persisted.stdout == "5 passed\n"
            assert persisted.stderr == ""
            assert persisted.duration_ms == 1250
            assert persisted.working_directory == "/workspace"
    finally:
        await _delete_repository(repository_id)


@pytest.mark.asyncio
async def test_persist_failed_test_result() -> None:
    repository_id, run = await _create_agent_run()

    try:
        result = TestResult(
            status=TestStatus.FAILED,
            command=("pytest", "tests", "-q"),
            exit_code=1,
            stdout="1 failed\n",
            stderr="AssertionError\n",
            duration_seconds=2.5,
        )

        async with async_session_factory() as session:
            persisted = await persist_test_result(
                session,
                agent_run_id=run.id,
                result=result,
                working_directory=Path("/workspace"),
            )

            assert persisted.status == TestRunStatusModel.FAILED
            assert persisted.command == "pytest tests -q"
            assert persisted.exit_code == 1
            assert persisted.stdout == "1 failed\n"
            assert persisted.stderr == "AssertionError\n"
            assert persisted.duration_ms == 2500
    finally:
        await _delete_repository(repository_id)


@pytest.mark.asyncio
async def test_persist_error_test_result() -> None:
    repository_id, run = await _create_agent_run()

    try:
        result = TestResult(
            status=TestStatus.ERROR,
            command=("pytest", "tests"),
            exit_code=2,
            stdout="",
            stderr="ImportError\n",
            duration_seconds=0.75,
        )

        async with async_session_factory() as session:
            persisted = await persist_test_result(
                session,
                agent_run_id=run.id,
                result=result,
                working_directory=Path("/workspace"),
            )

            assert persisted.status == TestRunStatusModel.ERROR
            assert persisted.exit_code == 2
            assert persisted.stderr == "ImportError\n"
            assert persisted.duration_ms == 750
    finally:
        await _delete_repository(repository_id)


@pytest.mark.asyncio
async def test_persist_timeout_test_result() -> None:
    repository_id, run = await _create_agent_run()

    try:
        result = TestResult(
            status=TestStatus.TIMEOUT,
            command=("pytest", "tests"),
            exit_code=None,
            stdout="",
            stderr="Test execution timed out.\n",
            duration_seconds=30.75,
        )

        async with async_session_factory() as session:
            persisted = await persist_test_result(
                session,
                agent_run_id=run.id,
                result=result,
                working_directory=Path("/workspace"),
            )

            assert persisted.status == TestRunStatusModel.ERROR
            assert persisted.exit_code is None
            assert persisted.stderr == "Test execution timed out.\n"
            assert persisted.duration_ms == 30750
    finally:
        await _delete_repository(repository_id)


@pytest.mark.asyncio
async def test_persist_empty_command_test_result() -> None:
    repository_id, run = await _create_agent_run()

    try:
        result = TestResult(
            status=TestStatus.PASSED,
            command=(),
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.0,
        )

        async with async_session_factory() as session:
            persisted = await persist_test_result(
                session,
                agent_run_id=run.id,
                result=result,
                working_directory=Path("/workspace"),
            )

            assert persisted.status == TestRunStatusModel.PASSED
            assert persisted.command == ""
            assert persisted.exit_code == 0
            assert persisted.duration_ms == 0
    finally:
        await _delete_repository(repository_id)
