import json
from pathlib import PurePosixPath

from agents.implementer.errors import ChangeParsingError
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)


def parse_implementation_result(content: str) -> ImplementationResult:
    """Parse an LLM response into a validated implementation result."""
    payload = _parse_json(content)

    if not isinstance(payload, dict):
        raise ChangeParsingError("Implementation response must be a JSON object.")

    summary = payload.get("summary")
    changes = payload.get("changes")

    if not isinstance(summary, str) or not summary.strip():
        raise ChangeParsingError("Implementation response requires a non-empty summary.")

    if not isinstance(changes, list) or not changes:
        raise ChangeParsingError("Implementation response requires at least one code change.")

    parsed_changes: list[CodeChange] = []

    for index, raw_change in enumerate(changes):
        if not isinstance(raw_change, dict):
            raise ChangeParsingError(f"Change at index {index} must be a JSON object.")

        parsed_changes.append(_parse_change(raw_change, index))

    return ImplementationResult(
        summary=summary.strip(),
        changes=tuple(parsed_changes),
    )


def _parse_json(content: str) -> object:
    text = content.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if len(lines) < 3:
            raise ChangeParsingError("Invalid Markdown code fence.")

        if lines[0].strip().lower() not in {"```json", "```"}:
            raise ChangeParsingError("Only JSON code fences are supported.")

        if lines[-1].strip() != "```":
            raise ChangeParsingError("Unclosed Markdown code fence.")

        text = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ChangeParsingError(f"Implementation response is not valid JSON: {exc.msg}.") from exc


def _parse_change(raw_change: dict[str, object], index: int) -> CodeChange:
    file_path = raw_change.get("file_path")
    operation = raw_change.get("operation")
    content = raw_change.get("content")
    reason = raw_change.get("reason")

    if not isinstance(file_path, str) or not file_path.strip():
        raise ChangeParsingError(f"Change at index {index} requires a non-empty file_path.")

    if not isinstance(operation, str):
        raise ChangeParsingError(f"Change at index {index} requires an operation.")

    if not isinstance(content, str):
        raise ChangeParsingError(f"Change at index {index} requires string content.")

    if not isinstance(reason, str) or not reason.strip():
        raise ChangeParsingError(f"Change at index {index} requires a non-empty reason.")

    try:
        change_operation = ChangeOperation(operation)
    except ValueError as exc:
        raise ChangeParsingError(
            f"Change at index {index} has unsupported operation: {operation!r}."
        ) from exc

    normalized_path = _validate_file_path(file_path, index)

    if change_operation is ChangeOperation.DELETE and content:
        raise ChangeParsingError(f"Delete change at index {index} must have empty content.")

    if change_operation is not ChangeOperation.DELETE and not content:
        raise ChangeParsingError(f"Change at index {index} requires non-empty content.")

    return CodeChange(
        file_path=normalized_path,
        operation=change_operation,
        content=content,
        reason=reason.strip(),
    )


def _validate_file_path(file_path: str, index: int) -> str:
    normalized = file_path.strip().replace("\\", "/")

    path = PurePosixPath(normalized)

    if path.is_absolute():
        raise ChangeParsingError(f"Change at index {index} contains an absolute file path.")

    if normalized == "." or ".." in path.parts:
        raise ChangeParsingError(f"Change at index {index} contains path traversal.")

    if not normalized:
        raise ChangeParsingError(f"Change at index {index} contains an empty file path.")

    return normalized
