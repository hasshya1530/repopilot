import json

import pytest

from agents.reviewer.errors import ReviewParsingError
from agents.reviewer.models import (
    ReviewCategory,
    ReviewDecision,
    ReviewSeverity,
)
from agents.reviewer.parser import parse_review_result


def make_review_payload(
    *,
    decision: str = "approve",
    summary: str = "The implementation looks correct.",
    findings: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if findings is None:
        findings = []

    return {
        "decision": decision,
        "summary": summary,
        "findings": findings,
    }


def make_finding(
    *,
    severity: str = "low",
    category: str = "code_quality",
    file_path: str = "app.py",
    line: int | None = 1,
    title: str = "Minor improvement",
    description: str = "The implementation could be simplified.",
    recommendation: str = "Simplify the implementation.",
) -> dict[str, object]:
    return {
        "severity": severity,
        "category": category,
        "file_path": file_path,
        "line": line,
        "title": title,
        "description": description,
        "recommendation": recommendation,
    }


def test_parse_approved_review_without_findings() -> None:
    payload = make_review_payload()

    result = parse_review_result(json.dumps(payload))

    assert result.decision == ReviewDecision.APPROVE
    assert result.approved is True
    assert result.summary == "The implementation looks correct."
    assert result.findings == ()
    assert result.blocking_findings == ()


def test_parse_review_with_finding() -> None:
    payload = make_review_payload(
        decision="request_changes",
        summary="A security issue must be addressed.",
        findings=[
            make_finding(
                severity="high",
                category="security",
                file_path="auth.py",
                line=42,
                title="Unsafe credential handling",
                description="Credentials are logged.",
                recommendation="Remove credentials from logs.",
            )
        ],
    )

    result = parse_review_result(json.dumps(payload))

    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert result.approved is False
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.severity == ReviewSeverity.HIGH
    assert finding.category == ReviewCategory.SECURITY
    assert finding.file_path == "auth.py"
    assert finding.line == 42
    assert finding.title == "Unsafe credential handling"
    assert finding.description == "Credentials are logged."
    assert finding.recommendation == "Remove credentials from logs."

    assert result.blocking_findings == (finding,)


def test_parse_multiple_findings() -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(
                severity="medium",
                category="correctness",
                file_path="service.py",
                line=10,
            ),
            make_finding(
                severity="low",
                category="maintainability",
                file_path="utils.py",
                line=20,
            ),
        ],
    )

    result = parse_review_result(json.dumps(payload))

    assert len(result.findings) == 2
    assert result.findings[0].category == ReviewCategory.CORRECTNESS
    assert result.findings[1].category == ReviewCategory.MAINTAINABILITY


def test_parse_json_code_fence() -> None:
    payload = make_review_payload()

    content = f"```json\n{json.dumps(payload)}\n```"

    result = parse_review_result(content)

    assert result.decision == ReviewDecision.APPROVE
    assert result.summary == "The implementation looks correct."


def test_parse_plain_code_fence() -> None:
    payload = make_review_payload()

    content = f"```\n{json.dumps(payload)}\n```"

    result = parse_review_result(content)

    assert result.decision == ReviewDecision.APPROVE


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            [],
            "Review response must be a JSON object",
        ),
        (
            {"summary": "Missing decision", "findings": []},
            "requires a decision",
        ),
        (
            {
                "decision": "approve",
                "findings": [],
            },
            "requires a non-empty summary",
        ),
        (
            {
                "decision": "approve",
                "summary": "Missing findings",
            },
            "requires a findings list",
        ),
    ],
)
def test_parse_rejects_invalid_top_level_payload(
    payload: object,
    message: str,
) -> None:
    content = json.dumps(payload)

    with pytest.raises(
        ReviewParsingError,
        match=message,
    ):
        parse_review_result(content)


def test_parse_rejects_invalid_json() -> None:
    with pytest.raises(
        ReviewParsingError,
        match="not valid JSON",
    ):
        parse_review_result("{invalid")


def test_parse_rejects_unclosed_code_fence() -> None:
    with pytest.raises(
        ReviewParsingError,
        match="Unclosed Markdown code fence",
    ):
        parse_review_result("```json\n{}")


def test_parse_rejects_non_json_code_fence() -> None:
    with pytest.raises(
        ReviewParsingError,
        match="Only JSON code fences",
    ):
        parse_review_result("```python\n{}\n```")


def test_parse_rejects_invalid_decision() -> None:
    payload = make_review_payload(
        decision="maybe",
    )

    with pytest.raises(
        ReviewParsingError,
        match="Unsupported review decision",
    ):
        parse_review_result(json.dumps(payload))


