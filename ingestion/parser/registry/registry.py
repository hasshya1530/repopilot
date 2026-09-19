from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ingestion.parser.languages.base import LanguageParser
from ingestion.parser.languages.javascript import JavaScriptParser
from ingestion.parser.languages.python import PythonParser
from ingestion.parser.languages.typescript import TypeScriptParser

ParserFactory = Callable[[], LanguageParser]


@dataclass(frozen=True, slots=True)
class LanguageDefinition:
    """Definition of a supported source language."""

    name: str
    extensions: frozenset[str]
    parser_factory: ParserFactory


class LanguageRegistry:
    """Registry mapping source-code extensions to language definitions."""

    def __init__(
        self,
        *,
        definitions: tuple[LanguageDefinition, ...] | None = None,
    ) -> None:
        if definitions is None:
            definitions = self._default_definitions()

        self._definitions: dict[str, LanguageDefinition] = {}

        for definition in definitions:
            self.register(definition)

    def register(self, definition: LanguageDefinition) -> None:
        """Register a language definition for all of its extensions."""

        for extension in definition.extensions:
            normalized_extension = self._normalize_extension(extension)
            self._definitions[normalized_extension] = definition

    def get_by_extension(
        self,
        extension: str,
    ) -> LanguageDefinition | None:
        """Return the language definition for an extension."""

        return self._definitions.get(
            self._normalize_extension(extension)
        )

    def get_parser(
        self,
        extension: str,
    ) -> LanguageParser | None:
        """Create the parser registered for an extension."""

        definition = self.get_by_extension(extension)

        if definition is None:
            return None

        return definition.parser_factory()

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        """Normalize extensions to lowercase dotted form."""

        normalized = extension.strip().lower()

        if not normalized:
            return normalized

        if not normalized.startswith("."):
            normalized = f".{normalized}"

        return normalized

    @staticmethod
    def _default_definitions() -> tuple[LanguageDefinition, ...]:
        """Return RepoPilot's default language definitions."""

        return (
            LanguageDefinition(
                name="python",
                extensions=frozenset({".py"}),
                parser_factory=PythonParser,
            ),
            LanguageDefinition(
                name="javascript",
                extensions=frozenset({".js", ".jsx"}),
                parser_factory=JavaScriptParser,
            ),
            LanguageDefinition(
                name="typescript",
                extensions=frozenset({".ts"}),
                parser_factory=TypeScriptParser,
            ),
            LanguageDefinition(
                name="typescript",
                extensions=frozenset({".tsx"}),
                parser_factory=lambda: TypeScriptParser(tsx=True),
            ),
        )


DEFAULT_LANGUAGE_REGISTRY = LanguageRegistry()
