from uuid import UUID, uuid4

import pytest

from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextDependency,
    ImplementationContextFile,
    ImplementationContextSymbol,
)
from agents.implementer.errors import ImplementationGenerationError
from agents.implementer.llm_implementer import LLMImplementer
from agents.implementer.models import (
    ChangeOperation,
    ImplementationResult,
)
from agents.implementer.validator import (
    ImplementationValidationCode,
    ImplementationValidationIssue,
    ImplementationValidationResult,
    ImplementationValidator,
)
from agents.llm.models import LLMResponse
from agents.planner.plan_models import (
    ImplementationPlan,
    PlannedFile,
)


def make_context(repository_id: UUID) -> ImplementationContext:
    source_symbol_id = uuid4()
    target_symbol_id = uuid4()

    return ImplementationContext(
        repository_id=repository_id,
        task_description="Update the service.",
        files=(
            ImplementationContextFile(
                file_path="src/service.py",
                content="def service():\n    return 1\n",
                reason="Target service.",
            ),
        ),
        symbols=(
            ImplementationContextSymbol(
                symbol_id=source_symbol_id,
                file_path="src/service.py",
                name="service",
                symbol_type="function",
                start_line=1,
                end_line=2,
                content="def service():\n    return 1",
                reason="Target function.",
            ),
        ),
        dependencies=(
            ImplementationContextDependency(
                source_symbol_id=source_symbol_id,
                target_symbol_id=target_symbol_id,
                relation="calls",
                depth=1,
            ),
        ),
    )


def make_plan() -> ImplementationPlan:
    return ImplementationPlan(
        summary="Update service.",
        assumptions=(),
        files_to_modify=(
            PlannedFile(
                file_path="src/service.py",
                reason="Update the service implementation.",
            ),
        ),
        files_to_create=(),
        symbols_to_modify=(),
        implementation_steps=(),
        dependencies=(),
        tests_to_add=(),
        validation_commands=(),
        risks=(),
    )


class RecordingProvider:
    def __init__(self, content: str) -> None:
        self.content = content
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return LLMResponse(
            content=self.content,
            model="test-model",
        )


class AlwaysInvalidValidator(ImplementationValidator):
    def validate(
        self,
        *,
        plan,
        implementation,
    ) -> ImplementationValidationResult:
        return ImplementationValidationResult(
            valid=False,
            issues=(
                ImplementationValidationIssue(
                    code=ImplementationValidationCode.UNPLANNED_FILE,
                    file_path="unexpected.py",
                    message="Unexpected implementation change.",
                ),
            ),
        )


@pytest.mark.asyncio
async def test_implementer_returns_validated_implementation() -> None:
    provider = RecordingProvider(
        """
        {
          "summary": "Updated the service.",
          "changes": [
            {
              "file_path": "src/service.py",
              "operation": "modify",
              "content": "def service():\\n    return 2\\n",
              "reason": "Update the service behavior."
            }
          ]
        }
        """
    )

    implementer = LLMImplementer(provider)

    result = await implementer.implement(
        make_context(uuid4()),
        make_plan(),
    )

    assert isinstance(result, ImplementationResult)
    assert result.summary == "Updated the service."
    assert len(result.changes) == 1
    assert result.changes[0].file_path == "src/service.py"
    assert result.changes[0].operation == ChangeOperation.MODIFY
    assert len(provider.requests) == 1


@pytest.mark.asyncio
async def test_implementer_rejects_invalid_json() -> None:
    provider = RecordingProvider("not valid json")

    implementer = LLMImplementer(provider)

    with pytest.raises(
        ImplementationGenerationError,
        match="invalid implementation result",
    ):
        await implementer.implement(
            make_context(uuid4()),
            make_plan(),
        )


@pytest.mark.asyncio
async def test_implementer_rejects_changes_that_violate_plan() -> None:
    provider = RecordingProvider(
        """
        {
          "summary": "Made an unrelated change.",
          "changes": [
            {
              "file_path": "src/unplanned.py",
              "operation": "modify",
              "content": "unexpected = True\\n",
              "reason": "This was not requested."
            }
          ]
        }
        """
    )

    implementer = LLMImplementer(provider)

    with pytest.raises(
        ImplementationGenerationError,
        match="violated the approved implementation plan",
    ):
        await implementer.implement(
            make_context(uuid4()),
            make_plan(),
        )


@pytest.mark.asyncio
async def test_implementer_uses_injected_validator() -> None:
    provider = RecordingProvider(
        """
        {
          "summary": "Updated the service.",
          "changes": [
            {
              "file_path": "src/service.py",
              "operation": "modify",
              "content": "def service():\\n    return 2\\n",
              "reason": "Update the service behavior."
            }
          ]
        }
        """
    )

    implementer = LLMImplementer(
        provider,
        validator=AlwaysInvalidValidator(),
    )

    with pytest.raises(
        ImplementationGenerationError,
        match="violated the approved implementation plan",
    ):
        await implementer.implement(
            make_context(uuid4()),
            make_plan(),
        )
