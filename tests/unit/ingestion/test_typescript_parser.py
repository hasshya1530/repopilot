from ingestion.parser.languages import SymbolType, TypeScriptParser


def test_typescript_parser_extracts_module() -> None:
    source = b"""
const value: number = 42;
"""

    symbols = TypeScriptParser().parse(source)

    modules = [symbol for symbol in symbols if symbol.symbol_type == SymbolType.MODULE]

    assert len(modules) == 1
    assert modules[0].name == "module"


def test_typescript_parser_extracts_imports() -> None:
    source = b"""
import React from "react";
import { useState } from "react";
"""

    symbols = TypeScriptParser().parse(source)

    imports = [symbol for symbol in symbols if symbol.symbol_type == SymbolType.IMPORT]

    assert len(imports) == 2


def test_typescript_parser_extracts_functions() -> None:
    source = b"""
function createUser(name: string): string {
    return name;
}

function getUser(id: number): number {
    return id;
}
"""

    symbols = TypeScriptParser().parse(source)

    functions = [symbol for symbol in symbols if symbol.symbol_type == SymbolType.FUNCTION]

    assert [symbol.name for symbol in functions] == [
        "createUser",
        "getUser",
    ]


def test_typescript_parser_extracts_classes_and_methods() -> None:
    source = b"""
class UserService {
    createUser(name: string): string {
        return name;
    }

    getUser(id: number): string {
        return String(id);
    }
}
"""

    symbols = TypeScriptParser().parse(source)

    classes = [symbol for symbol in symbols if symbol.symbol_type == SymbolType.CLASS]

    methods = [symbol for symbol in symbols if symbol.symbol_type == SymbolType.METHOD]

    assert [symbol.name for symbol in classes] == ["UserService"]

    assert [symbol.name for symbol in methods] == [
        "createUser",
        "getUser",
    ]

    assert all(symbol.parent == "UserService" for symbol in methods)


def test_typescript_parser_supports_interfaces() -> None:
    source = b"""
interface User {
    id: number;
    name: string;
}
"""

    symbols = TypeScriptParser().parse(source)

    assert any(
        symbol.name == "module" and symbol.symbol_type == SymbolType.MODULE for symbol in symbols
    )
