from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

# Make the repository root importable when this file is executed directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from agents.execution.service import ExecutionService  # noqa: E402
from agents.implementer.applier.service import ChangeApplier  # noqa: E402
from agents.implementer.context.service import ImplementationContextService  # noqa: E402
from agents.implementer.llm_implementer import LLMImplementer  # noqa: E402
from agents.llm.provider import LLMProvider  # noqa: E402
from agents.llm.providers.ollama import OllamaProvider  # noqa: E402
from agents.llm.providers.openrouter import OpenRouterProvider  # noqa: E402
from agents.workspace.service import WorkspaceManager  # noqa: E402
from apps.api.app.core.config import get_settings  # noqa: E402
from apps.api.app.core.database import async_session_factory  # noqa: E402
from apps.api.app.models.repository import Repository  # noqa: E402
from apps.api.app.services.repository_intelligence import (  # noqa: E402
    create_change_context_service,
    create_repository_context_service,
)
from scripts.repopilot_locked_plan import build_locked_plan  # noqa: E402

REPOSITORY_ID = UUID(
    "37f760f3-387d-4063-90aa-c05fc306558e"
)


TASK = """
Improve the background job retry handling in RepoPilot.
Inspect the existing job queue, worker, retry policy,
and related tests. Propose a small, backward-compatible
improvement and include regression tests.
""".strip()


def get_git_files(repository_path: Path) -> tuple[str, ...]:
    """Return tracked repository files."""

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repository_path),
            "ls-files",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip()
    )


def create_llm_provider(settings) -> LLMProvider:
    """Create the configured model provider."""

    provider_name = settings.model_provider.strip().lower()

    if provider_name == "ollama":
        return OllamaProvider(
            model_name=settings.model_name,
            base_url=settings.ollama_base_url,
        )

    if provider_name == "openrouter":
        if not settings.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required when "
                "MODEL_PROVIDER=openrouter."
            )

        return OpenRouterProvider(
            model_name=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            site_url=settings.openrouter_site_url,
            app_name=settings.openrouter_app_name,
        )

    raise RuntimeError(
        f"Unsupported MODEL_PROVIDER: {settings.model_provider!r}"
    )


