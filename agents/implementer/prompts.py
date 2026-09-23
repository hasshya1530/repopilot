from agents.implementer.context.models import ImplementationContext
from agents.planner.plan_models import ImplementationPlan

_SYSTEM_PROMPT = """\
You are RepoPilot's implementation agent.

Your job is to implement an approved software engineering plan.

You MUST:
- use only the repository source code supplied by the caller
- follow the implementation plan
- preserve existing behavior unless the plan explicitly changes it
- make the smallest reasonable changes
- include complete resulting file contents for every changed file
- never invent files or APIs that are not supported by the repository context
- return ONLY a valid JSON object
- do not return Markdown
- do not return a code fence
- do not include any text before or after the JSON object

The JSON format MUST be:

{
  "summary": "short implementation summary",
  "changes": [
    {
      "file_path": "relative/path/to/file.py",
      "operation": "modify",
      "content": "complete resulting file content",
      "reason": "why this change is required"
    }
  ]
}

CRITICAL JSON RULES:
- The entire response must be valid JSON.
- File contents are JSON string values.
- Escape every double quote that appears inside file content.
- Represent newlines inside file content as JSON newline escapes.
- Preserve the original source code exactly except for the requested changes.
- Do not put Markdown fences around file content.
- Do not truncate file content.
- Do not use comments such as "rest of file omitted".
- Do not use placeholders such as "...".
- Do not emit trailing commas.

Allowed operations:
- modify
- create
- delete

For DELETE operations:
- content MUST be an empty string.

For MODIFY and CREATE operations:
- content MUST contain the complete resulting file.

File paths:
- must be relative to the repository root
- must not be absolute
- must not contain '..'
- must not escape the repository
"""


def build_implementation_prompt(
    *,
    context: ImplementationContext,
    plan: ImplementationPlan,
) -> str:
    lines: list[str] = [
        "## Task",
        context.task_description,
        "",
        "## Approved Implementation Plan",
        f"Summary: {plan.summary}",
        "",
        "### Assumptions",
    ]

    lines.extend(
        f"- {assumption}"
        for assumption in plan.assumptions
    )

    lines.extend(
        [
            "",
            "### Files To Modify",
        ]
    )

    lines.extend(
        f"- `{file.file_path}`: {file.reason}"
        for file in plan.files_to_modify
    )

    lines.extend(
        [
            "",
            "### Files To Create",
        ]
    )

    lines.extend(
        f"- `{file.file_path}`: {file.reason}"
        for file in plan.files_to_create
    )

    lines.extend(
        [
            "",
            "### Symbols To Modify",
        ]
    )

    lines.extend(
        f"- `{symbol.file_path}`::{symbol.name}: {symbol.reason}"
        for symbol in plan.symbols_to_modify
    )

    lines.extend(
        [
            "",
            "### Implementation Steps",
        ]
    )

    lines.extend(
        f"{step.order}. [{step.step_type.value}] {step.description}"
        for step in plan.implementation_steps
    )

    lines.extend(
        [
            "",
            "### Tests To Add",
        ]
    )

    lines.extend(
        f"- {test}"
        for test in plan.tests_to_add
    )

    lines.extend(
        [
            "",
            "### Validation Commands",
        ]
    )

    lines.extend(
        f"- `{command}`"
        for command in plan.validation_commands
    )

    lines.extend(
        [
            "",
            "### Risks",
        ]
    )

    lines.extend(
        f"- {risk}"
        for risk in plan.risks
    )

    lines.extend(
        [
            "",
            "## Repository Source",
        ]
    )

    for file in context.files:
        lines.extend(
            [
                "",
                f"### File: `{file.file_path}`",
                f"Reason: {file.reason}",
                "",
                "```text",
                file.content,
                "```",
            ]
        )

    lines.extend(
        [
            "",
            "## Relevant Symbols",
        ]
    )

    for symbol in context.symbols:
        lines.extend(
            [
                "",
                (
                    f"### `{symbol.file_path}`::{symbol.name} "
                    f"({symbol.symbol_type})"
                ),
                (
                    f"Lines: {symbol.start_line}-"
                    f"{symbol.end_line}"
                ),
                f"Reason: {symbol.reason}",
                "",
                "```text",
                symbol.content,
                "```",
            ]
        )

    lines.extend(
        [
            "",
            "## Dependencies",
        ]
    )

    for dependency in context.dependencies:
        lines.append(
            f"- {dependency.source_symbol_id} "
            f"--[{dependency.relation}]--> "
            f"{dependency.target_symbol_id} "
            f"(depth={dependency.depth})"
        )

    lines.extend(
        [
            "",
            "## Final Requirements",
            "",
            "Return ONLY the JSON implementation result.",
            "Do NOT explain your answer outside the JSON.",
            "Every changed file must contain complete resulting content.",
            "The response must be parseable by Python json.loads().",
        ]
    )

    return "\n".join(lines)


def get_system_prompt() -> str:
    return _SYSTEM_PROMPT
