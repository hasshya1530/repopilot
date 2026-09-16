from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.repository import Repository
from apps.api.app.schemas.repository import RepositoryCreate


async def create_repository(
    session: AsyncSession,
    data: RepositoryCreate,
) -> Repository:
    existing = await session.execute(
        select(Repository).where(Repository.github_repo_id == data.github_repo_id)
    )

    repository = existing.scalar_one_or_none()

    if repository is not None:
        raise ValueError("Repository already exists")

    repository = Repository(
        owner=data.owner,
        name=data.name,
        full_name=data.full_name,
        github_repo_id=data.github_repo_id,
        default_branch=data.default_branch,
        description=data.description,
        is_private=data.is_private,
        clone_url=data.clone_url,
    )

    session.add(repository)
    await session.commit()
    await session.refresh(repository)

    return repository


async def get_repository(
    session: AsyncSession,
    repository_id: UUID,
) -> Repository | None:
    return await session.get(Repository, repository_id)


async def list_repositories(
    session: AsyncSession,
) -> list[Repository]:
    result = await session.execute(select(Repository).order_by(Repository.created_at.desc()))

    return list(result.scalars().all())
