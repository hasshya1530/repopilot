from typing import Protocol
from uuid import UUID

from ingestion.change_context.errors import (
    ChangeContextAnalysisError,
    ChangeContextConfigurationError,
    ChangeContextRetrievalError,
)
from ingestion.change_context.models import (
    ChangeContextDependency,
    ChangeContextFile,
    ChangeContextSymbol,
    RepositoryChangeContext,
)
from ingestion.context.models import RepositoryContext
from ingestion.graph.query.models import DependencyQuery, ImpactAnalysisResult


class RepositoryContextServiceProtocol(Protocol):
    async def build_context(
        self,
        repository_id: UUID,
        query: str,
        limit: int = 20,
    ) -> RepositoryContext:
        ...


class ImpactAnalysisServiceProtocol(Protocol):
    def analyze(
        self,
        query: DependencyQuery,
    ) -> ImpactAnalysisResult:
        ...


class ChangeContextService:
    """Build structured repository context for a proposed code change."""

    def __init__(
        self,
        context_service: RepositoryContextServiceProtocol,
        impact_service: ImpactAnalysisServiceProtocol,
    ) -> None:
        self._context_service = context_service
        self._impact_service = impact_service

    async def build(
        self,
        repository_id: UUID,
        task_description: str,
        symbol_id: UUID | None = None,
        *,
        context_limit: int = 20,
        max_depth: int = 2,
    ) -> RepositoryChangeContext:
        """Build repository context relevant to a proposed change."""

        if not task_description.strip():
            raise ChangeContextConfigurationError(
                "task_description must not be empty"
            )

        if context_limit < 1:
            raise ChangeContextConfigurationError(
                "context_limit must be at least 1"
            )

        if max_depth < 1:
            raise ChangeContextConfigurationError(
                "max_depth must be at least 1"
            )

        try:
            repository_context = await self._context_service.build_context(
                repository_id=repository_id,
                query=task_description,
                limit=context_limit,
            )
        except Exception as exc:
            raise ChangeContextRetrievalError(
                "Failed to retrieve repository context"
            ) from exc

        files = self._build_files(repository_context)
        symbols = self._build_symbols(repository_context)

        dependencies: tuple[ChangeContextDependency, ...] = ()

        if symbol_id is not None:
            try:
                impact = self._impact_service.analyze(
                    DependencyQuery(
                        symbol_id=symbol_id,
                        direction="incoming",
                        max_depth=max_depth,
                    )
                )
            except Exception as exc:
                raise ChangeContextAnalysisError(
                    "Failed to analyze repository impact"
                ) from exc

            dependencies = self._build_dependencies(impact)

        return RepositoryChangeContext(
            repository_id=repository_id,
            task_description=task_description,
            files=files,
            symbols=symbols,
            dependencies=dependencies,
        )

    @staticmethod
    def _build_files(
        context: RepositoryContext,
    ) -> tuple[ChangeContextFile, ...]:
        """Convert retrieved context items into relevant files."""

        files: list[ChangeContextFile] = []
        seen: set[str] = set()

        for item in context.items:
            if item.file_path in seen:
                continue

            seen.add(item.file_path)

            files.append(
                ChangeContextFile(
                    file_path=item.file_path,
                    reason="semantic repository match",
                    relevance_score=item.score,
                )
            )

        return tuple(files)

    @staticmethod
    def _build_symbols(
        context: RepositoryContext,
    ) -> tuple[ChangeContextSymbol, ...]:
        """Convert retrieved context items into relevant symbols."""

        symbols: list[ChangeContextSymbol] = []
        seen: set[UUID] = set()

        for item in context.items:
            if item.chunk_id in seen:
                continue

            seen.add(item.chunk_id)

            symbols.append(
                ChangeContextSymbol(
                    symbol_id=item.chunk_id,
                    file_path=item.file_path,
                    name=item.symbol_name,
                    symbol_type=item.symbol_type,
                    start_line=item.start_line,
                    end_line=item.end_line,
                    reason="semantic repository match",
                )
            )

        return tuple(symbols)

    @staticmethod
    def _build_dependencies(
        impact: ImpactAnalysisResult,
    ) -> tuple[ChangeContextDependency, ...]:
        """Convert impact analysis dependencies into change context dependencies."""

        return tuple(
            ChangeContextDependency(
                source_symbol_id=dependency.source,
                target_symbol_id=dependency.target,
                relation=dependency.relation.value,
                depth=dependency.depth,
            )
            for dependency in impact.dependencies
        )
