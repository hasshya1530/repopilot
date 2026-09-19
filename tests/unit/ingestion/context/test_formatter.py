from uuid import uuid4

from ingestion.context.formatter import RepositoryContextFormatter
from ingestion.context.models import (
    RepositoryContext,
    RepositoryContextFile,
    RepositoryContextItem,
)


def make_item(
    *,
    file_path: str,
    symbol_name: str,
    content: str,
    score: float,
    start_line: int = 10,
    end_line: int = 20,
    parent: str | None = None,
) -> RepositoryContextItem:
    return RepositoryContextItem(
        chunk_id=uuid4(),
        file_path=file_path,
        symbol_name=symbol_name,
        symbol_type="function",
        start_line=start_line,
        end_line=end_line,
        content=content,
        score=score,
        parent=parent,
    )


def make_context(
    *,
    files: tuple[RepositoryContextFile, ...],
    query: str = "authentication validation",
    total_candidates: int = 10,
    truncated: bool = False,
    character_count: int = 100,
) -> RepositoryContext:
    items = tuple(
        item
        for repository_file in files
        for item in repository_file.items
    )

    return RepositoryContext(
        repository_id=uuid4(),
        query=query,
        items=items,
        files=files,
        total_candidates=total_candidates,
        truncated=truncated,
        character_count=character_count,
    )


def test_formatter_includes_context_metadata() -> None:
    item = make_item(
        file_path="src/auth.py",
        symbol_name="validate_token",
        content="return token.is_valid()",
        score=0.912345,
    )

    repository_file = RepositoryContextFile(
        file_path="src/auth.py",
        items=(item,),
        score=0.912345,
    )

    context = make_context(
        files=(repository_file,),
        total_candidates=5,
        truncated=True,
        character_count=24,
    )

    formatted = RepositoryContextFormatter().format(context)

    assert "REPOSITORY CODE CONTEXT" in formatted
    assert "Query: authentication validation" in formatted
    assert "Retrieved candidates: 5" in formatted
    assert "Included chunks: 1" in formatted
    assert "Context truncated: yes" in formatted
    assert "Source characters: 24" in formatted


def test_formatter_includes_file_and_symbol_metadata() -> None:
    item = make_item(
        file_path="agents/auth/service.py",
        symbol_name="validate_token",
        content="return True",
        score=0.876543,
        start_line=42,
        end_line=57,
        parent="AuthService",
    )

    repository_file = RepositoryContextFile(
        file_path="agents/auth/service.py",
        items=(item,),
        score=0.876543,
    )

    context = make_context(files=(repository_file,))

    formatted = RepositoryContextFormatter().format(context)

    assert "FILE 1: agents/auth/service.py" in formatted
    assert "FILE RELEVANCE: 0.876543" in formatted
    assert "CHUNK 1.1" in formatted
    assert "SYMBOL: validate_token" in formatted
    assert "SYMBOL TYPE: function" in formatted
    assert "LINES: 42-57" in formatted
    assert "RELEVANCE: 0.876543" in formatted
    assert "PARENT: AuthService" in formatted


def test_formatter_includes_source_boundaries() -> None:
    item = make_item(
        file_path="src/example.py",
        symbol_name="example",
        content="def example():\n    return 42",
        score=0.9,
    )

    repository_file = RepositoryContextFile(
        file_path="src/example.py",
        items=(item,),
        score=0.9,
    )

    context = make_context(files=(repository_file,))

    formatted = RepositoryContextFormatter().format(context)

    assert "SOURCE BEGIN" in formatted
    assert "def example():" in formatted
    assert "return 42" in formatted
    assert "SOURCE END" in formatted


def test_formatter_preserves_source_containing_markdown_fences() -> None:
    source = 'value = """```python\nprint("hello")\n```"""'

    item = make_item(
        file_path="src/example.py",
        symbol_name="example",
        content=source,
        score=0.9,
    )

    repository_file = RepositoryContextFile(
        file_path="src/example.py",
        items=(item,),
        score=0.9,
    )

    context = make_context(files=(repository_file,))

    formatted = RepositoryContextFormatter().format(context)

    assert source in formatted
    assert "SOURCE BEGIN" in formatted
    assert "SOURCE END" in formatted


def test_formatter_preserves_file_order() -> None:
    first = make_item(
        file_path="src/first.py",
        symbol_name="first",
        content="first()",
        score=0.95,
    )

    second = make_item(
        file_path="src/second.py",
        symbol_name="second",
        content="second()",
        score=0.80,
    )

    first_file = RepositoryContextFile(
        file_path="src/first.py",
        items=(first,),
        score=0.95,
    )

    second_file = RepositoryContextFile(
        file_path="src/second.py",
        items=(second,),
        score=0.80,
    )

    context = make_context(
        files=(first_file, second_file),
    )

    formatted = RepositoryContextFormatter().format(context)

    assert formatted.index("FILE 1: src/first.py") < formatted.index(
        "FILE 2: src/second.py"
    )


def test_formatter_is_deterministic() -> None:
    item = make_item(
        file_path="src/example.py",
        symbol_name="example",
        content="return 1",
        score=0.91,
    )

    repository_file = RepositoryContextFile(
        file_path="src/example.py",
        items=(item,),
        score=0.91,
    )

    context = make_context(files=(repository_file,))

    formatter = RepositoryContextFormatter()

    assert formatter.format(context) == formatter.format(context)
    assert formatter.format(context) == formatter.format_for_prompt(context)


def test_formatter_handles_empty_context() -> None:
    context = make_context(files=())

    formatted = RepositoryContextFormatter().format(context)

    assert "No repository code was retrieved." in formatted
    assert "Included chunks: 0" in formatted
