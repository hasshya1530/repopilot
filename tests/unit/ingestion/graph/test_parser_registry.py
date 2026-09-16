from ingestion.graph.parsers import (
    PythonRelationshipParser,
    RelationshipParserRegistry,
)


def test_registry_returns_python_relationship_parser() -> None:
    registry = RelationshipParserRegistry()

    parser = registry.get_parser(".py")

    assert isinstance(parser, PythonRelationshipParser)


def test_registry_is_case_insensitive() -> None:
    registry = RelationshipParserRegistry()

    parser = registry.get_parser(".PY")

    assert isinstance(parser, PythonRelationshipParser)


def test_registry_returns_none_for_unsupported_extension() -> None:
    registry = RelationshipParserRegistry()

    assert registry.get_parser(".md") is None
