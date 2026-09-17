from typing import Protocol
from uuid import UUID

from agents.planner.llm_planner import LLMPlanner
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan


class PlanningContextServiceProtocol(Protocol):
    """Interface required to build planning context."""

    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> PlanningContext:
        """Build planning context for a repository task."""
        ...


class PlannerOrchestrator:
    """Coordinate repository context generation and LLM-based planning."""

    def __init__(
        self,
        context_service: PlanningContextServiceProtocol,
        planner: LLMPlanner,
    ) -> None:
        self._context_service = context_service
        self._planner = planner

    async def plan(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
        max_tokens: int = 4096,
    ) -> ImplementationPlan:
        context = await self._context_service.build(
            repository_id=repository_id,
            task_description=task_description,
            symbol_id=symbol_id,
            context_limit=context_limit,
            max_depth=max_depth,
        )

        return await self._planner.generate_plan(
            context,
            max_tokens=max_tokens,
        )
