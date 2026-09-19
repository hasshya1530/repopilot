from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.schemas.background_job import BackgroundJobResponse
from apps.api.app.services.background_job import get_background_job

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
)


@router.get(
    "/{job_id}",
    response_model=BackgroundJobResponse,
)
async def get_job_endpoint(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundJobResponse:
    job = await get_background_job(
        session,
        job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return BackgroundJobResponse.model_validate(job)
