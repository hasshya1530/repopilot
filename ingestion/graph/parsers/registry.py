from ingestion.graph.parsers.base import RelationshipParser
from ingestion.graph.parsers.python import PythonRelationshipParser


class RelationshipParserRegistry:
    """Resolve relationship parsers by source-file extension."""

    def __init__(self) -> None:
        self._parsers: dict[str, type[RelationshipParser]] = {
            ".py": PythonRelationshipParser,
        }

    def get_parser(self, extension: str) -> RelationshipParser | None:
        parser_factory = self._parsers.get(extension.lower())

        if parser_factory is None:
            return None

        return parser_factory()
