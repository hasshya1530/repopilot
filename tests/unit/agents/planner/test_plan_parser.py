from uuid import uuid4

import pytest

from agents.planner.plan_models import PlanStepType
from agents.planner.plan_parser import (
    PlanParsingError,
    parse_implementation_plan,
)


def valid_payload() -> str:
    symbol_id = str(uuid4())

    return f"""
{{
  "summary": "Update authentication.",
  "assumptions": ["Existing middleware remains unchanged."],
  "files_to_modify": [
    {{
      "file_path": "src/auth.py",
      "reason": "Contains authentication logic."
    }}
  ],
  "files_to_create": [],
  "symbols_to_modify": [
    {{
      "symbol_id": "{symbol_id}",
      "file_path": "src/auth.py",
      "name": "validate_token",
      "reason": "Update token validation."
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
      "step_type": "validate"
    }}
  ],
  "dependencies": [],
  "tests_to_add": ["Reject expired tokens."],
  "validation_commands": ["pytest tests/test_auth.py"],
  "risks": []
}}
"""


def test_parse_valid_plan() -> None:
    plan = parse_implementation_plan(valid_payload())

    assert plan.summary == "Update authentication."
    assert len(plan.files_to_modify) == 1
    assert len(plan.symbols_to_modify) == 1
    assert len(plan.implementation_steps) == 3
    assert plan.implementation_steps[0].step_type == PlanStepType.MODIFY


def test_parse_markdown_code_fence() -> None:
    content = f"```json\n{valid_payload().strip()}\n```"

    plan = parse_implementation_plan(content)

    assert plan.summary == "Update authentication."


def test_empty_response_is_rejected() -> None:
    with pytest.raises(PlanParsingError, match="empty"):
        parse_implementation_plan("")


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(PlanParsingError, match="valid JSON"):
        parse_implementation_plan("{not-json}")


def test_non_object_json_is_rejected() -> None:
    with pytest.raises(PlanParsingError, match="JSON object"):
        parse_implementation_plan("[]")


def test_invalid_step_type_is_rejected() -> None:
    content = valid_payload().replace(
        '"step_type": "modify"',
        '"step_type": "unknown"',
    )

    with pytest.raises(PlanParsingError):
        parse_implementation_plan(content)


def test_invalid_symbol_uuid_is_rejected() -> None:
    content = valid_payload()
    marker = '"symbol_id": "'
    start = content.index(marker) + len(marker)
    end = content.index('"', start)

    content = content[:start] + "not-a-uuid" + content[end:]

    with pytest.raises(PlanParsingError):
        parse_implementation_plan(content)


def test_validator_rejects_plan_without_steps() -> None:
    content = valid_payload().replace(
        """
  "implementation_steps": [
    {
      "order": 1,
      "description": "Update token validation.",
      "step_type": "modify",
      "file_path": "src/auth.py",
      "symbol_name": "validate_token"
    },
    {
      "order": 2,
      "description": "Add regression tests.",
      "step_type": "test",
      "file_path": "tests/test_auth.py"
    },
    {
      "order": 3,
      "description": "Run validation.",
      "step_type": "validate"
    }
  ],""",
        '"implementation_steps": [],',
    )

    with pytest.raises(PlanParsingError):
        parse_implementation_plan(content)
