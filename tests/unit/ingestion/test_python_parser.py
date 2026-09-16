from ingestion.parser.languages.base import SymbolType
from ingestion.parser.languages.python import PythonParser


def test_python_parser_extracts_module() -> None:
    source = b"""
x = 10
"""

    symbols = PythonParser().parse(source)

    assert len(symbols) == 1

    module = symbols[0]

    assert module.name == "module"
    assert module.symbol_type == SymbolType.MODULE
    assert module.start_line == 1


def test_python_parser_extracts_imports() -> None:
    source = b"""
import os
import json
from pathlib import Path
from typing import Any
"""

    symbols = PythonParser().parse(source)

    imports = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.IMPORT
    ]

    assert [symbol.name for symbol in imports] == [
        "import os",
        "import json",
        "from pathlib import Path",
        "from typing import Any",
    ]


def test_python_parser_extracts_functions() -> None:
    source = b"""
def create_user(name: str):
    return name


async def get_user(user_id: int):
    return user_id
"""

    symbols = PythonParser().parse(source)

    functions = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.FUNCTION
    ]

    assert [symbol.name for symbol in functions] == [
        "create_user",
        "get_user",
    ]

    assert functions[0].start_line == 2
    assert functions[0].end_line == 3

    assert functions[1].start_line == 6
    assert functions[1].end_line == 7


def test_python_parser_extracts_classes_and_methods() -> None:
    source = b"""
class UserService:

    def create_user(self, name: str):
        return name

    async def get_user(self, user_id: int):
        return user_id
"""

    symbols = PythonParser().parse(source)

    classes = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.CLASS
    ]

    methods = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.METHOD
    ]

    assert [symbol.name for symbol in classes] == [
        "UserService",
    ]

    assert [symbol.name for symbol in methods] == [
        "create_user",
        "get_user",
    ]

    assert methods[0].parent == "UserService"
    assert methods[1].parent == "UserService"


def test_python_parser_extracts_decorated_function() -> None:
    source = b"""
@app.get("/users")
async def list_users():
    return []
"""

    symbols = PythonParser().parse(source)

    functions = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.FUNCTION
    ]

    assert len(functions) == 1
    assert functions[0].name == "list_users"


def test_python_parser_extracts_decorated_class() -> None:
    source = b"""
@dataclass
class User:
    name: str
"""

    symbols = PythonParser().parse(source)

    classes = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.CLASS
    ]

    assert len(classes) == 1
    assert classes[0].name == "User"


def test_python_parser_tracks_line_ranges() -> None:
    source = b"""class Example:
    def method(self):
        value = 1
        return value
"""

    symbols = PythonParser().parse(source)

    example = next(
        symbol
        for symbol in symbols
        if symbol.name == "Example"
    )

    method = next(
        symbol
        for symbol in symbols
        if symbol.name == "method"
    )

    assert example.start_line == 1
    assert example.end_line == 4

    assert method.start_line == 2
    assert method.end_line == 4
