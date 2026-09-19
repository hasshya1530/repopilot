from __future__ import annotations

from uuid import UUID

from ingestion.retrieval.lexical import CodeLexicalRetrievalService
from ingestion.retrieval.models import RetrievalResult
from ingestion.retrieval.ranking import RankedRetrievalResult, RetrievalRanker
from ingestion.retrieval.service import CodeRetrievalService


class HybridCodeRetrievalService:
    """Combine semantic and lexical repository retrieval."""

    def __init__(
        self,
        *,
        semantic_service: CodeRetrievalService,
        lexical_service: CodeLexicalRetrievalService,
        ranker: RetrievalRanker | None = None,
    ) -> None:
        self._semantic_service = semantic_service
        self._lexical_service = lexical_service
        self._ranker = ranker or RetrievalRanker()

    async def search(
        self,
        *,
        repository_id: UUID,
        query: str,
        limit: int = 10,
        semantic_limit: int | None = None,
        lexical_limit: int | None = None,
        commit_sha: str | None = None,
        min_semantic_score: float | None = None,
    ) -> list[RankedRetrievalResult]:
        """Retrieve and rank candidates from semantic and lexical search."""

        if not query.strip() or limit <= 0:
            return []

        candidate_limit = max(limit, 10)

        semantic_candidates = await self._semantic_service.search(
            repository_id=repository_id,
            query=query,
            limit=semantic_limit or candidate_limit,
            commit_sha=commit_sha,
            min_score=min_semantic_score,
        )

        lexical_candidates = await self._lexical_service.search(
            repository_id=repository_id,
            query=query,
            limit=lexical_limit or candidate_limit,
            commit_sha=commit_sha,
        )

        candidates = self._merge_candidates(
            semantic_candidates,
            lexical_candidates,
        )

        ranked = self._ranker.rank(
            query=query,
            candidates=candidates,
        )

        return ranked[:limit]

    @staticmethod
    def _merge_candidates(
        semantic_candidates: list[RetrievalResult],
        lexical_candidates: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Deduplicate candidates while preserving the strongest signals."""

        candidates_by_id: dict[UUID, RetrievalResult] = {}

        for candidate in semantic_candidates:
            candidates_by_id[candidate.chunk_id] = candidate

        for candidate in lexical_candidates:
            existing = candidates_by_id.get(candidate.chunk_id)

            if existing is None:
                candidates_by_id[candidate.chunk_id] = candidate
                continue

            if candidate.score > existing.score:
                candidates_by_id[candidate.chunk_id] = RetrievalResult(
                    chunk_id=existing.chunk_id,
                    repository_id=existing.repository_id,
                    file_path=existing.file_path,
                    content=existing.content,
                    symbol_name=existing.symbol_name,
                    symbol_type=existing.symbol_type,
                    start_line=existing.start_line,
                    end_line=existing.end_line,
                    parent=existing.parent,
                    score=candidate.score,
                )

        return list(candidates_by_id.values())
