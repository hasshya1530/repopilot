from ingestion.graph.models import SymbolRelation
from ingestion.graph.parsers.python import PythonRelationshipParser


def test_python_parser_extracts_imports() -> None:
    source = b"""
import os
from pathlib import Path
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/example.py",
    )

    imports = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.IMPORTS
    ]

    assert len(imports) == 2
    assert imports[0].target_name == "os"
    assert imports[1].target_name == "Path"


def test_python_parser_extracts_function_calls() -> None:
    source = b"""
def login():
    validate_token()
    refresh_access_token()
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/auth.py",
    )

    calls = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.CALLS
    ]

    assert len(calls) == 2
    assert calls[0].source_name == "login"
    assert calls[0].target_name == "validate_token"
    assert calls[1].source_name == "login"
    assert calls[1].target_name == "refresh_access_token"


def test_python_parser_tracks_method_calls() -> None:
    source = b"""
class AuthService:
    def login(self):
        self.validate_token()

    def validate_token(self):
        return True
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/auth.py",
    )

    calls = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.CALLS
    ]

    assert len(calls) == 1
    assert calls[0].source_name == "login"
    assert calls[0].target_name == "self.validate_token"


def test_python_parser_extracts_multiple_from_imports() -> None:
    source = b"""
from package import foo, bar
from package.submodule import thing
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/example.py",
    )

    imports = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.IMPORTS
    ]

    assert len(imports) == 3

    assert imports[0].target_name == "foo"
    assert imports[0].target_file == "package"

    assert imports[1].target_name == "bar"
    assert imports[1].target_file == "package"

    assert imports[2].target_name == "thing"
    assert imports[2].target_file == "package.submodule"


def test_python_parser_extracts_dotted_imports() -> None:
    source = b"""
import os.path
import package.submodule
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/example.py",
    )

    imports = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.IMPORTS
    ]

    assert len(imports) == 2
    assert imports[0].target_name == "os.path"
    assert imports[1].target_name == "package.submodule"


def test_python_parser_tracks_imports_inside_function() -> None:
    source = b"""
def process():
    import json
    from pathlib import Path
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/example.py",
    )

    imports = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.IMPORTS
    ]

    assert len(imports) == 2
    assert all(relationship.source_name == "process" for relationship in imports)
    assert imports[0].target_name == "json"
    assert imports[1].target_name == "Path"


def test_python_parser_extracts_method_and_function_calls() -> None:
    source = b"""
def process():
    validate()
    service.run()
    helper.transform()

class Service:
    def run(self):
        validate()
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/service.py",
    )

    calls = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.CALLS
    ]

    assert len(calls) == 4

    assert calls[0].source_name == "process"
    assert calls[0].target_name == "validate"

    assert calls[1].source_name == "process"
    assert calls[1].target_name == "service.run"

    assert calls[2].source_name == "process"
    assert calls[2].target_name == "helper.transform"

    assert calls[3].source_name == "run"
    assert calls[3].target_name == "validate"


def test_python_parser_preserves_module_as_import_source() -> None:
    source = b"""
import requests
from pathlib import Path
""".strip()

    parser = PythonRelationshipParser()

    relationships = parser.parse(
        source,
        "src/client.py",
    )

    imports = [
        relationship
        for relationship in relationships
        if relationship.relation == SymbolRelation.IMPORTS
    ]

    assert all(relationship.source_name == "__module__" for relationship in imports)
    assert imports[0].target_name == "requests"
    assert imports[1].target_name == "Path"
    assert imports[1].target_file == "pathlib"
