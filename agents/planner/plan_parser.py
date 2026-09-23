import json
from typing import Any
from uuid import UUID

from agents.planner.plan_models import (
    ImplementationPlan,
    ImplementationStep,
    PlannedFile,
    PlannedSymbol,
    PlanStepType,
)
from agents.planner.plan_validator import validate_plan


class PlanParsingError(ValueError):
    """Raised when an LLM response cannot be converted into an implementation plan."""


def parse_implementation_plan(content: str) -> ImplementationPlan:
    """Parse and validate an implementation plan returned by an LLM."""

    if not content.strip():
        raise PlanParsingError("LLM returned an empty plan.")

    data = _parse_json(content)

    if not isinstance(data, dict):
        raise PlanParsingError("Implementation plan must be a JSON object.")

    try:
        plan = _build_plan(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise PlanParsingError(
            f"Invalid implementation plan structure: {exc}"
        ) from exc

    try:
        validate_plan(plan)
    except ValueError as exc:
        raise PlanParsingError(str(exc)) from exc

    return plan


def _parse_json(content: str) -> Any:
    text = content.strip()

    if text.startswith("```"):
        text = _remove_code_fence(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanParsingError(
            f"LLM response is not valid JSON: {exc.msg}."
        ) from exc


def _remove_code_fence(content: str) -> str:
    lines = content.splitlines()

    if not lines:
        return content

    if lines[0].strip().startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _build_plan(data: dict[str, Any]) -> ImplementationPlan:
    return ImplementationPlan(
        summary=_require_string(data, "summary"),
        assumptions=_string_tuple(data.get("assumptions", [])),
        files_to_modify=_planned_files(
            data.get("files_to_modify", [])
        ),
        files_to_create=_planned_files(
            data.get("files_to_create", [])
        ),
        test_files=_planned_files(
            data.get("test_files", [])
        ),
        symbols_to_modify=_planned_symbols(
            data.get("symbols_to_modify", [])
        ),
        implementation_steps=_implementation_steps(
            data.get("implementation_steps", [])
        ),
        dependencies=_string_tuple(
            data.get("dependencies", [])
        ),
        tests_to_add=_string_tuple(
            data.get("tests_to_add", [])
        ),
        validation_commands=_string_tuple(
            data.get("validation_commands", [])
        ),
        risks=_string_tuple(
            data.get("risks", [])
        ),
    )


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data[key]

    if not isinstance(value, str):
        raise TypeError(f"'{key}' must be a string.")

    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError("Expected a list of strings.")

    result: list[str] = []

    for item in value:
        if not isinstance(item, str):
            raise TypeError("Expected a list of strings.")

        result.append(item)

    return tuple(result)


def _planned_files(value: Any) -> tuple[PlannedFile, ...]:
    if not isinstance(value, list):
        raise TypeError("Planned files must be a list.")

    result: list[PlannedFile] = []

    for item in value:
        if not isinstance(item, dict):
            raise TypeError("Each planned file must be an object.")

        result.append(
            PlannedFile(
                file_path=_require_string(item, "file_path"),
                reason=_require_string(item, "reason"),
            )
        )

    return tuple(result)


def _planned_symbols(value: Any) -> tuple[PlannedSymbol, ...]:
    if not isinstance(value, list):
        raise TypeError("Planned symbols must be a list.")

    result: list[PlannedSymbol] = []

    for item in value:
        if not isinstance(item, dict):
            raise TypeError("Each planned symbol must be an object.")

        symbol_id = UUID(
            _require_string(item, "symbol_id")
        )

        result.append(
            PlannedSymbol(
                symbol_id=symbol_id,
                file_path=_require_string(item, "file_path"),
                name=_require_string(item, "name"),
                reason=_require_string(item, "reason"),
            )
        )

    return tuple(result)


def _implementation_steps(
    value: Any,
) -> tuple[ImplementationStep, ...]:
    if not isinstance(value, list):
        raise TypeError("Implementation steps must be a list.")

    result: list[ImplementationStep] = []

    for item in value:
        if not isinstance(item, dict):
            raise TypeError(
                "Each implementation step must be an object."
            )

        order = item["order"]

        if not isinstance(order, int):
            raise TypeError("Step order must be an integer.")

        step_type = PlanStepType(
            _require_string(item, "step_type")
        )

        file_path = item.get("file_path")

        if file_path is not None and not isinstance(file_path, str):
            raise TypeError(
                "Step file_path must be a string or null."
            )

        symbol_name = item.get("symbol_name")

        if symbol_name is not None and not isinstance(symbol_name, str):
            raise TypeError(
                "Step symbol_name must be a string or null."
            )

        result.append(
            ImplementationStep(
                order=order,
                description=_require_string(
                    item,
                    "description",
                ),
                step_type=step_type,
                file_path=file_path,
                symbol_name=symbol_name,
            )
        )

    return tuple(result)
