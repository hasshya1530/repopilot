from ingestion.parser.languages import JavaScriptParser, SymbolType


def test_javascript_parser_extracts_module() -> None:
    source = b"""
const value = 42;
"""

    symbols = JavaScriptParser().parse(source)

    modules = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.MODULE
    ]

    assert len(modules) == 1
    assert modules[0].name == "module"


def test_javascript_parser_extracts_imports() -> None:
    source = b"""
import React from "react";
import { useState } from "react";
"""

    symbols = JavaScriptParser().parse(source)

    imports = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.IMPORT
    ]

    assert len(imports) == 2
    assert "React" in imports[0].name
    assert "useState" in imports[1].name


def test_javascript_parser_extracts_functions() -> None:
    source = b"""
function createUser(name) {
    return name;
}

function getUser(id) {
    return id;
}
"""

    symbols = JavaScriptParser().parse(source)

    functions = [
        symbol
        for symbol in symbols
        if symbol.symbol_type == SymbolType.FUNCTION
    ]

    assert [symbol.name for symbol in functions] == [
        "createUser",
        "getUser",
    ]


def test_javascript_parser_extracts_classes_and_methods() -> None:
    source = b"""
class UserService {
    createUser(name) {
        return name;
    }

    getUser(id) {
        return id;
    }
}
"""

    symbols = JavaScriptParser().parse(source)

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

    assert [symbol.name for symbol in classes] == ["UserService"]

    assert [symbol.name for symbol in methods] == [
        "createUser",
        "getUser",
    ]

    assert all(
        symbol.parent == "UserService"
        for symbol in methods
    )


def test_javascript_parser_tracks_line_ranges() -> None:
    source = b"""class Example {
    method() {
        const value = 1;
        return value;
    }
}
"""

    symbols = JavaScriptParser().parse(source)

    method = next(
        symbol
        for symbol in symbols
        if symbol.name == "method"
    )

    assert method.start_line == 2
    assert method.end_line == 5
