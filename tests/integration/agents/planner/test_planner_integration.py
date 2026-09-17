from pathlib import Path
from uuid import uuid4

import pytest

from agents.llm.factory import create_llm_provider
from agents.planner.llm_planner import LLMPlanner
from agents.planner.orchestrator import PlannerOrchestrator
from agents.planner.service import PlanningContextService
from apps.api.app.core.config import get_settings
from apps.api.app.core.database import async_session_factory
from ingestion.change_context.service import ChangeContextService
from ingestion.context.service import RepositoryContextService
from ingestion.embeddings.factory import create_embedding_provider
from ingestion.graph.query import DependencyQuery, ImpactAnalysisResult
from ingestion.indexing.service import RepositoryIndexingService
from ingestion.retrieval.service import CodeRetrievalService
from ingestion.services.embedding import EmbeddingService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_planner(tmp_path: Path) -> None:
    settings = get_settings()

    if settings.model_provider != "ollama":
        pytest.skip("Ollama must be the configured LLM provider.")

    repository_path = tmp_path / "sample_repo"
    repository_path.mkdir()

    (repository_path / "auth.py").write_text(
        """
def validate_token(token: str) -> bool:
    return token == "valid"


def login(token: str) -> bool:
    return validate_token(token)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (repository_path / "service.py").write_text(
        """
from auth import validate_token


def authenticate(token: str) -> bool:
    return validate_token(token)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    embedding_provider = create_embedding_provider(settings)
    embedding_service = EmbeddingService(embedding_provider)

    provider = create_llm_provider(
        provider=settings.model_provider,
        model_name=settings.model_name,
        ollama_base_url=settings.ollama_base_url,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
    )

    planner = LLMPlanner(provider)

    async with async_session_factory() as session:
        from apps.api.app.models.repository import Repository

        test_id = uuid4().hex[:12]
        github_repo_id = int(test_id, 16) % 1_000_000_000

        repository = Repository(
            owner="integration",
            name=f"planner-e2e-{test_id}",
            full_name=f"integration/planner-e2e-{test_id}",
            github_repo_id=github_repo_id,
            default_branch="main",
            description="Planner integration test repository",
            is_private=False,
            clone_url=f"https://github.com/integration/planner-e2e-{test_id}.git",
        )

        session.add(repository)
        await session.commit()
        await session.refresh(repository)

        indexing_service = RepositoryIndexingService(
            session=session,
            embedding_service=embedding_service,
        )

        indexing_result = await indexing_service.index_repository(
            repository_id=repository.id,
            repository_path=repository_path,
            commit_sha="planner-integration-test",
        )

        assert indexing_result.discovered_files == 2
        assert indexing_result.parsed_files == 2
        assert indexing_result.chunks_created > 0
        assert indexing_result.embeddings_created > 0

        retrieval_service = CodeRetrievalService(
            session=session,
            embedding_provider=embedding_provider,
        )

        repository_context_service = RepositoryContextService(
            retrieval_service=retrieval_service,
        )

        # No symbol_id is supplied in this first E2E test, so
        # ChangeContextService does not require graph impact analysis.
        change_context_service = ChangeContextService(
            context_service=repository_context_service,
            impact_service=_UnusedImpactService(),
        )

        planning_context_service = PlanningContextService(
            change_context_service=change_context_service,
        )

        orchestrator = PlannerOrchestrator(
            context_service=planning_context_service,
            planner=planner,
        )

        plan = await orchestrator.plan(
            repository_id=repository.id,
            task_description=(
                "Improve authentication token validation and add "
                "regression tests for invalid tokens."
            ),
            context_limit=10,
            max_depth=2,
            max_tokens=1024,
        )

    assert plan.summary
    assert plan.implementation_steps
    assert plan.tests_to_add
    assert plan.validation_commands

    repository_files = {
        "auth.py",
        "service.py",
    }

    planned_files = {
        path.split("/")[-1]
        for path in (
            [file.file_path for file in plan.files_to_modify]
            + [file.file_path for file in plan.files_to_create]
        )
    }

    assert planned_files.intersection(repository_files)


class _UnusedImpactService:
    def analyze(self, query: DependencyQuery) -> ImpactAnalysisResult:
        raise AssertionError("Impact analysis should not be called when symbol_id is None.")
