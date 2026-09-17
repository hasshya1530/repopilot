from agents.debugger.analyzer import FailureAnalysis
from agents.implementer.context.models import ImplementationContext


def build_repair_prompt(
    analysis: FailureAnalysis,
    context: ImplementationContext,
) -> str:
    files = "\n\n".join(
        (
            f"FILE: {file.file_path}\n"
            f"REASON: {file.reason}\n"
            f"CONTENT:\n{file.content}"
        )
        for file in context.files
    )

    return f"""You are a software debugging agent.

Your task is to diagnose a failing test and propose the smallest safe
code change that fixes the underlying failure.

TASK:
{context.task_description}

FAILURE TYPE:
{analysis.failure_type}

FAILURE SUMMARY:
{analysis.summary}

FAILURE DETAILS:
{analysis.details}

TEST COMMAND:
{" ".join(analysis.test_command)}

REPOSITORY FILES:
{files}

Return ONLY valid JSON using this exact structure:

{{
  "summary": "Explain the root cause and the repair.",
  "changes": [
    {{
      "file_path": "path/to/file.py",
      "operation": "modify",
      "content": "complete resulting file content",
      "reason": "Why this change fixes the failure."
    }}
  ]
}}

Rules:
- Make the smallest change necessary.
- Preserve existing behavior outside the bug.
- Do not modify tests unless the failure proves the test itself is incorrect.
- Never use absolute paths.
- Never use paths containing '..'.
- Use only these operations: modify, create, delete.
- For modify, provide the complete resulting file content.
- For delete, content must be an empty string.
- For create or modify, content must not be empty.
- Every change must include a reason.
- Do not include Markdown code fences.
- Do not include explanations outside the JSON.
"""
