from __future__ import annotations

from ingestion.chunker.models import CodeChunk
from ingestion.parser.files import RepositoryFile
from ingestion.parser.languages.base import CodeSymbol
from ingestion.parser.registry import DEFAULT_LANGUAGE_REGISTRY, LanguageRegistry
from ingestion.parser.worker_client import (
    ParserWorkerClient,
    is_native_tree_sitter_extension,
)


class CodeChunker:
    """Convert parsed repository files into semantic code chunks."""

    def __init__(
        self,
        registry: LanguageRegistry = DEFAULT_LANGUAGE_REGISTRY,
        parser_worker: ParserWorkerClient | None = None,
    ) -> None:
        self._registry = registry
        self._parser_worker = parser_worker

    def chunk_file(
        self,
        repository_file: RepositoryFile,
    ) -> list[CodeChunk]:
        symbols = self._parse_file(repository_file)

        if not symbols:
            return []

        source = repository_file.path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        lines = source.splitlines()

        chunks: list[CodeChunk] = []

        for symbol in symbols:
            content = self._extract_symbol_source(
                lines=lines,
                symbol=symbol,
            )

            if not content.strip():
                continue

            chunks.append(
                CodeChunk(
                    file_path=repository_file.relative_path,
                    content=content,
                    symbol_name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    parent=symbol.parent,
                )
            )

        return chunks

    def _parse_file(
        self,
        repository_file: RepositoryFile,
    ) -> list[CodeSymbol]:
        if is_native_tree_sitter_extension(
            repository_file.extension,
        ):
            if self._parser_worker is None:
                raise RuntimeError(
                    "A ParserWorkerClient is required for "
                    "JavaScript/TypeScript/TSX files."
                )

            return self._parser_worker.parse(repository_file)

        parser = self._registry.get_parser(repository_file.extension)

        if parser is None:
            return []

        source = repository_file.path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        return parser.parse(source.encode("utf-8"))

    @staticmethod
    def _extract_symbol_source(
        *,
        lines: list[str],
        symbol: CodeSymbol,
    ) -> str:
        """Extract source from validated 1-based line ranges."""

        if symbol.start_line < 1:
            return ""

        if symbol.end_line < symbol.start_line:
            return ""

        start_index = symbol.start_line - 1
        end_index = min(symbol.end_line, len(lines))

        if start_index >= len(lines):
            return ""

        return "\n".join(lines[start_index:end_index])
