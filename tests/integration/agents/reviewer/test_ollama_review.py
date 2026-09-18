from uuid import UUID

import pytest

from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextFile,
)
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.llm.factory import create_llm_provider
from agents.reviewer.llm_reviewer import LLMReviewer
from agents.reviewer.models import ReviewCategory, ReviewDecision
from agents.reviewer.service import ReviewerService
from apps.api.app.core.config import get_settings

REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000001")


def make_context() -> ImplementationContext:
    return ImplementationContext(
        repository_id=REPOSITORY_ID,
        task_description=(
            "Fix the add function so that it returns the sum of a and b."
        ),
        files=(
            ImplementationContextFile(
                file_path="app.py",
                content="""\
def add(a: int, b: int) -> int:
    return a - b
""",
                reason="Target implementation file.",
            ),
        ),
        symbols=(),
        dependencies=(),
    )


def make_implementation() -> ImplementationResult:
    return ImplementationResult(
        summary="Implemented the requested add function.",
        changes=(
            CodeChange(
                file_path="app.py",
                operation=ChangeOperation.MODIFY,
                content="""\
def add(a: int, b: int) -> int:
    return a - b
""",
                reason="Implement addition.",
            ),
        ),
    )


@pytest.mark.integration
@pytest.mark.ollama
@pytest.mark.asyncio
async def test_ollama_reviews_real_incorrect_implementation() -> None:
    settings = get_settings()

    if settings.model_provider.lower() != "ollama":
        pytest.skip("Ollama review E2E requires MODEL_PROVIDER=ollama.")

    if settings.model_name != "qwen2.5-coder:3b":
        pytest.skip(
            "This E2E test expects MODEL_NAME=qwen2.5-coder:3b."
        )

    provider = create_llm_provider(
        provider="ollama",
        model_name=settings.model_name,
        ollama_base_url=settings.ollama_base_url,
    )

    reviewer = LLMReviewer(
        provider,
        temperature=0.0,
        max_tokens=4096,
    )
    service = ReviewerService(reviewer)

    result = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.approved is False
    assert result.findings

    assert any(
        finding.category == ReviewCategory.CORRECTNESS
        for finding in result.findings
    )

    assert any(
        finding.file_path == "app.py"
        for finding in result.findings
    )
