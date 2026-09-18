from pathlib import Path
from uuid import uuid4

import pytest

from apps.api.app.services.repository_intelligence import (
    RelationshipParserRegistry,
    create_change_context_service,
    create_relationship_extraction_service,
    create_repository_context_service,
)
from ingestion.graph.parsers import PythonRelationshipParser


class FakeSettings:
    embedding_provider = "ollama"
    embedding_model = "nomic-embed-text"
    ollama_base_url = "http://localhost:11434"


def test_relationship_parser_registry_registers_python() -> None:
    registry = RelationshipParserRegistry()

    parser = registry.get_parser(".py")

    assert isinstance(parser, PythonRelationshipParser)


def test_relationship_parser_registry_is_case_insensitive() -> None:
    registry = RelationshipParserRegistry()

    parser = registry.get_parser(".PY")

    assert isinstance(parser, PythonRelationshipParser)


def test_relationship_parser_registry_returns_none_for_unknown_extension() -> None:
    registry = RelationshipParserRegistry()

    assert registry.get_parser(".unknown") is None


def test_create_relationship_extraction_service() -> None:
    service = create_relationship_extraction_service()

    assert service is not None


@pytest.mark.asyncio
async def test_create_change_context_service_builds_repository_specific_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeEmbeddingProvider:
        async def embed(self, text: str) -> list[float]:
            return [0.0] * 768

    class FakeContextService:
        async def build_context(
            self,
            *,
            repository_id,
            query,
            limit,
        ):
            from ingestion.context.models import RepositoryContext

            return RepositoryContext(
                repository_id=repository_id,
                query=query,
                items=(),
            )

    class FakeGraph:
        repository_id = uuid4()
        symbols = ()
        edges = ()

    class FakeGraphService:
        def __init__(self, context_service, relationship_extraction_service):
            self.context_service = context_service
            self.relationship_extraction_service = (
                relationship_extraction_service
            )

        async def build_graph(
            self,
            *,
            repository_id,
            query,
            limit,
            repository_path,
        ):
            assert repository_id is not None
            assert query == "Improve authentication"
            assert limit == 20
            assert repository_path == Path("/tmp/repository")

            return FakeGraph()

    class FakeTraversalService:
        def __init__(self, graph):
            self.graph = graph

    class FakeImpactService:
        def __init__(self, graph, traversal_service):
            self.graph = graph
            self.traversal_service = traversal_service

        def analyze(self, query):
            raise AssertionError("Not called during construction")

    class FakeChangeContextService:
        def __init__(self, context_service, impact_service):
            self.context_service = context_service
            self.impact_service = impact_service

    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.create_embedding_provider",
        lambda settings: FakeEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.CodeRetrievalService",
        lambda session, embedding_provider: object(),
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.RepositoryContextService",
        lambda retrieval_service: FakeContextService(),
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.RepositoryGraphService",
        FakeGraphService,
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.DependencyTraversalService",
        FakeTraversalService,
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.ImpactAnalysisService",
        FakeImpactService,
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.ChangeContextService",
        FakeChangeContextService,
    )

    result = await create_change_context_service(
        session=object(),
        settings=FakeSettings(),
        repository_id=uuid4(),
        repository_path=Path("/tmp/repository"),
        task_description="Improve authentication",
    )

    assert isinstance(result, FakeChangeContextService)
    assert isinstance(result.impact_service, FakeImpactService)
    assert isinstance(result.impact_service.traversal_service, FakeTraversalService)


def test_create_repository_context_service_uses_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class FakeEmbeddingProvider:
        pass

    class FakeRetrievalService:
        def __init__(self, *, session, embedding_provider):
            captured["session"] = session
            captured["embedding_provider"] = embedding_provider

    class FakeContextService:
        def __init__(self, retrieval_service):
            captured["retrieval_service"] = retrieval_service

    provider = FakeEmbeddingProvider()
    session = object()

    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.create_embedding_provider",
        lambda settings: provider,
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.CodeRetrievalService",
        FakeRetrievalService,
    )
    monkeypatch.setattr(
        "apps.api.app.services.repository_intelligence.RepositoryContextService",
        FakeContextService,
    )

    result = create_repository_context_service(
        session=session,
        settings=FakeSettings(),
    )

    assert isinstance(result, FakeContextService)
    assert captured["session"] is session
    assert captured["embedding_provider"] is provider
