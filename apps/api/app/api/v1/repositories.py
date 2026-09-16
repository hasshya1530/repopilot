from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
)
from apps.api.app.services.repository import (
    create_repository,
    get_repository,
    list_repositories,
)

router = APIRouter(
    prefix="/repositories",
    tags=["repositories"],
)


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository_endpoint(
    data: RepositoryCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryResponse:
    try:
        repository = await create_repository(session, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RepositoryResponse.model_validate(repository)


@router.get(
    "",
    response_model=list[RepositoryResponse],
)
async def list_repositories_endpoint(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RepositoryResponse]:
    repositories = await list_repositories(session)

    return [RepositoryResponse.model_validate(repository) for repository in repositories]


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
)
async def get_repository_endpoint(
    repository_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryResponse:
    repository = await get_repository(session, repository_id)

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return RepositoryResponse.model_validate(repository)
