
from ingestion.chunker.models import CodeChunk
from ingestion.parser.files import RepositoryFile
from ingestion.parser.languages import CodeSymbol, LanguageParser


class CodeChunker:
    def __init__(self, parser: LanguageParser) -> None:
        self._parser = parser

    def chunk_file(self, repository_file: RepositoryFile) -> list[CodeChunk]:
        source = repository_file.path.read_bytes()
        symbols = self._parser.parse(source)

        chunks: list[CodeChunk] = []

        for symbol in symbols:
            content = self._extract_symbol_source(
                source=source,
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

    @staticmethod
    def _extract_symbol_source(
        source: bytes,
        symbol: CodeSymbol,
    ) -> str:
        lines = source.decode("utf-8").splitlines()

        start = symbol.start_line - 1
        end = symbol.end_line

        return "\n".join(lines[start:end])
