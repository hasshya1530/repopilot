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

OPENROUTER_MODEL = "nvidia/nemotron-3.5-lightning:free"


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
@pytest.mark.openrouter
@pytest.mark.asyncio
async def test_openrouter_reviews_real_incorrect_implementation() -> None:
    settings = get_settings()

    if not settings.openrouter_api_key:
        pytest.skip("OpenRouter review E2E requires OPENROUTER_API_KEY.")

    provider = create_llm_provider(
        provider="openrouter",
        model_name=OPENROUTER_MODEL,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
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
