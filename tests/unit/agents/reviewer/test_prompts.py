from uuid import UUID

from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextDependency,
    ImplementationContextFile,
    ImplementationContextSymbol,
)
from agents.implementer.models import (
    ChangeOperation,
    CodeChange,
    ImplementationResult,
)
from agents.reviewer.prompts import SYSTEM_REVIEW_PROMPT, build_review_prompt

REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000001")
SOURCE_SYMBOL_ID = UUID("00000000-0000-0000-0000-000000000002")
TARGET_SYMBOL_ID = UUID("00000000-0000-0000-0000-000000000003")


def make_context(
    *,
    files: tuple[ImplementationContextFile, ...] = (),
    symbols: tuple[ImplementationContextSymbol, ...] = (),
    dependencies: tuple[ImplementationContextDependency, ...] = (),
) -> ImplementationContext:
    return ImplementationContext(
        repository_id=REPOSITORY_ID,
        task_description="Fix the broken addition function.",
        files=files,
        symbols=symbols,
        dependencies=dependencies,
    )


def make_implementation(
    *,
    changes: tuple[CodeChange, ...] = (),
) -> ImplementationResult:
    return ImplementationResult(
        summary="Implemented the requested fix.",
        changes=changes,
    )


def make_change(
    *,
    file_path: str = "app.py",
    operation: ChangeOperation = ChangeOperation.MODIFY,
    content: str = "def add(a, b):\n    return a + b\n",
    reason: str = "Fix addition logic.",
) -> CodeChange:
    return CodeChange(
        file_path=file_path,
        operation=operation,
        content=content,
        reason=reason,
    )


def test_system_review_prompt_contains_review_contract() -> None:
    assert "senior code review agent" in SYSTEM_REVIEW_PROMPT
    assert "Do not modify code." in SYSTEM_REVIEW_PROMPT
    assert "Return ONLY valid JSON." in SYSTEM_REVIEW_PROMPT
    assert '"decision"' in SYSTEM_REVIEW_PROMPT
    assert '"findings"' in SYSTEM_REVIEW_PROMPT
    assert '"severity"' in SYSTEM_REVIEW_PROMPT
    assert '"category"' in SYSTEM_REVIEW_PROMPT


def test_build_review_prompt_contains_task_and_summary() -> None:
    prompt = build_review_prompt(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert "## Original Task" in prompt
    assert "Fix the broken addition function." in prompt
    assert "## Generated Implementation Summary" in prompt
    assert "Implemented the requested fix." in prompt


def test_build_review_prompt_contains_changed_file_details() -> None:
    implementation = make_implementation(
        changes=(
            make_change(
                file_path="src/calculator.py",
                content="def add(a, b):\n    return a + b\n",
                reason="Correct subtraction to addition.",
            ),
        )
    )

    prompt = build_review_prompt(
        context=make_context(),
        implementation=implementation,
    )

    assert "## Changed Files" in prompt
    assert "### MODIFY: src/calculator.py" in prompt
    assert "Reason: Correct subtraction to addition." in prompt
    assert "def add(a, b):" in prompt
    assert "return a + b" in prompt


def test_build_review_prompt_contains_repository_files() -> None:
    context_file = ImplementationContextFile(
        file_path="src/calculator.py",
        content="def add(a, b):\n    return a + b\n",
        reason="Relevant implementation file.",
    )

    prompt = build_review_prompt(
        context=make_context(files=(context_file,)),
        implementation=make_implementation(),
    )

    assert "## Repository Context" in prompt
    assert "### src/calculator.py" in prompt
    assert "Context reason: Relevant implementation file." in prompt
    assert "Current file content:" in prompt
    assert "return a + b" in prompt


def test_build_review_prompt_handles_empty_changes_and_files() -> None:
    prompt = build_review_prompt(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert "No changes were generated." in prompt
    assert "No repository files were provided." in prompt


def test_build_review_prompt_includes_relevant_symbols() -> None:
    symbol = ImplementationContextSymbol(
        symbol_id=SOURCE_SYMBOL_ID,
        file_path="src/calculator.py",
        name="add",
        symbol_type="function",
        start_line=1,
        end_line=2,
        content="def add(a, b):\n    return a + b",
        reason="Changed function.",
    )

    prompt = build_review_prompt(
        context=make_context(symbols=(symbol,)),
        implementation=make_implementation(),
    )

    assert "## Relevant Symbols" in prompt
    assert "src/calculator.py:1-2" in prompt
    assert "function: add" in prompt


def test_build_review_prompt_resolves_dependency_symbol_names() -> None:
    source = ImplementationContextSymbol(
        symbol_id=SOURCE_SYMBOL_ID,
        file_path="src/calculator.py",
        name="add",
        symbol_type="function",
        start_line=1,
        end_line=2,
        content="def add(a, b):\n    return a + b",
        reason="Source symbol.",
    )
    target = ImplementationContextSymbol(
        symbol_id=TARGET_SYMBOL_ID,
        file_path="src/math.py",
        name="validate_input",
        symbol_type="function",
        start_line=1,
        end_line=3,
        content="def validate_input(a, b):\n    return True",
        reason="Target symbol.",
    )
    dependency = ImplementationContextDependency(
        source_symbol_id=SOURCE_SYMBOL_ID,
        target_symbol_id=TARGET_SYMBOL_ID,
        relation="calls",
        depth=1,
    )

    prompt = build_review_prompt(
        context=make_context(
            symbols=(source, target),
            dependencies=(dependency,),
        ),
        implementation=make_implementation(),
    )

    assert "## Relevant Dependencies" in prompt
    assert "- add -> validate_input (calls, depth=1)" in prompt
    assert str(SOURCE_SYMBOL_ID) not in prompt
    assert str(TARGET_SYMBOL_ID) not in prompt


def test_build_review_prompt_falls_back_to_dependency_ids() -> None:
    dependency = ImplementationContextDependency(
        source_symbol_id=SOURCE_SYMBOL_ID,
        target_symbol_id=TARGET_SYMBOL_ID,
        relation="imports",
        depth=2,
    )

    prompt = build_review_prompt(
        context=make_context(dependencies=(dependency,)),
        implementation=make_implementation(),
    )

    assert "## Relevant Dependencies" in prompt
    assert (
        f"- {SOURCE_SYMBOL_ID} -> {TARGET_SYMBOL_ID} "
        "(imports, depth=2)"
    ) in prompt


def test_build_review_prompt_includes_review_instructions() -> None:
    prompt = build_review_prompt(
        context=make_context(),
        implementation=make_implementation(),
    )

    assert "## Review Instructions" in prompt
    assert "Review the generated implementation against the original task." in prompt
    assert "Prioritize concrete defects over stylistic preferences." in prompt
    assert "Return only the required JSON object." in prompt


def test_build_review_prompt_includes_create_and_delete_operations() -> None:
    implementation = make_implementation(
        changes=(
            make_change(
                file_path="src/new_module.py",
                operation=ChangeOperation.CREATE,
                content="VALUE = 42\n",
                reason="Create new module.",
            ),
            make_change(
                file_path="src/old_module.py",
                operation=ChangeOperation.DELETE,
                content="",
                reason="Remove obsolete module.",
            ),
        )
    )

    prompt = build_review_prompt(
        context=make_context(),
        implementation=implementation,
    )

    assert "### CREATE: src/new_module.py" in prompt
    assert "### DELETE: src/old_module.py" in prompt
    assert "Create new module." in prompt
    assert "Remove obsolete module." in prompt
