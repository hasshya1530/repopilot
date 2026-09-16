from pathlib import Path
from typing import Protocol

from ingestion.graph.models import SymbolRelationship
from ingestion.graph.parsers.base import RelationshipParser
from ingestion.parser.discovery import DiscoveryConfig, discover_files
from ingestion.parser.files import RepositoryFile


class RelationshipParserRegistryProtocol(Protocol):
    """Protocol for resolving relationship parsers by extension."""

    def get_parser(
        self,
        extension: str,
    ) -> RelationshipParser | None:
        ...


class RelationshipExtractionService:
    """Extract relationships from a single repository file."""

    def __init__(
        self,
        parser_registry: RelationshipParserRegistryProtocol,
    ) -> None:
        self._parser_registry = parser_registry

    def extract(
        self,
        repository_file: RepositoryFile,
        source: bytes,
    ) -> list[SymbolRelationship]:
        parser = self._parser_registry.get_parser(
            repository_file.extension,
        )

        if parser is None:
            return []

        return parser.parse(
            source,
            repository_file.relative_path,
        )


class RepositoryRelationshipExtractionService:
    """Extract source-level relationships across a repository."""

    def __init__(
        self,
        parser_registry: RelationshipParserRegistryProtocol,
        *,
        discovery_config: DiscoveryConfig | None = None,
    ) -> None:
        self._parser_registry = parser_registry
        self._discovery_config = discovery_config

    def extract_repository(
        self,
        repository_path: Path,
    ) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []

        files = discover_files(
            repository_path,
            self._discovery_config,
        )

        for repository_file in files:
            relationships.extend(
                self._extract_file(repository_file)
            )

        return relationships

    def _extract_file(
        self,
        repository_file: RepositoryFile,
    ) -> list[SymbolRelationship]:
        parser = self._parser_registry.get_parser(
            repository_file.extension,
        )

        if parser is None:
            return []

        source = repository_file.path.read_bytes()

        return parser.parse(
            source,
            repository_file.relative_path,
        )