async def main() -> None:
    settings = get_settings()

    repository_path = Path(
        settings.repository_source_root
    ).resolve()

    workspace_root = Path(
        settings.workspace_root
    ).expanduser()

    print("=" * 100)
    print("REPOPILOT — REAL IMPLEMENTATION / EXECUTION E2E")
    print("=" * 100)
    print(f"Repository:      {repository_path}")
    print(f"Workspace root:  {workspace_root}")
    print(f"Repository ID:   {REPOSITORY_ID}")
    print(f"LLM provider:    {settings.model_provider}")
    print(f"LLM model:       {settings.model_name}")
    print()

    async with async_session_factory() as session:
        repository = await session.scalar(
            select(Repository).where(
                Repository.id == REPOSITORY_ID
            )
        )

        if repository is None:
            raise RuntimeError(
                f"Repository not found: {REPOSITORY_ID}"
            )

        print(f"Repository: {repository.full_name}")
        print()

        # ------------------------------------------------------------------
        # STEP 1 — REPOSITORY CONTEXT
        # ------------------------------------------------------------------

        print("=" * 100)
        print("STEP 1 — REAL REPOSITORY CONTEXT")
        print("=" * 100)

        repository_context_service = (
            create_repository_context_service(
                session=session,
                settings=settings,
            )
        )

        repository_context = (
            await repository_context_service.build_context(
                repository_id=REPOSITORY_ID,
                query=TASK,
                limit=20,
            )
        )

        print(
            f"Retrieved context items: "
            f"{len(repository_context.items)}"
        )
        print()

        # ------------------------------------------------------------------
        # STEP 2 — CHANGE CONTEXT
        # ------------------------------------------------------------------

        print("=" * 100)
        print("STEP 2 — REAL CHANGE CONTEXT")
        print("=" * 100)

        change_context_service = (
            await create_change_context_service(
                session=session,
                settings=settings,
                repository_id=REPOSITORY_ID,
                repository_path=repository_path,
                task_description=TASK,
            )
        )

        change_context = await change_context_service.build(
            repository_id=REPOSITORY_ID,
            task_description=TASK,
            context_limit=20,
        )

        print(
            f"Change-context files: "
            f"{len(change_context.files)}"
        )
        print(
            f"Change-context symbols: "
            f"{len(change_context.symbols)}"
        )
        print(
            f"Change-context dependencies: "
            f"{len(change_context.dependencies)}"
        )
        print()

        # ------------------------------------------------------------------
        # STEP 3 — LOCKED APPROVED PLAN
        # ------------------------------------------------------------------

        print("=" * 100)
        print("STEP 3 — LOCKED APPROVED PLAN")
        print("=" * 100)

        plan = build_locked_plan()

        print("Using previously validated planner output.")
        print("Live planner execution is intentionally disabled for this E2E.")
        print()
        print("PLAN LOCKED SUCCESSFULLY")
        print("-" * 100)
        print(f"Summary: {plan.summary}")
        print()

        print("Files to modify:")
        for item in plan.files_to_modify:
            print(
                f"  - {item.file_path}: "
                f"{item.reason}"
            )

        print()

        print("Files to create:")
        for item in plan.files_to_create:
            print(
                f"  - {item.file_path}: "
                f"{item.reason}"
            )

        print()

        print("Test files:")
        for item in plan.test_files:
            print(
                f"  - {item.file_path}: "
                f"{item.reason}"
            )

        print()

        print("Implementation steps:")
        for step in plan.implementation_steps:
            print(
                f"  {step.order}. "
                f"[{step.step_type.value}] "
                f"{step.description}"
            )

        print()

        print("Tests:")
        for test in plan.tests_to_add:
            print(f"  - {test}")

        print()

        print("Validation commands:")
        for command in plan.validation_commands:
            print(f"  - {command}")

        print()

        if not plan.validation_commands:
            raise RuntimeError(
                "Approved plan contains no validation commands."
            )

        validation_command = plan.validation_commands[0]

        # ------------------------------------------------------------------
        # STEP 4 — PLAN-AWARE IMPLEMENTATION CONTEXT
        # ------------------------------------------------------------------

        print("=" * 100)
        print("STEP 4 — PLAN-AWARE IMPLEMENTATION CONTEXT")
        print("=" * 100)

        implementation_context_service = ImplementationContextService()

        implementation_context = implementation_context_service.build(
            repository_id=REPOSITORY_ID,
            repository_path=repository_path,
            task_description=TASK,
            change_context=change_context,
            plan=plan,
        )

        print(
            f"Context files: "
            f"{len(implementation_context.files)}"
        )
        print(
            f"Total source chars: "
            f"{sum(len(item.content) for item in implementation_context.files)}"
        )
        print(
            f"Relevant symbols: "
            f"{len(implementation_context.symbols)}"
        )
        print(
            f"Dependencies: "
            f"{len(implementation_context.dependencies)}"
        )
        print()

        for item in implementation_context.files:
            print(f"  - {item.file_path}")

        print()

        # ------------------------------------------------------------------
        # STEP 5 — WORKSPACE
        # ------------------------------------------------------------------

        print("=" * 100)
        print("STEP 5 — CREATE ISOLATED WORKSPACE")
        print("=" * 100)

        workspace_manager = WorkspaceManager(
            workspace_root
        )

        workspace_path = (
            workspace_manager.create_from_repository(
                repository_path,
                branch_name="repopilot/real-e2e",
            )
        )

        try:
            workspace_info = workspace_manager.info(
                workspace_path
            )

            print(f"Workspace: {workspace_info.path}")
            print(
                f"Branch:    "
                f"{workspace_info.branch_name}"
            )
            print(
                f"Commit:    "
                f"{workspace_info.commit_sha}"
            )
            print(
                f"Clean:     "
                f"{workspace_info.is_clean}"
            )
            print()

            provider = create_llm_provider(settings)

            # ------------------------------------------------------------------
            # STEP 6 — REAL LLM IMPLEMENTATION
            # ------------------------------------------------------------------

            print("=" * 100)
            print("STEP 6 — REAL LLM IMPLEMENTATION")
            print("=" * 100)

            implementer = LLMImplementer(
                provider=provider,
            )

            implementation_started = time.perf_counter()

            implementation = await implementer.implement(
                implementation_context,
                plan,
                max_tokens=8192,
            )

            implementation_elapsed = (
                time.perf_counter() - implementation_started
            )

            print(
                f"Implementation completed in "
                f"{implementation_elapsed:.2f}s"
            )
            print()
            print("IMPLEMENTATION GENERATED SUCCESSFULLY")
            print("-" * 100)
            print(f"Summary: {implementation.summary}")
            print(
                f"Changes: {len(implementation.changes)}"
            )
            print()

            for change in implementation.changes:
                print(
                    f"  - [{change.operation.value}] "
                    f"{change.file_path}"
                )
                print(
                    f"    Reason: {change.reason}"
                )
                print(
                    f"    Content chars: {len(change.content)}"
                )

            print()

            # ------------------------------------------------------------------
            # STEP 7 — APPLY IMPLEMENTATION
            # ------------------------------------------------------------------

            print("=" * 100)
            print("STEP 7 — APPLY IMPLEMENTATION TO WORKSPACE")
            print("=" * 100)

            change_applier = ChangeApplier(
                workspace_path
            )

            application = change_applier.apply(
                implementation
            )

            print(
                f"Files changed: {application.files_changed}"
            )
            print(
                f"Dry run:       {application.dry_run}"
            )
            print()

            for applied_change in application.changes:
                print(
                    f"  - [{applied_change.status.value}] "
                    f"{applied_change.operation} "
                    f"{applied_change.file_path}"
                )

            print()

            # ------------------------------------------------------------------
            # STEP 8 — VERIFY WORKSPACE STATE
            # ------------------------------------------------------------------

            print("=" * 100)
            print("STEP 8 — VERIFY WORKSPACE CHANGES")
            print("=" * 100)

            status_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "status",
                    "--short",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            diff_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace_path),
                    "diff",
                    "--stat",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            status_output = status_result.stdout.strip()
            diff_output = diff_result.stdout.strip()

            print("Git status:")
            print(status_output or "(clean)")
            print()

            print("Diff stat:")
            print(diff_output or "(no diff)")
            print()

            if not status_output:
                raise RuntimeError(
                    "Implementation completed but workspace has no "
                    "tracked changes."
                )

            # ------------------------------------------------------------------
            # STEP 9 — REAL SANDBOX EXECUTION
            # ------------------------------------------------------------------

            print("=" * 100)
            print("STEP 9 — REAL SANDBOX EXECUTION")
            print("=" * 100)

            print("Approved validation command:")
            print(f"  {validation_command}")
            print()
            print("Executing inside repopilot-sandbox...")
            print()

            execution_service = ExecutionService()

            execution_started = time.perf_counter()

            execution = execution_service.execute(
                workspace_path,
                implementation,
                validation_command=validation_command,
            )

            execution_elapsed = (
                time.perf_counter() - execution_started
            )

            print(
                f"Execution completed in "
                f"{execution_elapsed:.2f}s"
            )
            print()

            # ------------------------------------------------------------------
            # STEP 10 — TEST RESULT
            # ------------------------------------------------------------------

            print("=" * 100)
            print("STEP 10 — TEST RESULT")
            print("=" * 100)

            print(
                f"Status:      {execution.tests.status.value}"
            )
            print(
                f"Exit code:   {execution.tests.exit_code}"
            )
            print(
                f"Duration:    "
                f"{execution.tests.duration_seconds:.2f}s"
            )
            print(
                f"Command:     "
                f"{' '.join(execution.tests.command)}"
            )
            print()

            print("STDOUT:")
            print(execution.tests.stdout or "(empty)")
            print()

            print("STDERR:")
            print(execution.tests.stderr or "(empty)")
            print()

            if not execution.succeeded:
                raise RuntimeError(
                    "Real sandbox execution failed. "
                    f"Test status: {execution.tests.status.value}"
                )

            print("REAL SANDBOX EXECUTION PASSED")
            print()

            # ------------------------------------------------------------------
            # STEP 11 — FINAL E2E RESULT
            # ------------------------------------------------------------------

            print("=" * 100)
            print("STEP 11 — FINAL AUTONOMOUS E2E RESULT")
            print("=" * 100)

            print("Repository context:       PASSED")
            print("Change context:           PASSED")
            print("Approved plan:            PASSED")
            print("Implementation context:   PASSED")
            print("Isolated workspace:       PASSED")
            print("Real LLM implementation: PASSED")
            print("Implementation validation:PASSED")
            print("Safe change application:  PASSED")
            print("Workspace verification:   PASSED")
            print("Sandbox execution:        PASSED")
            print("Validation tests:         PASSED")
            print()
            print("FULL REAL IMPLEMENTATION + EXECUTION E2E PASSED")
            print()

        finally:
            workspace_manager.remove(
                workspace_path
            )

    print("=" * 100)
    print("REPOPILOT — REAL IMPLEMENTATION / EXECUTION E2E PASSED")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
