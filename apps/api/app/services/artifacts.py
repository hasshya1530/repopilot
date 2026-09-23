from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.agent_run import AgentRun, AgentRunStatus
from apps.api.app.models.file_change import FileChange, FileChangeOperation
from apps.api.app.models.task_step import (
    AgentType,
    TaskStep,
    TaskStepStatus,
)
from apps.api.app.models.test_run import TestRun, TestRunStatus
from apps.api.app.models.tool_call import ToolCall, ToolCallStatus


async def create_task_step(
    session: AsyncSession,
    *,
    task_id: UUID,
    step_number: int,
    name: str,
    agent_type: AgentType,
    input_data: str | None = None,
) -> TaskStep:
    step = TaskStep(
        task_id=task_id,
        step_number=step_number,
        name=name,
        agent_type=agent_type,
        status=TaskStepStatus.RUNNING,
        input_data=input_data,
    )

    session.add(step)
    await session.commit()
    await session.refresh(step)

    return step


async def get_task_step(
    session: AsyncSession,
    step_id: UUID,
) -> TaskStep | None:
    result = await session.execute(
        select(TaskStep).where(TaskStep.id == step_id)
    )

    return result.scalar_one_or_none()


async def complete_task_step(
    session: AsyncSession,
    step_id: UUID,
    *,
    output_data: str | None = None,
) -> TaskStep | None:
    step = await get_task_step(session, step_id)

    if step is None:
        return None

    step.status = TaskStepStatus.COMPLETED
    step.output_data = output_data

    await session.commit()
    await session.refresh(step)

    return step


async def fail_task_step(
    session: AsyncSession,
    step_id: UUID,
    *,
    error_message: str,
) -> TaskStep | None:
    step = await get_task_step(session, step_id)

    if step is None:
        return None

    step.status = TaskStepStatus.FAILED
    step.error_message = error_message

    await session.commit()
    await session.refresh(step)

    return step


async def create_agent_run(
    session: AsyncSession,
    *,
    task_step_id: UUID,
    agent_type: AgentType,
    attempt_number: int = 1,
    model_provider: str | None = None,
    model_name: str | None = None,
    input_data: str | None = None,
) -> AgentRun:
    run = AgentRun(
        task_step_id=task_step_id,
        agent_type=agent_type.value,
        status=AgentRunStatus.RUNNING,
        attempt_number=attempt_number,
        model_provider=model_provider,
        model_name=model_name,
        input_data=input_data,
    )

    session.add(run)
    await session.commit()
    await session.refresh(run)

    return run


async def complete_agent_run(
    session: AsyncSession,
    run_id: UUID,
    *,
    output_data: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> AgentRun | None:
    run = await session.get(AgentRun, run_id)

    if run is None:
        return None

    run.status = AgentRunStatus.COMPLETED
    run.output_data = output_data
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens

    await session.commit()
    await session.refresh(run)

    return run


async def fail_agent_run(
    session: AsyncSession,
    run_id: UUID,
    *,
    error_message: str,
) -> AgentRun | None:
    run = await session.get(AgentRun, run_id)

    if run is None:
        return None

    run.status = AgentRunStatus.FAILED
    run.error_message = error_message

    await session.commit()
    await session.refresh(run)

    return run


async def create_file_change(
    session: AsyncSession,
    *,
    agent_run_id: UUID,
    file_path: str,
    operation: FileChangeOperation,
    before_content: str | None = None,
    after_content: str | None = None,
    diff: str | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
    line_additions: int = 0,
    line_deletions: int = 0,
) -> FileChange:
    change = FileChange(
        agent_run_id=agent_run_id,
        file_path=file_path,
        operation=operation,
        before_content=before_content,
        after_content=after_content,
        diff=diff,
        before_hash=before_hash,
        after_hash=after_hash,
        line_additions=line_additions,
        line_deletions=line_deletions,
    )

    session.add(change)
    await session.commit()
    await session.refresh(change)

    return change


async def create_test_run(
    session: AsyncSession,
    *,
    agent_run_id: UUID,
    command: str,
    status: TestRunStatus = TestRunStatus.RUNNING,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    duration_ms: int | None = None,
    working_directory: str | None = None,
) -> TestRun:
    test_run = TestRun(
        agent_run_id=agent_run_id,
        command=command,
        status=status,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        working_directory=working_directory,
    )

    session.add(test_run)
    await session.commit()
    await session.refresh(test_run)

    return test_run


async def complete_test_run(
    session: AsyncSession,
    test_run_id: UUID,
    *,
    status: TestRunStatus,
    exit_code: int | None,
    stdout: str | None,
    stderr: str | None,
    duration_ms: int | None,
) -> TestRun | None:
    test_run = await session.get(TestRun, test_run_id)

    if test_run is None:
        return None

    test_run.status = status
    test_run.exit_code = exit_code
    test_run.stdout = stdout
    test_run.stderr = stderr
    test_run.duration_ms = duration_ms

    await session.commit()
    await session.refresh(test_run)

    return test_run


async def create_tool_call(
    session: AsyncSession,
    *,
    agent_run_id: UUID,
    tool_name: str,
    sequence_number: int,
    tool_server: str | None = None,
    input_data: str | None = None,
) -> ToolCall:
    tool_call = ToolCall(
        agent_run_id=agent_run_id,
        tool_name=tool_name,
        tool_server=tool_server,
        status=ToolCallStatus.RUNNING,
        sequence_number=sequence_number,
        input_data=input_data,
    )

    session.add(tool_call)
    await session.commit()
    await session.refresh(tool_call)

    return tool_call


async def complete_tool_call(
    session: AsyncSession,
    tool_call_id: UUID,
    *,
    output_data: str | None = None,
    duration_ms: int | None = None,
) -> ToolCall | None:
    tool_call = await session.get(ToolCall, tool_call_id)

    if tool_call is None:
        return None

    tool_call.status = ToolCallStatus.COMPLETED
    tool_call.output_data = output_data
    tool_call.duration_ms = duration_ms

    await session.commit()
    await session.refresh(tool_call)

    return tool_call


async def fail_tool_call(
    session: AsyncSession,
    tool_call_id: UUID,
    *,
    error_message: str,
    duration_ms: int | None = None,
) -> ToolCall | None:
    tool_call = await session.get(ToolCall, tool_call_id)

    if tool_call is None:
        return None

    tool_call.status = ToolCallStatus.FAILED
    tool_call.error_message = error_message
    tool_call.duration_ms = duration_ms

    await session.commit()
    await session.refresh(tool_call)

    return tool_call
