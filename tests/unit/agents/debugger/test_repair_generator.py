from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from agents.debugger.analyzer import FailureAnalysis
from agents.debugger.errors import RepairGenerationError
from agents.debugger.repair_generator import RepairGenerator
from agents.implementer.context.models import ImplementationContext
from agents.llm.models import LLMResponse


def make_analysis() -> FailureAnalysis:
    return FailureAnalysis(
        failure_type="assertion_error",
        summary="Tests failed with exit code 1.",
        details="AssertionError: expected 200 but got 401",
        test_command=("pytest", "-q"),
    )


def make_context() -> ImplementationContext:
    return ImplementationContext(
        repository_id=UUID("00000000-0000-0000-0000-000000000001"),
        task_description="Fix the authentication failure.",
        files=(),
        symbols=(),
        dependencies=(),
    )


def make_provider(response_content: str) -> AsyncMock:
    provider = AsyncMock()

    provider.generate.return_value = LLMResponse(
        content=response_content,
        model="test-model",
    )

    return provider


@pytest.mark.asyncio
async def test_generate_returns_repair_proposal() -> None:
    provider = make_provider(
        """
        {
          "summary": "Fix the authentication status handling.",
          "changes": [
            {
              "file_path": "auth/service.py",
              "operation": "modify",
              "content": "def login():\\n    return 200\\n",
              "reason": "Return the expected successful status."
            }
          ]
        }
        """
    )

    generator = RepairGenerator(provider)

    proposal = await generator.generate(
        make_analysis(),
        make_context(),
    )

    assert proposal.diagnosis == "Fix the authentication status handling."
    assert len(proposal.changes) == 1
    assert proposal.changes[0].file_path == "auth/service.py"
    assert proposal.changes[0].operation.value == "modify"
    assert proposal.changes[0].reason == "Return the expected successful status."

    provider.generate.assert_awaited_once()

    request = provider.generate.await_args.args[0]

    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"
    assert "assertion_error" in request.messages[1].content
    assert "Fix the authentication failure." in request.messages[1].content


@pytest.mark.asyncio
async def test_generate_rejects_successful_test_result() -> None:
    provider = AsyncMock()
    generator = RepairGenerator(provider)

    analysis = FailureAnalysis(
        failure_type="none",
        summary="Tests passed successfully.",
        details="No failure requires debugging.",
        test_command=("pytest", "-q"),
    )

    with pytest.raises(
        RepairGenerationError,
        match="Cannot generate a repair",
    ):
        await generator.generate(
            analysis,
            make_context(),
        )

    provider.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_wraps_llm_failure() -> None:
    provider = AsyncMock()
    provider.generate.side_effect = RuntimeError("LLM unavailable")

    generator = RepairGenerator(provider)

    with pytest.raises(
        RepairGenerationError,
        match="LLM repair generation failed",
    ):
        await generator.generate(
            make_analysis(),
            make_context(),
        )


@pytest.mark.asyncio
async def test_generate_rejects_invalid_llm_response() -> None:
    provider = make_provider(
        """
        {
          "summary": "This is invalid because changes are missing."
        }
        """
    )

    generator = RepairGenerator(provider)

    with pytest.raises(
        RepairGenerationError,
        match="invalid repair result",
    ):
        await generator.generate(
            make_analysis(),
            make_context(),
        )
