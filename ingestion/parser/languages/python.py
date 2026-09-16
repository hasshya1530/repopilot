import tree_sitter_python
from tree_sitter import Language, Node, Parser

from ingestion.parser.languages.base import (
    CodeSymbol,
    LanguageParser,
    SymbolType,
)


class PythonParser(LanguageParser):
    def __init__(self) -> None:
        self._language = Language(tree_sitter_python.language())
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
                name = self._node_text(child, source)

                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type=SymbolType.IMPORT,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

            elif child.type == "import_from_statement":
                name = self._node_text(child, source)

                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type=SymbolType.IMPORT,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

            elif child.type == "class_definition":
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

            elif child.type == "function_definition":
                name = self._definition_name(child)

                symbol_type = SymbolType.METHOD if parent is not None else SymbolType.FUNCTION

                symbols.append(
                    CodeSymbol(
                        name=name,
                        symbol_type=symbol_type,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        parent=parent,
                    )
                )

            elif child.type == "decorated_definition":
                self._extract_symbols(
                    node=child,
                    source=source,
                    symbols=symbols,
                    parent=parent,
                )

            elif child.type == "block":
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
    def _node_text(
        node: Node,
        source: bytes,
    ) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8")
