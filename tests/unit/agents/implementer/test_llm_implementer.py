import json
from uuid import UUID, uuid4

import pytest

from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextDependency,
    ImplementationContextFile,
    ImplementationContextSymbol,
)
from agents.implementer.llm_implementer import LLMImplementer
from agents.implementer.models import ChangeOperation
from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider
from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlannedSymbol,
    PlanStepType,
)


class FakeLLMProvider(LLMProvider):
    """Deterministic LLM provider for unit tests."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.requests: list[LLMRequest] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        return LLMResponse(
            content=self._response,
            model=self.model_name,
        )


def make_context(repository_id: UUID) -> ImplementationContext:
    symbol_id = uuid4()

    return ImplementationContext(
        repository_id=repository_id,
        task_description="Improve authentication token validation.",
        files=(
            ImplementationContextFile(
                file_path="auth.py",
                content=(
                    'def validate_token(token: str) -> bool:\n'
                    '    return token == "valid"\n'
                ),
                reason="Authentication logic is relevant.",
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
                    'def validate_token(token: str) -> bool:\n'
                    '    return token == "valid"'
                ),
                reason="Target validation function.",
            ),
        ),
        dependencies=(
            ImplementationContextDependency(
                source_symbol_id=symbol_id,
                target_symbol_id=symbol_id,
                relation="calls",
                depth=1,
            ),
        ),
    )


def make_plan() -> ImplementationPlan:
    symbol_id = uuid4()

    return ImplementationPlan(
        summary="Improve authentication validation.",
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="auth.py",
                reason="Modify token validation.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(
            PlannedSymbol(
                symbol_id=symbol_id,
                file_path="auth.py",
                name="validate_token",
                reason="Improve token validation.",
            ),
        ),
        implementation_steps=(
            ImplementationStep(
                order=1,
                description="Modify token validation.",
                step_type=PlanStepType.MODIFY,
                file_path="auth.py",
                symbol_name="validate_token",
            ),
        ),
        dependencies=(),
        tests_to_add=("Add invalid token regression tests.",),
        validation_commands=("pytest",),
        risks=(),
    )


@pytest.mark.asyncio
async def test_implement_generates_structured_changes() -> None:
    response = json.dumps(
        {
            "summary": "Improve authentication validation.",
            "changes": [
                {
                    "file_path": "auth.py",
                    "operation": "modify",
                    "content": (
                        'def validate_token(token: str) -> bool:\n'
                        '    return token.strip() == "valid"\n'
                    ),
                    "reason": (
                        "Reject tokens with invalid surrounding whitespace."
                    ),
                }
            ],
        }
    )

    provider = FakeLLMProvider(response)

    implementer = LLMImplementer(provider)

    repository_id = uuid4()

    result = await implementer.implement(
        context=make_context(repository_id),
        plan=make_plan(),
    )

    assert result.summary == "Improve authentication validation."
    assert len(result.changes) == 1

    change = result.changes[0]

    assert change.file_path == "auth.py"
    assert change.operation is ChangeOperation.MODIFY
    assert "validate_token" in change.content
    assert "strip()" in change.content

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert len(request.messages) == 2
    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"

    user_prompt = request.messages[1].content

    assert "Improve authentication token validation." in user_prompt
    assert "auth.py" in user_prompt
    assert "validate_token" in user_prompt
    assert "Add invalid token regression tests." in user_prompt


@pytest.mark.asyncio
async def test_implement_rejects_invalid_llm_output() -> None:
    response = json.dumps(
        {
            "summary": "Invalid implementation.",
            "changes": [],
        }
    )

    provider = FakeLLMProvider(response)

    implementer = LLMImplementer(provider)

    with pytest.raises(
        Exception,
        match="invalid implementation result",
    ):
        await implementer.implement(
            context=make_context(uuid4()),
            plan=make_plan(),
        )
