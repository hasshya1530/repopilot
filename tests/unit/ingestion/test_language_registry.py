from ingestion.parser.languages import PythonParser
from ingestion.parser.registry import (
    DEFAULT_LANGUAGE_REGISTRY,
    LanguageDefinition,
    LanguageRegistry,
)


def test_registry_resolves_python_extension() -> None:
    definition = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".py")

    assert definition is not None
    assert definition.name == "python"


def test_registry_resolves_extension_without_dot() -> None:
    definition = DEFAULT_LANGUAGE_REGISTRY.get_by_extension("py")

    assert definition is not None
    assert definition.name == "python"


def test_registry_is_case_insensitive() -> None:
    definition = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".PY")

    assert definition is not None
    assert definition.name == "python"


def test_registry_returns_none_for_unsupported_extension() -> None:
    definition = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".xyz")

    assert definition is None


def test_registry_creates_python_parser() -> None:
    parser = DEFAULT_LANGUAGE_REGISTRY.get_parser(".py")

    assert isinstance(parser, PythonParser)


def test_registry_returns_none_parser_for_unsupported_extension() -> None:
    parser = DEFAULT_LANGUAGE_REGISTRY.get_parser(".xyz")

    assert parser is None


def test_registry_supports_multiple_extensions() -> None:
    registry = LanguageRegistry(
        definitions=(
            LanguageDefinition(
                name="python",
                extensions=frozenset({".py", ".pyw"}),
                parser_factory=PythonParser,
            ),
        ),
    )

    assert registry.get_by_extension(".py") is not None
    assert registry.get_by_extension(".pyw") is not None

def test_registry_resolves_javascript_extensions() -> None:
    javascript = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".js")
    jsx = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".jsx")

    assert javascript is not None
    assert javascript.name == "javascript"

    assert jsx is not None
    assert jsx.name == "javascript"


def test_registry_creates_javascript_parser() -> None:
    parser = DEFAULT_LANGUAGE_REGISTRY.get_parser(".js")

    assert parser is not None
    assert parser.__class__.__name__ == "JavaScriptParser"

def test_registry_resolves_typescript_extensions() -> None:
    typescript = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".ts")
    tsx = DEFAULT_LANGUAGE_REGISTRY.get_by_extension(".tsx")

    assert typescript is not None
    assert typescript.name == "typescript"

    assert tsx is not None
    assert tsx.name == "typescript"


def test_registry_creates_typescript_parser() -> None:
    parser = DEFAULT_LANGUAGE_REGISTRY.get_parser(".ts")

    assert parser is not None
    assert parser.__class__.__name__ == "TypeScriptParser"
