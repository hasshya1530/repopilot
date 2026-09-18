from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator.errors import OrchestrationExecutionError
from apps.api.app.core.database import get_db
from apps.api.app.schemas.orchestration import (
    OrchestrationStartResponse,
)

router = APIRouter(
    prefix="/tasks",
    tags=["orchestration"],
)


async def run_orchestration(
    task_id: UUID,
    session: AsyncSession,
) -> None:
    # Importing the concrete factory here keeps API wiring separate
    # from the orchestration domain.
    from apps.api.app.services.orchestration_factory import (
        create_orchestration_service,
    )

    service = create_orchestration_service(session)

    try:
        await service.run(task_id)
    except OrchestrationExecutionError:
        # The service persists failure state. Background execution
        # must not turn an already-accepted request into an HTTP error.
        return


@router.post(
    "/{task_id}/run",
    response_model=OrchestrationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_orchestration(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrchestrationStartResponse:
    from apps.api.app.services.task import get_task

    task = await get_task(session, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} was not found.",
        )

    background_tasks.add_task(
        run_orchestration,
        task_id,
        session,
    )

    return OrchestrationStartResponse(
        task_id=task_id,
        status=task.status,
        message="Orchestration started.",
    )
