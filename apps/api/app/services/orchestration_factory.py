from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from agents.approval.repository import SQLAlchemyApprovalRepository
from agents.approval.service import ApprovalService
from agents.debugger.repair_generator import RepairGenerator
from agents.debugger.service import DebuggerService
from agents.execution.service import ExecutionService
from agents.implementer.context.service import ImplementationContextService
from agents.implementer.llm_implementer import LLMImplementer
from agents.llm.factory import create_llm_provider
from agents.orchestrator.adapters.artifacts import SqlAlchemyArtifactPersistence
from agents.orchestrator.adapters.persistence import SqlAlchemyTaskPersistence
from agents.orchestrator.adapters.planning_context import (
    RepositoryAwarePlanningContextBuilder,
)
from agents.orchestrator.adapters.repository_source import LocalRepositorySource
from agents.orchestrator.protocols import OrchestrationDependencies
from agents.orchestrator.service import OrchestrationService
from agents.planner.llm_planner import LLMPlanner
from agents.reviewer.llm_reviewer import LLMReviewer
from agents.reviewer.service import ReviewerService
from agents.sandbox.config import SandboxConfig
from agents.sandbox.executor import DockerSandboxExecutor
from agents.testing.runner import TestRunner
from agents.workspace.service import WorkspaceManager
from apps.api.app.core.config import Settings, get_settings
from apps.api.app.services.github.service import GitHubService
from tools.github.client import GitHubClient


def create_orchestration_service(
    session: AsyncSession,
    *,
    settings: Settings | None = None,
) -> OrchestrationService:
    """Build the complete RepoPilot orchestration dependency graph."""

    resolved_settings = settings or get_settings()

    if not resolved_settings.github_token.strip():
        raise ValueError(
            "GITHUB_TOKEN must be configured before running RepoPilot orchestration."
        )

    repository_source_root = (
        Path(resolved_settings.repository_source_root)
        .expanduser()
        .resolve()
    )

    workspace_root = (
        Path(resolved_settings.workspace_root)
        .expanduser()
        .resolve()
    )

    provider = create_llm_provider(
        provider=resolved_settings.model_provider,
        model_name=resolved_settings.model_name,
        ollama_base_url=resolved_settings.ollama_base_url,
        openrouter_base_url=resolved_settings.openrouter_base_url,
        openrouter_api_key=resolved_settings.openrouter_api_key,
        openrouter_site_url=resolved_settings.openrouter_site_url,
        openrouter_app_name=resolved_settings.openrouter_app_name,
    )

    # ---------------------------------------------------------
    # Planning
    # ---------------------------------------------------------

    planner = LLMPlanner(provider)

    planning_context_builder = RepositoryAwarePlanningContextBuilder(
        session=session,
        settings=resolved_settings,
    )

    # ---------------------------------------------------------
    # Implementation
    # ---------------------------------------------------------

    implementer = LLMImplementer(provider)

    implementation_context_builder = ImplementationContextService()

    # ---------------------------------------------------------
    # Sandbox + testing
    # ---------------------------------------------------------

    sandbox_config = SandboxConfig(
        image=resolved_settings.sandbox_image,
        timeout_seconds=resolved_settings.sandbox_timeout_seconds,
        memory_limit=resolved_settings.sandbox_memory_limit,
        cpu_limit=float(resolved_settings.sandbox_cpu_limit),
        network_disabled=True,
        read_only=False,
    )

    sandbox_executor = DockerSandboxExecutor(
        config=sandbox_config,
    )

    test_runner = TestRunner(
        sandbox_executor=sandbox_executor,
    )

    execution_service = ExecutionService(
        test_runner=test_runner,
    )

    # ---------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------

    persistence = SqlAlchemyTaskPersistence(
        session=session,
    )

    artifacts = SqlAlchemyArtifactPersistence(
        session=session,
        model_provider=resolved_settings.model_provider,
        model_name=resolved_settings.model_name,
    )

    # ---------------------------------------------------------
    # Self-debugging
    # ---------------------------------------------------------

    debugger = DebuggerService(
        repair_generator=RepairGenerator(provider),
        test_runner=test_runner,
        max_attempts=3,
        artifact_persistence=artifacts,
    )

    # ---------------------------------------------------------
    # Automated review
    # ---------------------------------------------------------

    reviewer = ReviewerService(
        reviewer=LLMReviewer(provider),
    )

    # ---------------------------------------------------------
    # Human approval
    # ---------------------------------------------------------

    approval = ApprovalService(
        repository=SQLAlchemyApprovalRepository(session),
    )

    # ---------------------------------------------------------
    # GitHub
    # ---------------------------------------------------------

    github_client = GitHubClient(
        resolved_settings.github_token,
    )

    github_service = GitHubService(
        client=github_client,
        session=session,
    )

    # ---------------------------------------------------------
    # Repository source
    # ---------------------------------------------------------

    repositories: dict[str, Path] = {}

    if resolved_settings.github_e2e_repository.strip():
        repositories[resolved_settings.github_e2e_repository] = (
            repository_source_root
        )

    repository_source = LocalRepositorySource(
        repositories=repositories,
    )

    # ---------------------------------------------------------
    # Isolated workspaces
    # ---------------------------------------------------------

    workspace_manager = WorkspaceManager(
        root_path=workspace_root,
    )

    # ---------------------------------------------------------
    # Orchestration dependency graph
    # ---------------------------------------------------------

    dependencies = OrchestrationDependencies(
        persistence=persistence,
        artifacts=artifacts,
        repository_source=repository_source,
        planning_context_builder=planning_context_builder,
        planner=planner,
        implementation_context_builder=implementation_context_builder,
        implementer=implementer,
        workspace=workspace_manager,
        execution=execution_service,
        debugger=debugger,
        reviewer=reviewer,
        approval=approval,
        pull_request=github_service,
    )

    return OrchestrationService(
        dependencies=dependencies,
    )
