from pathlib import Path

from ingestion.graph.extraction import RelationshipExtractionService
from ingestion.graph.models import SymbolRelation, SymbolRelationship
from ingestion.graph.parsers.base import RelationshipParser
from ingestion.parser.files import RepositoryFile


class FakeRelationshipParser(RelationshipParser):
    def parse(
        self,
        source: bytes,
        file_path: str,
    ) -> list[SymbolRelationship]:
        return [
            SymbolRelationship(
                source_name="login",
                target_name="validate_token",
                relation=SymbolRelation.CALLS,
                source_file=file_path,
            )
        ]


class FakeParserRegistry:
    def __init__(self, parser: RelationshipParser | None) -> None:
        self.parser = parser

    def get_parser(self, extension: str) -> RelationshipParser | None:
        return self.parser


def test_extraction_service_extracts_relationships() -> None:
    service = RelationshipExtractionService(
        FakeParserRegistry(FakeRelationshipParser())
    )

    repository_file = RepositoryFile(
        path=Path("/repo/auth.py"),
        relative_path="auth.py",
        size_bytes=100,
        extension=".py",
    )

    relationships = service.extract(
        repository_file,
        b"def login():\n    validate_token()",
    )

    assert len(relationships) == 1
    assert relationships[0].source_name == "login"
    assert relationships[0].target_name == "validate_token"
    assert relationships[0].source_file == "auth.py"


def test_extraction_service_returns_empty_for_unsupported_language() -> None:
    service = RelationshipExtractionService(
        FakeParserRegistry(None)
    )

    repository_file = RepositoryFile(
        path=Path("/repo/readme.md"),
        relative_path="readme.md",
        size_bytes=100,
        extension=".md",
    )

    assert service.extract(repository_file, b"# README") == []
