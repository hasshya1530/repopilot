from __future__ import annotations

import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from ingestion.parser.languages.base import (
    CodeSymbol,
    LanguageParser,
    SymbolType,
)


class TypeScriptParser(LanguageParser):
    """Extract TypeScript or TSX symbols with Tree-sitter."""

    def __init__(self, *, tsx: bool = False) -> None:
        self._tsx = tsx

        language_factory = (
            tree_sitter_typescript.language_tsx
            if tsx
            else tree_sitter_typescript.language_typescript
        )

        self._language = Language(language_factory())
        self._parser = Parser(self._language)

    def parse(self, source: bytes) -> list[CodeSymbol]:
        tree = self._parser.parse(source)

        symbols: list[CodeSymbol] = [
            CodeSymbol(
                name="module",
                symbol_type=SymbolType.MODULE,
                start_line=1,
                end_line=tree.root_node.end_point.row + 1,
            )
        ]

        self._extract_symbols(
            node=tree.root_node,
            source=source,
            symbols=symbols,
        )

        return symbols

    def _extract_symbols(
        self,
        node: Node,
        source: bytes,
        symbols: list[CodeSymbol],
        parent: str | None = None,
    ) -> None:
        for child in node.children:
            if child.type == "import_statement":
                symbols.append(
                    CodeSymbol(
                        name=self._node_text(child, source),
                        symbol_type=SymbolType.IMPORT,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

            elif child.type in {
                "function_declaration",
                "generator_function_declaration",
            }:
                name = self._definition_name(child)

                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type=(
                            SymbolType.METHOD
                            if parent is not None
                            else SymbolType.FUNCTION
                        ),
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

            elif child.type in {
                "class_declaration",
                "abstract_class_declaration",
            }:
                name = self._definition_name(child)

                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type=SymbolType.CLASS,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

                self._extract_symbols(
                    node=child,
                    source=source,
                    symbols=symbols,
                    parent=name,
                )

            elif child.type == "method_definition":
                name = self._definition_name(child)

                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

            elif child.type in {
                "class_body",
                "statement_block",
            }:
                self._extract_symbols(
                    node=child,
                    source=source,
                    symbols=symbols,
                    parent=parent,
                )

    @staticmethod
    def _definition_name(node: Node) -> str:
        name_node = node.child_by_field_name("name")

        if name_node is None or name_node.text is None:
            return "<anonymous>"

        return name_node.text.decode("utf-8")

    @staticmethod
    def _node_text(node: Node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8")
