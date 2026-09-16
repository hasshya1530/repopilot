import tree_sitter_python
from tree_sitter import Language, Node, Parser

from ingestion.graph.models import SymbolRelation, SymbolRelationship
from ingestion.graph.parsers.base import RelationshipParser


class PythonRelationshipParser(RelationshipParser):
    """Extract imports and direct function/method calls from Python."""

    def __init__(self) -> None:
        self._language = Language(tree_sitter_python.language())
        self._parser = Parser(self._language)

    def parse(
        self,
        source: bytes,
        file_path: str,
    ) -> list[SymbolRelationship]:
        tree = self._parser.parse(source)
        relationships: list[SymbolRelationship] = []

        self._visit(
            node=tree.root_node,
            source=source,
            file_path=file_path,
            current_symbol=None,
            relationships=relationships,
        )

        return relationships

    def _visit(
        self,
        *,
        node: Node,
        source: bytes,
        file_path: str,
        current_symbol: str | None,
        relationships: list[SymbolRelationship],
    ) -> None:
        symbol = current_symbol

        if node.type in {"function_definition", "class_definition"}:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                symbol = self._node_text(name_node, source)

        if node.type == "import_statement":
            self._extract_import(
                node=node,
                source=source,
                file_path=file_path,
                current_symbol=symbol,
                relationships=relationships,
            )
        elif node.type == "import_from_statement":
            self._extract_import_from(
                node=node,
                source=source,
                file_path=file_path,
                current_symbol=symbol,
                relationships=relationships,
            )
        elif node.type == "call":
            function_node = node.child_by_field_name("function")
            if function_node is not None and symbol is not None:
                target_name = self._node_text(function_node, source)
                relationships.append(
                    SymbolRelationship(
                        source_name=symbol,
                        target_name=target_name,
                        relation=SymbolRelation.CALLS,
                        source_file=file_path,
                    )
                )

        for child in node.children:
            self._visit(
                node=child,
                source=source,
                file_path=file_path,
                current_symbol=symbol,
                relationships=relationships,
            )

    @staticmethod
    def _extract_import(
        *,
        node: Node,
        source: bytes,
        file_path: str,
        current_symbol: str | None,
        relationships: list[SymbolRelationship],
    ) -> None:
        source_name = current_symbol or "__module__"

        for child in node.named_children:
            imported_name = PythonRelationshipParser._node_text(child, source)

            relationships.append(
                SymbolRelationship(
                    source_name=source_name,
                    target_name=imported_name,
                    relation=SymbolRelation.IMPORTS,
                    source_file=file_path,
                )
            )

    @staticmethod
    def _extract_import_from(
        *,
        node: Node,
        source: bytes,
        file_path: str,
        current_symbol: str | None,
        relationships: list[SymbolRelationship],
    ) -> None:
        source_name = current_symbol or "__module__"
        named_children = node.named_children

        if len(named_children) < 2:
            return

        module_name = PythonRelationshipParser._node_text(
            named_children[0],
            source,
        )

        for imported_node in named_children[1:]:
            imported_name = PythonRelationshipParser._node_text(
                imported_node,
                source,
            )

            relationships.append(
                SymbolRelationship(
                    source_name=source_name,
                    target_name=imported_name,
                    relation=SymbolRelation.IMPORTS,
                    source_file=file_path,
                    target_file=module_name,
                )
            )

    @staticmethod
    def _node_text(node: Node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8")
