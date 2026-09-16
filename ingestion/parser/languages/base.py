from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SymbolType(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"


@dataclass(frozen=True, slots=True)
class CodeSymbol:
    name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    parent: str | None = None


class LanguageParser(ABC):
    @abstractmethod
    def parse(self, source: bytes) -> list[CodeSymbol]:
        """Parse source code and return extracted symbols."""
