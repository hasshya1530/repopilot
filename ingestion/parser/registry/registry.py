from ingestion.parser.languages import (
    JavaScriptParser,
    LanguageParser,
    PythonParser,
    TypeScriptParser,
)
from ingestion.parser.registry.languages import LanguageDefinition


class LanguageRegistry:
    def __init__(
        self,
        definitions: tuple[LanguageDefinition, ...],
    ) -> None:
        self._definitions = definitions
        self._extension_map = {
            extension.lower(): definition
            for definition in definitions
            for extension in definition.extensions
        }

    def get_by_extension(
        self,
        extension: str,
    ) -> LanguageDefinition | None:
        normalized_extension = extension.lower()

        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

        return self._extension_map.get(normalized_extension)

    def get_parser(
        self,
        extension: str,
    ) -> LanguageParser | None:
        definition = self.get_by_extension(extension)

        if definition is None:
            return None

        return definition.parser_factory()


DEFAULT_LANGUAGE_REGISTRY = LanguageRegistry(
    definitions=(
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
            extensions=frozenset({".ts", ".tsx"}),
            parser_factory=TypeScriptParser,
        ),
    ),
)
