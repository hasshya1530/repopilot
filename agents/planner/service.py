from typing import Protocol
from uuid import UUID

from agents.planner.errors import PlanningContextError
from agents.planner.models import PlanningConstraint, PlanningContext
from ingestion.change_context.models import RepositoryChangeContext


class ChangeContextServiceProtocol(Protocol):
    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> RepositoryChangeContext:
        ...


class PlanningContextService:
    """Convert repository change context into planner-ready context."""

    def __init__(
        self,
        change_context_service: ChangeContextServiceProtocol,
    ) -> None:
        self._change_context_service = change_context_service

    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> PlanningContext:
        """Build the structured context consumed by the planner."""

        if not task_description.strip():
            raise PlanningContextError(
                "task_description must not be empty"
            )

        try:
            change_context = await self._change_context_service.build(
                repository_id=repository_id,
                task_description=task_description,
                symbol_id=symbol_id,
                context_limit=context_limit,
                max_depth=max_depth,
            )
        except Exception as exc:
            raise PlanningContextError(
                "Failed to build planning context"
            ) from exc

        constraints = self._build_constraints(change_context)

        return PlanningContext(
            repository_id=change_context.repository_id,
            task_description=change_context.task_description,
            files=change_context.files,
            symbols=change_context.symbols,
            dependencies=change_context.dependencies,
            constraints=constraints,
            change_context=change_context,
            repository_context=change_context.repository_context,
        )

    @staticmethod
    def _build_constraints(
        context: RepositoryChangeContext,
    ) -> tuple[PlanningConstraint, ...]:
        """Derive deterministic planning constraints from repository context."""

        constraints: list[PlanningConstraint] = []

        if context.dependencies:
            constraints.append(
                PlanningConstraint(
                    name="dependency_awareness",
                    description=(
                        "The implementation plan must account for the "
                        "identified symbol dependencies."
                    ),
                )
            )

        if context.files:
            constraints.append(
                PlanningConstraint(
                    name="relevant_files",
                    description=(
                        "Prefer modifying the identified relevant files "
                        "unless additional files are justified."
                    ),
                )
            )

        if context.symbols:
            constraints.append(
                PlanningConstraint(
                    name="symbol_scope",
                    description=(
                        "Preserve the behavior and contracts of relevant "
                        "repository symbols unless the task requires a change."
                    ),
                )
            )

        constraints.append(
            PlanningConstraint(
                name="tests_required",
                description=(
                    "The implementation plan must include appropriate "
                    "validation and testing."
                ),
            )
        )

        if context.repository_context is not None:
            constraints.append(
                PlanningConstraint(
                    name="repository_evidence",
                    description=(
                        "Base implementation decisions on the retrieved "
                        "repository source evidence and do not invent "
                        "unsupported repository behavior."
                    ),
                )
            )

        return tuple(constraints)
