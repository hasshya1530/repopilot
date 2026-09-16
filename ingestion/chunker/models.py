from dataclasses import dataclass

from ingestion.parser.languages.base import SymbolType


@dataclass(frozen=True, slots=True)
class CodeChunk:
    file_path: str
    content: str
    symbol_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    parent: str | None = None
