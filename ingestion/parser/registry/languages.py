from collections.abc import Callable
from dataclasses import dataclass

from ingestion.parser.languages import LanguageParser

ParserFactory = Callable[[], LanguageParser]


@dataclass(frozen=True, slots=True)
class LanguageDefinition:
    name: str
    extensions: frozenset[str]
    parser_factory: ParserFactory
