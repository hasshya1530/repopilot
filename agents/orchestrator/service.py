from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from agents.approval.models import ApprovalRequest
from agents.debugger.models import DebuggerResult
from agents.implementer.models import ImplementationResult
from agents.orchestrator.errors import (
    OrchestrationConfigurationError,
    OrchestrationExecutionError,
)
from agents.orchestrator.models import (
    OrchestrationArtifacts,
    OrchestrationResult,
    OrchestrationState,
    OrchestrationStatus,
    OrchestrationStepType,
)
from agents.orchestrator.protocols import OrchestrationDependencies
from agents.orchestrator.transitions import transition
from agents.reviewer.models import ReviewDecision
from apps.api.app.models.task import TaskStatus


@dataclass(frozen=True, slots=True)
class OrchestrationConfig:
    context_limit: int = 20
    max_depth: int = 2
    planner_max_tokens: int = 4096
    implementer_max_tokens: int = 8192
    max_debug_attempts: int = 3


class OrchestrationService:
    def __init__(
        self,
        dependencies: OrchestrationDependencies,
        *,
        config: OrchestrationConfig | None = None,
    ) -> None:
        self._dependencies = dependencies
        self._config = config or OrchestrationConfig()

        if self._config.max_debug_attempts < 0:
            raise OrchestrationConfigurationError(
                "max_debug_attempts cannot be negative."
            )

    async def run(
        self,
        task_id: UUID,
    ) -> OrchestrationResult:
        task = await self._dependencies.persistence.get_task(task_id)

        if task is None:
            raise OrchestrationExecutionError(
                f"Task {task_id} was not found."
            )

        if task.status != TaskStatus.PENDING:
            raise OrchestrationExecutionError(
                f"Task {task_id} cannot start from status "
                f"{task.status.value!r}."
            )

        repository = await self._dependencies.persistence.get_repository(
            task.repository_id
        )

        if repository is None:
            raise OrchestrationExecutionError(
                f"Repository {task.repository_id} was not found."
            )

        state = OrchestrationState(
            task_id=task.id,
            repository_id=repository.id,
            status=OrchestrationStatus.PENDING,
            max_debug_attempts=self._config.max_debug_attempts,
        )

        artifacts = OrchestrationArtifacts()
        workspace_path: Path | None = None

        try:
            task_description = task.description or task.title

            # ---------------------------------------------------------
            # 1. UNDERSTANDING
            # ---------------------------------------------------------
            state = transition(
                state,
                OrchestrationStatus.UNDERSTANDING,
                current_step=OrchestrationStepType.UNDERSTAND,
            )

            repository_path = (
                await self._dependencies.repository_source.prepare(
                    repository
                )
            )

            planning_context = (
                await self._dependencies.planning_context_builder.build(
                    repository.id,
                    task_description,
                    repository_path,
                    context_limit=self._config.context_limit,
                    max_depth=self._config.max_depth,
                )
            )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
            )

            # ---------------------------------------------------------
            # 2. PLANNING
            # ---------------------------------------------------------
            state = await self._set_task_status(
                task_id,
                state,
                TaskStatus.PLANNING,
            )

            state = transition(
                state,
                OrchestrationStatus.PLANNING,
                current_step=OrchestrationStepType.PLAN,
            )

            planner = self._dependencies.planner
            generate_plan = getattr(planner, "generate_plan", None)

            if callable(generate_plan):
                plan = await generate_plan(
                    planning_context,
                    max_tokens=self._config.planner_max_tokens,
                )
            else:
                # Backward compatibility for legacy planner test doubles.
                legacy_plan = getattr(planner, "plan", None)

                if not callable(legacy_plan):
                    raise TypeError(
                        "Planner dependency must provide either "
                        "generate_plan() or plan()."
                    )

                plan = await legacy_plan(
                    repository.id,
                    task_description,
                    context_limit=self._config.context_limit,
                    max_depth=self._config.max_depth,
                    max_tokens=self._config.planner_max_tokens,
                )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
                plan=plan,
            )

            # ---------------------------------------------------------
            # 3. BUILD IMPLEMENTATION CONTEXT
            # ---------------------------------------------------------
            change_context = planning_context.change_context

            if change_context is None:
                return await self._fail(
                    task_id,
                    state,
                    "Planning context is missing repository change context.",
                )

            implementation_context = (
                self._dependencies.implementation_context_builder.build(
                    repository_id=repository.id,
                    repository_path=repository_path,
                    task_description=task_description,
                    change_context=change_context,
                    plan=plan,
                )
            )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
                plan=plan,
                implementation_context=implementation_context,
            )

            # ---------------------------------------------------------
            # 4. IMPLEMENTATION
            # ---------------------------------------------------------
            state = await self._set_task_status(
                task_id,
                state,
                TaskStatus.IMPLEMENTING,
            )

            state = transition(
                state,
                OrchestrationStatus.IMPLEMENTING,
                current_step=OrchestrationStepType.IMPLEMENT,
            )

            implementation = (
                await self._dependencies.implementer.implement(
                    implementation_context,
                    plan,
                    max_tokens=self._config.implementer_max_tokens,
                )
            )

            if not implementation.changes:
                return await self._fail(
                    task_id,
                    state,
                    "Implementation produced no changes.",
                )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
                plan=plan,
                implementation_context=implementation_context,
                implementation=implementation,
            )

            # ---------------------------------------------------------
            # 5. CREATE ISOLATED WORKSPACE
            # ---------------------------------------------------------
            workspace_path = (
                self._dependencies.workspace.create_from_repository(
                    repository_path
                )
            )

            # ---------------------------------------------------------
            # 6. TESTING
            # ---------------------------------------------------------
            state = await self._set_task_status(
                task_id,
                state,
                TaskStatus.TESTING,
            )

            state = transition(
                state,
                OrchestrationStatus.TESTING,
                current_step=OrchestrationStepType.EXECUTE,
            )

            execution = self._dependencies.execution.execute(
                workspace_path,
                implementation,
            )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
                plan=plan,
                implementation_context=implementation_context,
                implementation=implementation,
                execution=execution,
            )

            # ---------------------------------------------------------
            # 7. DEBUGGING / SELF-REPAIR
            # ---------------------------------------------------------
            if not execution.succeeded:
                state = transition(
                    state,
                    OrchestrationStatus.DEBUGGING,
                    current_step=OrchestrationStepType.DEBUG,
                    attempt=1,
                )

                debugger = await self._dependencies.debugger.debug(
                    workspace_path,
                    implementation_context,
                )

                if not debugger.succeeded:
                    return await self._fail(
                        task_id,
                        state,
                        "Automated debugging could not produce "
                        "a passing test result.",
                    )

                implementation = self._merge_debugger_changes(
                    implementation,
                    debugger,
                )

                artifacts = OrchestrationArtifacts(
                    planning_context=planning_context,
                    plan=plan,
                    implementation_context=implementation_context,
                    implementation=implementation,
                    execution=artifacts.execution,
                    debugger=debugger,
                )

                state = transition(
                    state,
                    OrchestrationStatus.TESTING,
                    current_step=OrchestrationStepType.EXECUTE,
                    attempt=len(debugger.attempts),
                )

                if debugger.final_test_result.status.value != "passed":
                    return await self._fail(
                        task_id,
                        state,
                        "Tests still fail after debugging.",
                    )

            # ---------------------------------------------------------
            # 8. REVIEW
            # ---------------------------------------------------------
            state = await self._set_task_status(
                task_id,
                state,
                TaskStatus.REVIEWING,
            )

            state = transition(
                state,
                OrchestrationStatus.REVIEWING,
                current_step=OrchestrationStepType.REVIEW,
            )

            review = await self._dependencies.reviewer.review(
                context=implementation_context,
                implementation=implementation,
            )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
                plan=plan,
                implementation_context=implementation_context,
                implementation=implementation,
                execution=artifacts.execution,
                debugger=artifacts.debugger,
                review=review,
            )

            if review.decision == ReviewDecision.REQUEST_CHANGES:
                return await self._fail(
                    task_id,
                    state,
                    "Code review requested changes.",
                )

            # ---------------------------------------------------------
            # 9. CREATE PULL REQUEST
            # ---------------------------------------------------------
            state = transition(
                state,
                OrchestrationStatus.CREATING_PR,
                current_step=OrchestrationStepType.CREATE_PR,
            )

            branch_name = (
                task.branch_name
                or f"repopilot/{task.id.hex[:12]}"
            )

            pull_request = (
                await self._dependencies.pull_request
                .create_pull_request_from_implementation(
                    repository=repository,
                    task=task,
                    implementation=implementation,
                    branch_name=branch_name,
                    title=task.title,
                    body=(
                        f"Automated implementation for task "
                        f"`{task.title}`.\n\n"
                        f"{review.summary}"
                    ),
                )
            )

            artifacts = OrchestrationArtifacts(
                planning_context=planning_context,
                plan=plan,
                implementation_context=implementation_context,
                implementation=implementation,
                execution=artifacts.execution,
                debugger=artifacts.debugger,
                review=review,
                pull_request=pull_request,
            )

            # ---------------------------------------------------------
            # 10. WAIT FOR HUMAN APPROVAL
            # ---------------------------------------------------------
            state = await self._set_task_status(
                task_id,
                state,
                TaskStatus.WAITING_APPROVAL,
            )

            state = transition(
                state,
                OrchestrationStatus.WAITING_APPROVAL,
                current_step=OrchestrationStepType.APPROVAL,
            )

            return OrchestrationResult(
                task_id=task_id,
                status=state.status,
                summary=(
                    "Implementation completed, passed tests, "
                    "passed automated review, and is awaiting "
                    "human approval."
                ),
                pull_request_id=pull_request.id,
                metadata={
                    "branch_name": branch_name,
                    "review_summary": review.summary,
                },
            )

        except OrchestrationExecutionError:
            await self._dependencies.persistence.update_task_status(
                task_id,
                TaskStatus.FAILED,
            )
            raise

        except Exception as exc:
            await self._dependencies.persistence.update_task_status(
                task_id,
                TaskStatus.FAILED,
            )

            raise OrchestrationExecutionError(
                f"Orchestration failed for task {task_id}: {exc}"
            ) from exc

        finally:
            if workspace_path is not None:
                self._dependencies.workspace.remove(
                    workspace_path
                )

    async def resume_approval(
        self,
        task_id: UUID,
        pull_request_id: UUID,
    ) -> OrchestrationResult:
        task = await self._dependencies.persistence.get_task(task_id)

        if task is None:
            raise OrchestrationExecutionError(
                f"Task {task_id} was not found."
            )

        if task.status != TaskStatus.WAITING_APPROVAL:
            raise OrchestrationExecutionError(
                f"Task {task_id} cannot resume approval from "
                f"status {task.status.value!r}."
            )

        approval = await self._dependencies.approval.get_status(
            ApprovalRequest(
                pull_request_id=pull_request_id
            )
        )

        if approval.pending:
            return OrchestrationResult(
                task_id=task_id,
                status=OrchestrationStatus.WAITING_APPROVAL,
                summary="Human approval is still required.",
                pull_request_id=pull_request_id,
                metadata={
                    "approval_status": approval.status.value
                },
            )

        if approval.rejected:
            state = OrchestrationState(
                task_id=task_id,
                repository_id=task.repository_id,
                status=OrchestrationStatus.WAITING_APPROVAL,
                current_step=OrchestrationStepType.APPROVAL,
            )

            return await self._fail(
                task_id,
                state,
                "Human approval was rejected.",
            )

        updated = await self._dependencies.persistence.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
        )

        if updated is None:
            raise OrchestrationExecutionError(
                f"Task {task_id} disappeared while completing approval."
            )

        return OrchestrationResult(
            task_id=task_id,
            status=OrchestrationStatus.COMPLETED,
            summary="Human approval received; task completed.",
            pull_request_id=pull_request_id,
            metadata={
                "approval_status": approval.status.value
            },
        )

    async def _set_task_status(
        self,
        task_id: UUID,
        state: OrchestrationState,
        task_status: TaskStatus,
    ) -> OrchestrationState:
        updated = await self._dependencies.persistence.update_task_status(
            task_id,
            task_status,
        )

        if updated is None:
            raise OrchestrationExecutionError(
                f"Task {task_id} disappeared while updating "
                f"its status."
            )

        return state

    async def _fail(
        self,
        task_id: UUID,
        state: OrchestrationState,
        error: str,
    ) -> OrchestrationResult:
        failed_state = transition(
            state,
            OrchestrationStatus.FAILED,
            error=error,
        )

        updated = await self._dependencies.persistence.update_task_status(
            task_id,
            TaskStatus.FAILED,
        )

        if updated is None:
            raise OrchestrationExecutionError(
                f"Task {task_id} disappeared while marking it failed."
            )

        return OrchestrationResult(
            task_id=task_id,
            status=failed_state.status,
            summary="Orchestration failed.",
            error=error,
        )

    @staticmethod
    def _merge_debugger_changes(
        implementation: ImplementationResult,
        debugger: DebuggerResult,
    ) -> ImplementationResult:
        changes_by_path = {
            change.file_path: change
            for change in implementation.changes
        }

        for attempt in debugger.attempts:
            for change in attempt.changes:
                changes_by_path[change.file_path] = change

        return ImplementationResult(
            summary=(
                f"{implementation.summary} "
                f"Applied {len(debugger.attempts)} debugger repair attempt(s)."
            ),
            changes=tuple(changes_by_path.values()),
        )
