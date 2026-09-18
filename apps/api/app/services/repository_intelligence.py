from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import Settings
from ingestion.change_context.service import ChangeContextService
from ingestion.context.service import RepositoryContextService
from ingestion.embeddings.factory import create_embedding_provider
from ingestion.graph.extraction.service import (
    RepositoryRelationshipExtractionService,
)
from ingestion.graph.parsers import PythonRelationshipParser
from ingestion.graph.query.impact import ImpactAnalysisService
from ingestion.graph.query.traversal import DependencyTraversalService
from ingestion.graph.service import RepositoryGraphService
from ingestion.retrieval.service import CodeRetrievalService


class RelationshipParserRegistry:
    """Registry for repository relationship parsers."""

    def __init__(self) -> None:
        self._parsers: dict[str, Any] = {
            ".py": PythonRelationshipParser(),
        }

    def get_parser(self, extension: str) -> Any:
        """Return a parser for the supplied file extension."""
        return self._parsers.get(extension.lower())


def create_relationship_extraction_service() -> (
    RepositoryRelationshipExtractionService
):
    """Create the repository relationship extraction service."""

    parser_registry = RelationshipParserRegistry()

    return RepositoryRelationshipExtractionService(
        parser_registry=parser_registry,
    )


def create_repository_context_service(
    *,
    session: AsyncSession,
    settings: Settings,
) -> RepositoryContextService:
    """Create the repository context service."""

    embedding_provider = create_embedding_provider(settings)

    retrieval_service = CodeRetrievalService(
        session=session,
        embedding_provider=embedding_provider,
    )

    return RepositoryContextService(
        retrieval_service=retrieval_service,
    )


async def create_change_context_service(
    *,
    session: AsyncSession,
    settings: Settings,
    repository_id: UUID,
    repository_path: Path,
    task_description: str,
    context_limit: int = 20,
    graph_limit: int = 20,
) -> ChangeContextService:
    """Create repository-specific change context."""

    context_service = create_repository_context_service(
        session=session,
        settings=settings,
    )

    relationship_extraction_service = (
        create_relationship_extraction_service()
    )

    graph_service = RepositoryGraphService(
        context_service=context_service,
        relationship_extraction_service=relationship_extraction_service,
    )

    graph = await graph_service.build_graph(
        repository_id=repository_id,
        query=task_description,
        limit=graph_limit or context_limit,
        repository_path=repository_path,
    )

    traversal_service = DependencyTraversalService(graph)

    impact_service = ImpactAnalysisService(
        graph=graph,
        traversal_service=traversal_service,
    )

    return ChangeContextService(
        context_service=context_service,
        impact_service=impact_service,
    )
