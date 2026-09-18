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
from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider
from agents.reviewer.llm_reviewer import LLMReviewer
from agents.reviewer.models import (
    ReviewCategory,
    ReviewDecision,
    ReviewSeverity,
)
from agents.reviewer.service import ReviewerService

REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeReviewProvider(LLMProvider):
    """Deterministic provider for the reviewer E2E test."""

    @property
    def model_name(self) -> str:
        return "fake-review-model"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        return LLMResponse(
            content="""\
{
  "decision": "request_changes",
  "summary": "The implementation contains a correctness issue.",
  "findings": [
    {
      "severity": "high",
      "category": "correctness",
      "file_path": "app.py",
      "line": 2,
      "title": "Incorrect arithmetic operation",
      "description": "The implementation subtracts b instead of adding b.",
      "recommendation": "Change the subtraction operation to addition."
    }
  ]
}
""",
            model=self.model_name,
        )


def make_context() -> ImplementationContext:
    return ImplementationContext(
        repository_id=REPOSITORY_ID,
        task_description="Implement an add function that returns a + b.",
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
        summary="Implemented the add function.",
        changes=(
            CodeChange(
                file_path="app.py",
                operation=ChangeOperation.MODIFY,
                content="""\
def add(a: int, b: int) -> int:
    return a - b
""",
                reason="Implement the requested addition function.",
            ),
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_pipeline_detects_real_correctness_issue() -> None:
    provider = FakeReviewProvider()
    reviewer = LLMReviewer(provider)
    service = ReviewerService(reviewer)

    result = await service.review(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.approved is False
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.severity == ReviewSeverity.HIGH
    assert finding.category == ReviewCategory.CORRECTNESS
    assert finding.file_path == "app.py"
    assert finding.line == 2
    assert finding.title == "Incorrect arithmetic operation"

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert request.temperature == 0.0
    assert request.max_tokens == 4096

    user_prompt = request.messages[1].content

    assert "Implement an add function that returns a + b." in user_prompt
    assert "app.py" in user_prompt
    assert "return a - b" in user_prompt
    assert "Implemented the add function." in user_prompt
