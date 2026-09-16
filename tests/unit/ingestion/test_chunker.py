from pathlib import Path

from ingestion.chunker import CodeChunker
from ingestion.parser.files import RepositoryFile
from ingestion.parser.languages import SymbolType


def make_repository_file(
    tmp_path: Path,
    content: str,
) -> RepositoryFile:
    file_path = tmp_path / "example.py"
    file_path.write_text(content, encoding="utf-8")

    return RepositoryFile(
        path=file_path,
        relative_path="example.py",
        size_bytes=file_path.stat().st_size,
        extension=".py",
    )


def test_chunker_creates_chunks_for_symbols(tmp_path: Path) -> None:
    source = """class UserService:
    def create_user(self, name: str):
        return name
"""

    repository_file = make_repository_file(tmp_path, source)

    chunks = CodeChunker().chunk_file(repository_file)

    assert len(chunks) == 3


def test_chunker_preserves_file_path(tmp_path: Path) -> None:
    source = """def hello():
    return "hello"
"""

    repository_file = make_repository_file(tmp_path, source)

    chunks = CodeChunker().chunk_file(repository_file)

    function_chunk = next(chunk for chunk in chunks if chunk.symbol_type == SymbolType.FUNCTION)

    assert function_chunk.file_path == "example.py"


def test_chunker_preserves_symbol_metadata(tmp_path: Path) -> None:
    source = """class UserService:
    def create_user(self, name: str):
        return name
"""

    repository_file = make_repository_file(tmp_path, source)

    chunks = CodeChunker().chunk_file(repository_file)

    method = next(chunk for chunk in chunks if chunk.symbol_type == SymbolType.METHOD)

    assert method.symbol_name == "create_user"
    assert method.parent == "UserService"


def test_chunker_extracts_exact_source(tmp_path: Path) -> None:
    source = """def create_user(name: str):
    return name
"""

    repository_file = make_repository_file(tmp_path, source)

    chunks = CodeChunker().chunk_file(repository_file)

    function = next(chunk for chunk in chunks if chunk.symbol_type == SymbolType.FUNCTION)

    assert function.content == source.strip()


def test_chunker_tracks_line_ranges(tmp_path: Path) -> None:
    source = """class Example:
    def method(self):
        value = 1
        return value
"""

    repository_file = make_repository_file(tmp_path, source)

    chunks = CodeChunker().chunk_file(repository_file)

    method = next(chunk for chunk in chunks if chunk.symbol_type == SymbolType.METHOD)

    assert method.start_line == 2
    assert method.end_line == 4

def test_chunker_skips_unsupported_language(tmp_path: Path) -> None:
    source = "some unknown format"

    file_path = tmp_path / "example.xyz"
    file_path.write_text(source, encoding="utf-8")

    repository_file = RepositoryFile(
        path=file_path,
        relative_path="example.xyz",
        size_bytes=file_path.stat().st_size,
        extension=".xyz",
    )

    chunks = CodeChunker().chunk_file(repository_file)

    assert chunks == []
