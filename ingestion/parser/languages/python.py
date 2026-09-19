from __future__ import annotations

import ast

from ingestion.parser.languages.base import (
    CodeSymbol,
    LanguageParser,
    SymbolType,
)


class PythonParser(LanguageParser):
    """Extract Python symbols using Python's standard-library AST parser."""

    def parse(self, source: bytes) -> list[CodeSymbol]:
        text = source.decode("utf-8", errors="replace")

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []

        lines = text.splitlines()

        symbols: list[CodeSymbol] = [
            CodeSymbol(
                name="module",
                symbol_type=SymbolType.MODULE,
                start_line=1,
                end_line=max(len(lines), 1),
            )
        ]

        self._visit_body(
            body=tree.body,
            symbols=symbols,
            parent=None,
        )

        return symbols

    def _visit_body(
        self,
        *,
        body: list[ast.stmt],
        symbols: list[CodeSymbol],
        parent: str | None,
    ) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                start_line, end_line = self._node_lines(node)

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type=SymbolType.CLASS,
                        start_line=start_line,
                        end_line=end_line,
                        parent=parent,
                    )
                )

                self._visit_body(
                    body=node.body,
                    symbols=symbols,
                    parent=node.name,
                )
                continue

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start_line, end_line = self._node_lines(node)

                symbol_type = (
                    SymbolType.METHOD
                    if parent is not None
                    else SymbolType.FUNCTION
                )

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type=symbol_type,
                        start_line=start_line,
                        end_line=end_line,
                        parent=parent,
                    )
                )

                self._visit_nested_functions(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )
                continue

            if isinstance(node, (ast.Import, ast.ImportFrom)):
                start_line, end_line = self._node_lines(node)

                symbols.append(
                    CodeSymbol(
                        name=self._import_name(node),
                        symbol_type=SymbolType.IMPORT,
                        start_line=start_line,
                        end_line=end_line,
                        parent=parent,
                    )
                )
                continue

            if isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                ),
            ):
                self._visit_body(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )

                self._visit_body(
                    body=node.orelse,
                    symbols=symbols,
                    parent=parent,
                )
                continue

            if isinstance(node, (ast.With, ast.AsyncWith)):
                self._visit_body(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )
                continue

            if isinstance(node, ast.Try):
                self._visit_body(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )

                self._visit_body(
                    body=node.orelse,
                    symbols=symbols,
                    parent=parent,
                )

                self._visit_body(
                    body=node.finalbody,
                    symbols=symbols,
                    parent=parent,
                )

                for handler in node.handlers:
                    self._visit_body(
                        body=handler.body,
                        symbols=symbols,
                        parent=parent,
                    )

    def _visit_nested_functions(
        self,
        *,
        body: list[ast.stmt],
        symbols: list[CodeSymbol],
        parent: str | None,
    ) -> None:
        """Find definitions nested inside a function body."""

        for node in body:
            if isinstance(node, ast.ClassDef):
                start_line, end_line = self._node_lines(node)

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type=SymbolType.CLASS,
                        start_line=start_line,
                        end_line=end_line,
                        parent=parent,
                    )
                )

                self._visit_body(
                    body=node.body,
                    symbols=symbols,
                    parent=node.name,
                )
                continue

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start_line, end_line = self._node_lines(node)

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type=SymbolType.FUNCTION,
                        start_line=start_line,
                        end_line=end_line,
                        parent=parent,
                    )
                )

                self._visit_nested_functions(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )
                continue

            if isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                ),
            ):
                self._visit_nested_functions(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )

                self._visit_nested_functions(
                    body=node.orelse,
                    symbols=symbols,
                    parent=parent,
                )
                continue

            if isinstance(node, (ast.With, ast.AsyncWith)):
                self._visit_nested_functions(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )
                continue

            if isinstance(node, ast.Try):
                self._visit_nested_functions(
                    body=node.body,
                    symbols=symbols,
                    parent=parent,
                )

                self._visit_nested_functions(
                    body=node.orelse,
                    symbols=symbols,
                    parent=parent,
                )

                self._visit_nested_functions(
                    body=node.finalbody,
                    symbols=symbols,
                    parent=parent,
                )

                for handler in node.handlers:
                    self._visit_nested_functions(
                        body=handler.body,
                        symbols=symbols,
                        parent=parent,
                    )

    @staticmethod
    def _node_lines(
        node: ast.AST,
    ) -> tuple[int, int]:
        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line)

        return (
            max(start_line, 1),
            max(end_line, start_line),
        )

    @staticmethod
    def _import_name(
        node: ast.Import | ast.ImportFrom,
    ) -> str:
        if isinstance(node, ast.Import):
            names = ", ".join(
                alias.name
                for alias in node.names
            )
            return f"import {names}"

        module = node.module or ""

        names = ", ".join(
            alias.name
            for alias in node.names
        )

        if node.level:
            module = f"{'.' * node.level}{module}"

        return f"from {module} import {names}"
