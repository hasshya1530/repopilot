from uuid import uuid4

import pytest

from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextFile,
    ImplementationContextSymbol,
)
from agents.implementer.llm_implementer import LLMImplementer
from agents.implementer.models import ChangeOperation
from agents.llm.factory import create_llm_provider
from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlanStepType,
)
from apps.api.app.core.config import get_settings


def make_context() -> ImplementationContext:
    repository_id = uuid4()
    symbol_id = uuid4()

    return ImplementationContext(
        repository_id=repository_id,
        task_description="Add token validation to the authentication module.",
        files=(
            ImplementationContextFile(
                file_path="auth.py",
                reason="The authentication logic must be updated.",
                content=(
                    "def validate_token(token: str) -> bool:\n"
                    "    return bool(token)\n"
                ),
            ),
        ),
        symbols=(
            ImplementationContextSymbol(
                symbol_id=symbol_id,
                file_path="auth.py",
                name="validate_token",
                symbol_type="function",
                start_line=1,
                end_line=2,
                content=(
                    "def validate_token(token: str) -> bool:\n"
                    "    return bool(token)\n"
                ),
                reason="This function is the target of the requested change.",
            ),
        ),
        dependencies=(),
    )


def make_plan() -> ImplementationPlan:
    return ImplementationPlan(
        summary="Improve authentication token validation.",
        assumptions=(
            "The existing validate_token function should remain the public entry point.",
        ),
        files_to_modify=(
            PlannedFile(
                file_path="auth.py",
                reason="Update token validation logic.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description=(
                    "Update validate_token to reject empty or "
                    "whitespace-only tokens."
                ),
                step_type=PlanStepType.MODIFY,
                file_path="auth.py",
                symbol_name="validate_token",
            ),
            ImplementationStep(
                order=2,
                description="Validate the updated authentication behavior.",
                step_type=PlanStepType.TEST,
            ),
        ),
        dependencies=(),
        tests_to_add=(
            "Add coverage for empty and whitespace-only tokens.",
        ),
        validation_commands=("python -m pytest",),
        risks=(
            "Existing callers may depend on the current boolean behavior.",
        ),
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ollama_implementer_generates_structured_changes() -> None:
    settings = get_settings()

    if settings.model_provider != "ollama":
        pytest.skip("Ollama integration test requires MODEL_PROVIDER=ollama.")

    provider = create_llm_provider(provider=settings.model_provider, model_name=settings.model_name)
    implementer = LLMImplementer(provider)

    result = await implementer.implement(
        context=make_context(),
        plan=make_plan(),
        max_tokens=2048,
    )

    assert result.summary.strip()
    assert result.changes

    for change in result.changes:
        assert change.file_path
        assert not change.file_path.startswith("/")
        assert ".." not in change.file_path.split("/")
        assert change.reason.strip()

        if change.operation == ChangeOperation.DELETE:
            assert change.content == ""
        else:
            assert change.content.strip()

    assert any(
        change.file_path == "auth.py"
        for change in result.changes
    )
