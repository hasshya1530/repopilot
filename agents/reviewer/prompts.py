from agents.implementer.context.models import ImplementationContext
from agents.implementer.models import ImplementationResult

SYSTEM_REVIEW_PROMPT = """\
You are RepoPilot's senior code review agent.

Your job is to review an AI-generated implementation against the user's task.

You are a reviewer, not an implementer.

Do not modify code.
Do not propose changes outside the scope of the task unless they are directly
relevant to correctness, security, reliability, or maintainability.

Review the actual implementation carefully.

Focus on:
- correctness
- security
- maintainability
- code quality
- test coverage
- performance
- architecture

Only report findings that are supported by the provided code and task.
Avoid speculative findings and subjective style preferences.

Severity definitions:
- info: useful observation with no meaningful risk
- low: minor issue with limited impact
- medium: issue that should generally be addressed
- high: significant correctness, security, reliability, or architectural issue
- critical: severe issue that can cause major breakage, security impact, or data loss

Decision rules:
- APPROVE when the implementation satisfies the task and has no high or
  critical issues.
- REQUEST_CHANGES when the implementation has a high or critical issue.
- Medium or lower findings may still result in REQUEST_CHANGES when they
  materially prevent the task from being considered complete.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
  "decision": "approve" | "request_changes",
  "summary": "short review summary",
  "findings": [
    {
      "severity": "info" | "low" | "medium" | "high" | "critical",
      "category": "correctness" | "security" | "maintainability" |
                  "code_quality" | "test_coverage" | "performance" |
                  "architecture",
      "file_path": "repository-relative/path.py",
      "line": 42,
      "title": "short finding title",
      "description": "specific evidence-based explanation",
      "recommendation": "specific recommended action"
    }
  ]
}

Use null for "line" when a finding applies to a file or change generally.

Do not wrap the JSON in Markdown unless explicitly requested.
"""


def build_review_prompt(
    *,
    context: ImplementationContext,
    implementation: ImplementationResult,
) -> str:
    """Build the user prompt containing the task and implementation context."""
    sections: list[str] = [
        "## Original Task",
        context.task_description.strip(),
        "",
        "## Generated Implementation Summary",
        implementation.summary.strip(),
        "",
        "## Changed Files",
    ]

    if not implementation.changes:
        sections.append("No changes were generated.")

    for change in implementation.changes:
        sections.extend(
            [
                "",
                f"### {change.operation.value.upper()}: {change.file_path}",
                f"Reason: {change.reason.strip()}",
                "",
                "Generated content:",
                "```",
                change.content,
                "```",
            ]
        )

    sections.extend(["", "## Repository Context"])

    if not context.files:
        sections.append("No repository files were provided.")

    for file_context in context.files:
        sections.extend(
            [
                "",
                f"### {file_context.file_path}",
                f"Context reason: {file_context.reason.strip()}",
                "",
                "Current file content:",
                "```",
                file_context.content,
                "```",
            ]
        )

    if context.symbols:
        sections.extend(["", "## Relevant Symbols"])

        for symbol in context.symbols:
            sections.extend(
                [
                    "",
                    f"- {symbol.file_path}:{symbol.start_line}-{symbol.end_line}",
                    f"  {symbol.symbol_type}: {symbol.name}",
                ]
            )

    if context.dependencies:
        symbol_by_id = {
            symbol.symbol_id: symbol
            for symbol in context.symbols
        }

        sections.extend(["", "## Relevant Dependencies"])

        for dependency in context.dependencies:
            source = symbol_by_id.get(dependency.source_symbol_id)
            target = symbol_by_id.get(dependency.target_symbol_id)

            source_name = source.name if source is not None else str(
                dependency.source_symbol_id
            )
            target_name = target.name if target is not None else str(
                dependency.target_symbol_id
            )

            sections.append(
                f"- {source_name} -> {target_name} "
                f"({dependency.relation}, depth={dependency.depth})"
            )

    sections.extend(
        [
            "",
            "## Review Instructions",
            "Review the generated implementation against the original task.",
            "Use the repository context to understand surrounding code.",
            "Prioritize concrete defects over stylistic preferences.",
            "Identify the affected file and line when the location is clear.",
            "Return only the required JSON object.",
        ]
    )

    return "\n".join(sections)
