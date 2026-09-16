from uuid import uuid4

from ingestion.retrieval import RetrievalResult


def test_retrieval_result() -> None:
    repository_id = uuid4()
    chunk_id = uuid4()

    result = RetrievalResult(
        chunk_id=chunk_id,
        repository_id=repository_id,
        file_path="src/auth.py",
        content="def refresh_token(): ...",
        symbol_name="refresh_token",
        symbol_type="function",
        start_line=10,
        end_line=15,
        parent=None,
        score=0.92,
    )

    assert result.chunk_id == chunk_id
    assert result.repository_id == repository_id
    assert result.file_path == "src/auth.py"
    assert result.symbol_name == "refresh_token"
    assert result.score == 0.92
