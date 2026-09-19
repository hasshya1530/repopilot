from uuid import uuid4

import pytest

from ingestion.retrieval.models import RetrievalResult
from ingestion.retrieval.ranking import RankingWeights, RetrievalRanker


def make_result(
    *,
    file_path: str,
    symbol_name: str,
    content: str,
    score: float,
    symbol_type: str = "function",
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        repository_id=uuid4(),
        file_path=file_path,
        content=content,
        symbol_name=symbol_name,
        symbol_type=symbol_type,
        start_line=1,
        end_line=10,
        parent=None,
        score=score,
    )


def test_ranker_prioritizes_exact_file_match() -> None:
    ranker = RetrievalRanker()

    candidates = [
        make_result(
            file_path="agents/jobs/retry.py",
            symbol_name="retry_job",
            content="Retry a failed background job.",
            score=0.86,
        ),
        make_result(
            file_path="apps/api/app/services/unrelated.py",
            symbol_name="handle_job",
            content="Handle background execution.",
            score=0.90,
        ),
    ]

    ranked = ranker.rank(
        query="fix retry logic in agents/jobs/retry.py",
        candidates=candidates,
    )

    assert ranked[0].result.file_path == "agents/jobs/retry.py"
    assert ranked[0].file_path_score == 1.0


def test_ranker_prioritizes_exact_symbol_match() -> None:
    ranker = RetrievalRanker()

    candidates = [
        make_result(
            file_path="agents/jobs/worker.py",
            symbol_name="process_job",
            content="Process a background job.",
            score=0.85,
        ),
        make_result(
            file_path="agents/jobs/worker.py",
            symbol_name="retry_job",
            content="Retry a background job.",
            score=0.84,
        ),
    ]

    ranked = ranker.rank(
        query="fix retry_job",
        candidates=candidates,
    )

    assert ranked[0].result.symbol_name == "retry_job"
    assert ranked[0].symbol_name_score == 1.0


def test_ranker_uses_lexical_overlap() -> None:
    ranker = RetrievalRanker()

    candidates = [
        make_result(
            file_path="src/auth.py",
            symbol_name="refresh_token",
            content="Refresh an expired authentication token.",
            score=0.80,
        ),
        make_result(
            file_path="src/math.py",
            symbol_name="calculate_total",
            content="Calculate the total of numeric values.",
            score=0.80,
        ),
    ]

    ranked = ranker.rank(
        query="authentication token refresh",
        candidates=candidates,
    )

    assert ranked[0].result.file_path == "src/auth.py"
    assert ranked[0].lexical_score > ranked[1].lexical_score


def test_ranker_preserves_semantic_signal() -> None:
    ranker = RetrievalRanker()

    candidates = [
        make_result(
            file_path="src/general.py",
            symbol_name="handle",
            content="Generic implementation.",
            score=0.95,
        ),
        make_result(
            file_path="src/auth.py",
            symbol_name="authenticate",
            content="Authentication implementation.",
            score=0.70,
        ),
    ]

    ranked = ranker.rank(
        query="database connection pooling",
        candidates=candidates,
    )

    assert ranked[0].result.file_path == "src/general.py"


def test_ranker_returns_empty_for_blank_query() -> None:
    ranker = RetrievalRanker()

    result = ranker.rank(
        query="   ",
        candidates=[],
    )

    assert result == []


def test_ranker_returns_empty_for_no_candidates() -> None:
    ranker = RetrievalRanker()

    result = ranker.rank(
        query="authentication",
        candidates=[],
    )

    assert result == []


def test_ranker_clamps_semantic_score() -> None:
    ranker = RetrievalRanker()

    candidate = make_result(
        file_path="src/auth.py",
        symbol_name="authenticate",
        content="Authentication implementation.",
        score=1.5,
    )

    ranked = ranker.rank(
        query="authentication",
        candidates=[candidate],
    )

    assert ranked[0].semantic_score == 1.0


def test_invalid_weights_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RankingWeights(
            semantic=-0.1,
            file_path=0.4,
            symbol_name=0.4,
            lexical=0.3,
        )


def test_zero_weights_are_rejected() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        RankingWeights(
            semantic=0.0,
            file_path=0.0,
            symbol_name=0.0,
            lexical=0.0,
        )


def test_custom_weights_are_supported() -> None:
    ranker = RetrievalRanker(
        weights=RankingWeights(
            semantic=0.5,
            file_path=0.2,
            symbol_name=0.2,
            lexical=0.1,
        )
    )

    candidate = make_result(
        file_path="src/auth.py",
        symbol_name="authenticate",
        content="Authentication implementation.",
        score=0.8,
    )

    ranked = ranker.rank(
        query="authentication",
        candidates=[candidate],
    )

    assert ranked[0].score > 0.0
