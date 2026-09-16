from pathlib import Path

from ingestion.graph.extraction.service import (
    RepositoryRelationshipExtractionService,
)
from ingestion.graph.models import SymbolRelation, SymbolRelationship
from ingestion.graph.parsers.base import RelationshipParser


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
    def get_parser(self, extension: str) -> RelationshipParser | None:
        if extension == ".py":
            return FakeRelationshipParser()

        return None


def test_extract_repository_collects_relationships(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    auth_file = source_dir / "auth.py"
    auth_file.write_text(
        "def login():\n    validate_token()\n",
        encoding="utf-8",
    )

    (source_dir / "README.md").write_text(
        "# Example\n",
        encoding="utf-8",
    )

    service = RepositoryRelationshipExtractionService(
        FakeParserRegistry()
    )

    relationships = service.extract_repository(tmp_path)

    assert len(relationships) == 1
    assert relationships[0].source_name == "login"
    assert relationships[0].target_name == "validate_token"
    assert relationships[0].source_file == "src/auth.py"


def test_extract_repository_returns_empty_for_no_supported_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text(
        "# Example\n",
        encoding="utf-8",
    )

    service = RepositoryRelationshipExtractionService(
        FakeParserRegistry()
    )

    assert service.extract_repository(tmp_path) == []
