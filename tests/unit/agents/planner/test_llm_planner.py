from uuid import uuid4

import pytest

from agents.llm.models import LLMRequest, LLMResponse
from agents.llm.provider import LLMProvider
from agents.planner.llm_planner import (
    LLMPlanner,
    PlannerGenerationError,
    build_planning_prompt,
)
from agents.planner.models import PlanningConstraint, PlanningContext
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
)


class FakeLLMProvider(LLMProvider):
    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[LLMRequest] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        return LLMResponse(
            content=self.content,
            model=self.model_name,
        )


def make_context() -> PlanningContext:
    symbol_id = uuid4()
    dependency_id = uuid4()

    return PlanningContext(
        repository_id=uuid4(),
        task_description="Update authentication token validation.",
        files=(
            ChangeContextFile(
                file_path="src/auth.py",
                reason="Contains token validation.",
                relevance_score=0.91,
            ),
        ),
        symbols=(
            ChangeContextSymbol(
                symbol_id=symbol_id,
                file_path="src/auth.py",
                name="validate_token",
                symbol_type="function",
                start_line=10,
                end_line=25,
                reason="Primary validation function.",
            ),
        ),
        dependencies=(
            ChangeContextDependency(
                source_symbol_id=dependency_id,
                target_symbol_id=symbol_id,
                relation="calls",
                depth=1,
            ),
        ),
        constraints=(
            PlanningConstraint(
                name="tests_required",
                description="Add regression coverage.",
            ),
        ),
    )


def valid_response() -> str:
    symbol_id = str(uuid4())

    return f"""
{{
  "summary": "Update authentication token validation.",
  "assumptions": [],
  "files_to_modify": [
    {{
      "file_path": "src/auth.py",
      "reason": "Contains token validation."
    }}
  ],
  "files_to_create": [],
  "symbols_to_modify": [
    {{
      "symbol_id": "{symbol_id}",
      "file_path": "src/auth.py",
      "name": "validate_token",
      "reason": "Update validation behavior."
    }}
  ],
  "implementation_steps": [
    {{
      "order": 1,
      "description": "Update token validation.",
      "step_type": "modify",
      "file_path": "src/auth.py",
      "symbol_name": "validate_token"
    }},
    {{
      "order": 2,
      "description": "Add regression tests.",
      "step_type": "test",
      "file_path": "tests/test_auth.py"
    }},
    {{
      "order": 3,
      "description": "Run validation.",
      "step_type": "validate",
      "file_path": null,
      "symbol_name": null
    }}
  ],
  "dependencies": [],
  "tests_to_add": ["Reject expired tokens."],
  "validation_commands": ["pytest tests/test_auth.py"],
  "risks": []
}}
"""


def test_build_planning_prompt_contains_context() -> None:
    prompt = build_planning_prompt(make_context())

    assert "Update authentication token validation." in prompt
    assert "src/auth.py" in prompt
    assert "validate_token" in prompt
    assert "tests_required" in prompt
    assert "RETURN ONLY" not in prompt


@pytest.mark.asyncio
async def test_generate_plan_calls_provider() -> None:
    provider = FakeLLMProvider(valid_response())
    planner = LLMPlanner(provider)

    plan = await planner.generate_plan(make_context())

    assert plan.summary == "Update authentication token validation."
    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert len(request.messages) == 2
    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"
    assert request.temperature == 0.0


@pytest.mark.asyncio
async def test_invalid_llm_output_raises_planner_error() -> None:
    provider = FakeLLMProvider("This is not JSON.")
    planner = LLMPlanner(provider)

    with pytest.raises(PlannerGenerationError, match="invalid implementation plan"):
        await planner.generate_plan(make_context())
