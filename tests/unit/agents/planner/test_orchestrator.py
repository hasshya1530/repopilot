from uuid import uuid4

import pytest

from agents.planner.models import PlanningContext
from agents.planner.orchestrator import PlannerOrchestrator
from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlannedSymbol,
    PlanStepType,
)
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
)


class FakeContextService:
    def __init__(self, context: PlanningContext) -> None:
        self.context = context
        self.calls: list[dict[str, object]] = []

    async def build(
        self,
        repository_id,
        task_description,
        symbol_id=None,
        *,
        context_limit=20,
        max_depth=2,
    ):
        self.calls.append(
            {
                "repository_id": repository_id,
                "task_description": task_description,
                "symbol_id": symbol_id,
                "context_limit": context_limit,
                "max_depth": max_depth,
            }
        )
        return self.context


class FakePlanner:
    def __init__(self, plan: ImplementationPlan) -> None:
        self.plan = plan
        self.calls: list[dict[str, object]] = []

    async def generate_plan(
        self,
        context: PlanningContext,
        *,
        max_tokens: int = 4096,
    ) -> ImplementationPlan:
        self.calls.append(
            {
                "context": context,
                "max_tokens": max_tokens,
            }
        )
        return self.plan


def make_context() -> PlanningContext:
    symbol_id = uuid4()

    return PlanningContext(
        repository_id=uuid4(),
        task_description="Update authentication.",
        files=(
            ChangeContextFile(
                file_path="src/auth.py",
                reason="Authentication logic.",
                relevance_score=0.9,
            ),
        ),
        symbols=(
            ChangeContextSymbol(
                symbol_id=symbol_id,
                file_path="src/auth.py",
                name="validate_token",
                symbol_type="function",
                start_line=10,
                end_line=20,
                reason="Primary validation function.",
            ),
        ),
        dependencies=(
            ChangeContextDependency(
                source_symbol_id=uuid4(),
                target_symbol_id=symbol_id,
                relation="calls",
                depth=1,
            ),
        ),
        constraints=(),
    )


def make_plan() -> ImplementationPlan:
    return ImplementationPlan(
        summary="Update authentication.",
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="src/auth.py",
                reason="Authentication logic.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(
            PlannedSymbol(
                symbol_id=uuid4(),
                file_path="src/auth.py",
                name="validate_token",
                reason="Update validation.",
            ),
        ),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Update token validation.",
                step_type=PlanStepType.MODIFY,
                file_path="src/auth.py",
                symbol_name="validate_token",
            ),
            ImplementationStep(
                order=2,
                description="Add regression tests.",
                step_type=PlanStepType.TEST,
                file_path="tests/test_auth.py",
            ),
            ImplementationStep(
                order=3,
                description="Run tests.",
                step_type=PlanStepType.VALIDATE,
            ),
        ),
        dependencies=(),
        tests_to_add=("Reject expired tokens.",),
        validation_commands=("pytest tests/test_auth.py",),
        risks=(),
    )


@pytest.mark.asyncio
async def test_orchestrator_builds_context_then_generates_plan() -> None:
    context = make_context()
    plan = make_plan()

    context_service = FakeContextService(context)
    planner = FakePlanner(plan)

    orchestrator = PlannerOrchestrator(
        context_service=context_service,
        planner=planner,  # type: ignore[arg-type]
    )

    repository_id = uuid4()
    symbol_id = uuid4()

    result = await orchestrator.plan(
        repository_id=repository_id,
        task_description="Update authentication.",
        symbol_id=symbol_id,
        context_limit=10,
        max_depth=3,
        max_tokens=2048,
    )

    assert result == plan

    assert len(context_service.calls) == 1
    assert context_service.calls[0] == {
        "repository_id": repository_id,
        "task_description": "Update authentication.",
        "symbol_id": symbol_id,
        "context_limit": 10,
        "max_depth": 3,
    }

    assert len(planner.calls) == 1
    assert planner.calls[0]["context"] == context
    assert planner.calls[0]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_orchestrator_uses_default_options() -> None:
    context = make_context()
    plan = make_plan()

    context_service = FakeContextService(context)
    planner = FakePlanner(plan)

    orchestrator = PlannerOrchestrator(
        context_service=context_service,
        planner=planner,  # type: ignore[arg-type]
    )

    result = await orchestrator.plan(
        repository_id=uuid4(),
        task_description="Update authentication.",
    )

    assert result == plan
    assert context_service.calls[0]["context_limit"] == 20
    assert context_service.calls[0]["max_depth"] == 2
    assert planner.calls[0]["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_orchestrator_passes_none_symbol_id() -> None:
    context = make_context()
    plan = make_plan()

    context_service = FakeContextService(context)
    planner = FakePlanner(plan)

    orchestrator = PlannerOrchestrator(
        context_service=context_service,
        planner=planner,  # type: ignore[arg-type]
    )

    await orchestrator.plan(
        repository_id=uuid4(),
        task_description="Update authentication.",
    )

    assert context_service.calls[0]["symbol_id"] is None
