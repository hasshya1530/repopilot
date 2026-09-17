from agents.llm.models import LLMMessage, LLMRequest
from agents.llm.provider import LLMProvider
from agents.planner.models import PlanningContext
from agents.planner.plan_models import ImplementationPlan
from agents.planner.plan_parser import PlanParsingError, parse_implementation_plan


class PlannerGenerationError(RuntimeError):
    """Raised when the LLM planner cannot produce a valid implementation plan."""


class LLMPlanner:
    """Generate validated implementation plans using an LLM."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def generate_plan(
        self,
        context: PlanningContext,
        *,
        max_tokens: int = 4096,
    ) -> ImplementationPlan:
        request = LLMRequest(
            messages=(
                LLMMessage(
                    role="system",
                    content=_SYSTEM_PROMPT,
                ),
                LLMMessage(
                    role="user",
                    content=build_planning_prompt(context),
                ),
            ),
            temperature=0.0,
            max_tokens=max_tokens,
        )

        response = await self._provider.generate(request)

        try:
            return parse_implementation_plan(response.content)
        except PlanParsingError as exc:
            raise PlannerGenerationError(
                f"LLM returned an invalid implementation plan: {exc}"
            ) from exc


def build_planning_prompt(context: PlanningContext) -> str:
    """Build a deterministic planning prompt from repository context."""
    sections = [
        "TASK",
        context.task_description,
        "",
        "RELEVANT FILES",
        _format_files(context),
        "",
        "RELEVANT SYMBOLS",
        _format_symbols(context),
        "",
        "DEPENDENCIES",
        _format_dependencies(context),
        "",
        "CONSTRAINTS",
        _format_constraints(context),
        "",
        "OUTPUT REQUIREMENTS",
        _OUTPUT_REQUIREMENTS,
    ]

    return "\n".join(sections)


def _format_files(context: PlanningContext) -> str:
    if not context.files:
        return "None identified."

    return "\n".join(
        f"- {item.file_path}: {item.reason} (relevance={item.relevance_score:.4f})"
        for item in context.files
    )


def _format_symbols(context: PlanningContext) -> str:
    if not context.symbols:
        return "None identified."

    return "\n".join(
        f"- {item.symbol_id}: {item.file_path}:{item.start_line}-"
        f"{item.end_line} {item.name} [{item.symbol_type}] — {item.reason}"
        for item in context.symbols
    )


def _format_dependencies(context: PlanningContext) -> str:
    if not context.dependencies:
        return "None identified."

    return "\n".join(
        f"- {item.source_symbol_id} -> {item.target_symbol_id} "
        f"[{item.relation}], depth={item.depth}"
        for item in context.dependencies
    )


def _format_constraints(context: PlanningContext) -> str:
    if not context.constraints:
        return "None."

    return "\n".join(
        f"- {constraint.name}: {constraint.description}" for constraint in context.constraints
    )


_SYSTEM_PROMPT = """\
You are RepoPilot's software engineering planner.

Your job is to analyze the supplied repository context and produce a
concrete implementation plan.

You MUST:
- reason only from the supplied repository context;
- avoid inventing files or symbols unless creating a new file is necessary;
- preserve existing architecture and conventions;
- account for affected dependencies;
- include tests for behavioral changes;
- include executable validation commands;
- identify assumptions and risks;
- return ONLY valid JSON;
- do not wrap the JSON in Markdown.

The plan will be validated before any implementation work is allowed.
"""

_OUTPUT_REQUIREMENTS = """\
Return a JSON object with exactly these top-level fields:

{
  "summary": "string",
  "assumptions": ["string"],
  "files_to_modify": [
    {
      "file_path": "relative/path",
      "reason": "string"
    }
  ],
  "files_to_create": [
    {
      "file_path": "relative/path",
      "reason": "string"
    }
  ],
  "symbols_to_modify": [
    {
      "symbol_id": "UUID",
      "file_path": "relative/path",
      "name": "string",
      "reason": "string"
    }
  ],
  "implementation_steps": [
    {
      "order": 1,
      "description": "string",
      "step_type": "modify|create|delete|test|validate",
      "file_path": "relative/path or null",
      "symbol_name": "string or null"
    }
  ],
  "dependencies": ["string"],
  "tests_to_add": ["string"],
  "validation_commands": ["string"],
  "risks": ["string"]
}

Implementation steps must be ordered sequentially starting at 1.
Use relative repository paths only.
Do not use absolute paths.
Do not use '..' path traversal.
"""
