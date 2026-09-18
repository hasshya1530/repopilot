from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.planner.models import PlanningContext
from agents.planner.service import PlanningContextService
from apps.api.app.core.config import Settings
from apps.api.app.services.repository_intelligence import (
    create_change_context_service,
)


class RepositoryAwarePlanningContextBuilder:
    """Build planning context from a prepared repository checkout."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
    ) -> None:
        self._session = session
        self._settings = settings

    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        repository_path: Path,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> PlanningContext:
        change_context_service = await create_change_context_service(
            session=self._session,
            settings=self._settings,
            repository_id=repository_id,
            repository_path=repository_path,
            task_description=task_description,
            context_limit=context_limit,
            graph_limit=context_limit,
        )

        planning_context_service = PlanningContextService(
            change_context_service=change_context_service,
        )

        return await planning_context_service.build(
            repository_id=repository_id,
            task_description=task_description,
            symbol_id=symbol_id,
            context_limit=context_limit,
            max_depth=max_depth,
        )