def test_parse_rejects_empty_summary() -> None:
    payload = make_review_payload(
        summary="   ",
    )

    with pytest.raises(
        ReviewParsingError,
        match="non-empty summary",
    ):
        parse_review_result(json.dumps(payload))


def test_parse_rejects_non_list_findings() -> None:
    payload = {
        "decision": "approve",
        "summary": "Looks good.",
        "findings": {},
    }

    with pytest.raises(
        ReviewParsingError,
        match="requires a findings list",
    ):
        parse_review_result(json.dumps(payload))


@pytest.mark.parametrize(
    "field",
    [
        "severity",
        "category",
        "file_path",
        "title",
        "description",
        "recommendation",
    ],
)
def test_parse_rejects_missing_finding_field(
    field: str,
) -> None:
    finding = make_finding()
    del finding[field]

    payload = make_review_payload(
        decision="request_changes",
        findings=[finding],
    )

    with pytest.raises(
        ReviewParsingError,
        match="requires",
    ):
        parse_review_result(json.dumps(payload))


def test_parse_rejects_non_object_finding() -> None:
    payload = make_review_payload(
        decision="request_changes",
    )
    payload["findings"] = ["invalid"]

    with pytest.raises(
        ReviewParsingError,
        match="must be a JSON object",
    ):
        parse_review_result(json.dumps(payload))


def test_parse_rejects_invalid_severity() -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(severity="extreme"),
        ],
    )

    with pytest.raises(
        ReviewParsingError,
        match="unsupported severity",
    ):
        parse_review_result(json.dumps(payload))


def test_parse_rejects_invalid_category() -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(category="random"),
        ],
    )

    with pytest.raises(
        ReviewParsingError,
        match="unsupported category",
    ):
        parse_review_result(json.dumps(payload))


@pytest.mark.parametrize(
    "file_path",
    [
        "/etc/passwd",
        "../secret.py",
        "foo/../../secret.py",
    ],
)
def test_parse_rejects_unsafe_file_path(
    file_path: str,
) -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(file_path=file_path),
        ],
    )

    with pytest.raises(
        ReviewParsingError,
        match="path",
    ):
        parse_review_result(json.dumps(payload))


@pytest.mark.parametrize(
    "line",
    [
        0,
        -1,
        True,
        "10",
    ],
)
def test_parse_rejects_invalid_line(
    line: object,
) -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(line=line),  # type: ignore[arg-type]
        ],
    )

    with pytest.raises(
        ReviewParsingError,
        match="invalid line",
    ):
        parse_review_result(json.dumps(payload))


def test_parse_allows_missing_line() -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(line=None),
        ],
    )

    result = parse_review_result(json.dumps(payload))

    assert result.findings[0].line is None


def test_approve_with_high_finding_is_rejected() -> None:
    payload = make_review_payload(
        decision="approve",
        findings=[
            make_finding(
                severity="high",
                category="security",
            ),
        ],
    )

    with pytest.raises(
        ReviewParsingError,
        match="Approved review cannot contain high or critical findings",
    ):
        parse_review_result(json.dumps(payload))


def test_approve_with_critical_finding_is_rejected() -> None:
    payload = make_review_payload(
        decision="approve",
        findings=[
            make_finding(
                severity="critical",
                category="security",
            ),
        ],
    )

    with pytest.raises(
        ReviewParsingError,
        match="Approved review cannot contain high or critical findings",
    ):
        parse_review_result(json.dumps(payload))


def test_request_changes_with_high_finding_is_allowed() -> None:
    payload = make_review_payload(
        decision="request_changes",
        findings=[
            make_finding(
                severity="high",
                category="security",
            ),
        ],
    )

    result = parse_review_result(json.dumps(payload))

    assert result.decision == ReviewDecision.REQUEST_CHANGES
    assert len(result.blocking_findings) == 1


def test_whitespace_is_normalized() -> None:
    payload = make_review_payload(
        summary="  Review summary  ",
        findings=[
            make_finding(
                file_path="  src/app.py  ",
                title="  Finding title  ",
                description="  Finding description  ",
                recommendation="  Recommendation  ",
            )
        ],
    )

    result = parse_review_result(json.dumps(payload))

    assert result.summary == "Review summary"
    assert result.findings[0].file_path == "src/app.py"
    assert result.findings[0].title == "Finding title"
    assert result.findings[0].description == "Finding description"
    assert result.findings[0].recommendation == "Recommendation"
