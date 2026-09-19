from __future__ import annotations

import re
from dataclasses import dataclass

from ingestion.retrieval.models import RetrievalResult


@dataclass(frozen=True, slots=True)
class RankingWeights:
    """Weights used to combine semantic and lexical retrieval signals."""

    semantic: float = 0.70
    file_path: float = 0.12
    symbol_name: float = 0.10
    lexical: float = 0.08

    def __post_init__(self) -> None:
        weights = (
            self.semantic,
            self.file_path,
            self.symbol_name,
            self.lexical,
        )

        if any(weight < 0.0 for weight in weights):
            raise ValueError("Ranking weights must be non-negative.")

        total = sum(weights)

        if total <= 0.0:
            raise ValueError("At least one ranking weight must be greater than zero.")


@dataclass(frozen=True, slots=True)
class RankedRetrievalResult:
    """A retrieval result together with its ranking signals."""

    result: RetrievalResult
    score: float
    semantic_score: float
    file_path_score: float
    symbol_name_score: float
    lexical_score: float


class RetrievalRanker:
    """Rank semantic retrieval candidates using software-aware lexical signals."""

    _TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")

    def __init__(
        self,
        *,
        weights: RankingWeights | None = None,
    ) -> None:
        self._weights = weights or RankingWeights()

    def rank(
        self,
        *,
        query: str,
        candidates: list[RetrievalResult],
    ) -> list[RankedRetrievalResult]:
        """Rank retrieval candidates against a natural-language query."""

        normalized_query = query.strip()

        if not normalized_query or not candidates:
            return []

        query_tokens = self._tokenize(normalized_query)
        normalized_query_lower = normalized_query.lower()

        ranked: list[RankedRetrievalResult] = []

        for candidate in candidates:
            semantic_score = self._clamp(candidate.score)

            file_path_score = self._file_path_score(
                query=normalized_query_lower,
                query_tokens=query_tokens,
                file_path=candidate.file_path,
            )

            symbol_name_score = self._symbol_name_score(
                query=normalized_query_lower,
                query_tokens=query_tokens,
                symbol_name=candidate.symbol_name,
            )

            lexical_score = self._lexical_score(
                query_tokens=query_tokens,
                result=candidate,
            )

            final_score = (
                semantic_score * self._weights.semantic
                + file_path_score * self._weights.file_path
                + symbol_name_score * self._weights.symbol_name
                + lexical_score * self._weights.lexical
            )

            ranked.append(
                RankedRetrievalResult(
                    result=candidate,
                    score=final_score,
                    semantic_score=semantic_score,
                    file_path_score=file_path_score,
                    symbol_name_score=symbol_name_score,
                    lexical_score=lexical_score,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                -item.semantic_score,
                item.result.file_path,
                item.result.start_line,
                item.result.end_line,
                str(item.result.chunk_id),
            )
        )

        return ranked

    @classmethod
    def _file_path_score(
        cls,
        *,
        query: str,
        query_tokens: set[str],
        file_path: str,
    ) -> float:
        normalized_path = file_path.lower()
        path_tokens = cls._tokenize(normalized_path)

        if normalized_path in query:
            return 1.0

        if path_tokens and path_tokens.issubset(query_tokens):
            return 1.0

        if path_tokens & query_tokens:
            return 0.75

        filename = normalized_path.rsplit("/", maxsplit=1)[-1]

        if filename.rsplit(".", maxsplit=1)[0] in query_tokens:
            return 0.75

        return 0.0

    @classmethod
    def _symbol_name_score(
        cls,
        *,
        query: str,
        query_tokens: set[str],
        symbol_name: str,
    ) -> float:
        normalized_symbol = symbol_name.lower()

        if not normalized_symbol:
            return 0.0

        if normalized_symbol in query:
            return 1.0

        symbol_tokens = cls._tokenize(normalized_symbol)

        if not symbol_tokens:
            return 0.0

        overlap = len(symbol_tokens & query_tokens) / len(symbol_tokens)

        if overlap >= 1.0:
            return 1.0

        if overlap > 0.0:
            return 0.75

        return 0.0

    @classmethod
    def _lexical_score(
        cls,
        *,
        query_tokens: set[str],
        result: RetrievalResult,
    ) -> float:
        if not query_tokens:
            return 0.0

        candidate_text = " ".join(
            (
                result.file_path,
                result.symbol_name,
                result.symbol_type,
                result.parent or "",
                result.content,
            )
        ).lower()

        candidate_tokens = cls._tokenize(candidate_text)

        if not candidate_tokens:
            return 0.0

        overlap = query_tokens & candidate_tokens

        return len(overlap) / len(query_tokens)

    @classmethod
    def _tokenize(cls, value: str) -> set[str]:
        return {
            token.lower()
            for token in cls._TOKEN_PATTERN.findall(value)
            if len(token) > 1
        }

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
