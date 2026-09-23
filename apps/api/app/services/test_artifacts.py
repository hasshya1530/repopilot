from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.testing.models import TestResult, TestStatus
from apps.api.app.models.test_run import TestRun, TestRunStatus
from apps.api.app.services.artifacts import create_test_run


def _to_test_run_status(status: TestStatus) -> TestRunStatus:
    mapping = {
        TestStatus.PASSED: TestRunStatus.PASSED,
        TestStatus.FAILED: TestRunStatus.FAILED,
        TestStatus.ERROR: TestRunStatus.ERROR,
        # The persistence model does not have a dedicated TIMEOUT status.
        # Preserve timeout semantics as an execution error at the DB layer.
        TestStatus.TIMEOUT: TestRunStatus.ERROR,
    }
    return mapping[status]


def _duration_ms(duration_seconds: float) -> int:
    return max(0, round(duration_seconds * 1000))


async def persist_test_result(
    session: AsyncSession,
    *,
    agent_run_id: UUID,
    result: TestResult,
    working_directory: Path,
) -> TestRun:
    return await create_test_run(
        session,
        agent_run_id=agent_run_id,
        command=" ".join(result.command),
        status=_to_test_run_status(result.status),
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_ms=_duration_ms(result.duration_seconds),
        working_directory=str(working_directory),
    )
