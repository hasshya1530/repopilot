import json
from pathlib import PurePosixPath

from agents.reviewer.errors import ReviewParsingError
from agents.reviewer.models import (
    ReviewCategory,
    ReviewDecision,
    ReviewFinding,
    ReviewResult,
    ReviewSeverity,
)


def parse_review_result(content: str) -> ReviewResult:
    """Parse an LLM review response into a validated review result."""
    payload = _parse_json(content)

    if not isinstance(payload, dict):
        raise ReviewParsingError(
            "Review response must be a JSON object."
        )

    decision = payload.get("decision")
    summary = payload.get("summary")
    findings = payload.get("findings")

    if not isinstance(decision, str):
        raise ReviewParsingError(
            "Review response requires a decision."
        )

    try:
        parsed_decision = ReviewDecision(decision)
    except ValueError as exc:
        raise ReviewParsingError(
            f"Unsupported review decision: {decision!r}."
        ) from exc

    if not isinstance(summary, str) or not summary.strip():
        raise ReviewParsingError(
            "Review response requires a non-empty summary."
        )

    if not isinstance(findings, list):
        raise ReviewParsingError(
            "Review response requires a findings list."
        )

    parsed_findings = tuple(
        _parse_finding(raw_finding, index)
        for index, raw_finding in enumerate(findings)
    )

    if (
        parsed_decision == ReviewDecision.APPROVE
        and any(
            finding.severity
            in {
                ReviewSeverity.HIGH,
                ReviewSeverity.CRITICAL,
            }
            for finding in parsed_findings
        )
    ):
        raise ReviewParsingError(
            "Approved review cannot contain high or critical findings."
        )

    return ReviewResult(
        decision=parsed_decision,
        summary=summary.strip(),
        findings=parsed_findings,
    )


def _parse_json(content: str) -> object:
    text = content.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if len(lines) < 3:
            raise ReviewParsingError(
                "Unclosed Markdown code fence."
            )

        if lines[0].strip().lower() not in {
            "```json",
            "```",
        }:
            raise ReviewParsingError(
                "Only JSON code fences are supported."
            )

        if lines[-1].strip() != "```":
            raise ReviewParsingError(
                "Unclosed Markdown code fence."
            )

        text = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReviewParsingError(
            f"Review response is not valid JSON: {exc.msg}."
        ) from exc


def _parse_finding(
    raw_finding: object,
    index: int,
) -> ReviewFinding:
    if not isinstance(raw_finding, dict):
        raise ReviewParsingError(
            f"Finding at index {index} must be a JSON object."
        )

    severity = raw_finding.get("severity")
    category = raw_finding.get("category")
    file_path = raw_finding.get("file_path")
    line = raw_finding.get("line")
    title = raw_finding.get("title")
    description = raw_finding.get("description")
    recommendation = raw_finding.get("recommendation")

    if not isinstance(severity, str):
        raise ReviewParsingError(
            f"Finding at index {index} requires a severity."
        )

    if not isinstance(category, str):
        raise ReviewParsingError(
            f"Finding at index {index} requires a category."
        )

    if not isinstance(file_path, str) or not file_path.strip():
        raise ReviewParsingError(
            f"Finding at index {index} requires a file_path."
        )

    if line is not None and (
        not isinstance(line, int)
        or isinstance(line, bool)
        or line < 1
    ):
        raise ReviewParsingError(
            f"Finding at index {index} has an invalid line."
        )

    if not isinstance(title, str) or not title.strip():
        raise ReviewParsingError(
            f"Finding at index {index} requires a non-empty title."
        )

    if not isinstance(description, str) or not description.strip():
        raise ReviewParsingError(
            f"Finding at index {index} requires a non-empty description."
        )

    if (
        not isinstance(recommendation, str)
        or not recommendation.strip()
    ):
        raise ReviewParsingError(
            f"Finding at index {index} requires a non-empty "
            "recommendation."
        )

    try:
        parsed_severity = ReviewSeverity(severity)
    except ValueError as exc:
        raise ReviewParsingError(
            f"Finding at index {index} has unsupported severity: "
            f"{severity!r}."
        ) from exc

    try:
        parsed_category = ReviewCategory(category)
    except ValueError as exc:
        raise ReviewParsingError(
            f"Finding at index {index} has unsupported category: "
            f"{category!r}."
        ) from exc

    normalized_path = _validate_file_path(
        file_path,
        index,
    )

    return ReviewFinding(
        severity=parsed_severity,
        category=parsed_category,
        file_path=normalized_path,
        line=line,
        title=title.strip(),
        description=description.strip(),
        recommendation=recommendation.strip(),
    )


def _validate_file_path(
    file_path: str,
    index: int,
) -> str:
    normalized = file_path.strip().replace("\\", "/")
    path = PurePosixPath(normalized)

    if path.is_absolute():
        raise ReviewParsingError(
            f"Finding at index {index} contains an absolute file path."
        )

    if normalized == "." or ".." in path.parts:
        raise ReviewParsingError(
            f"Finding at index {index} contains path traversal."
        )

    if not normalized:
        raise ReviewParsingError(
            f"Finding at index {index} contains an empty file path."
        )

    return normalized
