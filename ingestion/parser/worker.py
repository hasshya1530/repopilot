from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ingestion.parser.files import RepositoryFile
from ingestion.parser.languages.base import CodeSymbol
from ingestion.parser.registry import DEFAULT_LANGUAGE_REGISTRY


def _serialize_symbol(symbol: CodeSymbol) -> dict[str, Any]:
    return {
        "name": symbol.name,
        "symbol_type": symbol.symbol_type.value,
        "start_line": symbol.start_line,
        "end_line": symbol.end_line,
        "parent": symbol.parent,
    }


def _parse_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(request["path"])
    relative_path = str(request["relative_path"])
    extension = str(request["extension"])

    repository_file = RepositoryFile(
        path=path,
        relative_path=relative_path,
        size_bytes=int(request["size_bytes"]),
        extension=extension,
    )

    parser = DEFAULT_LANGUAGE_REGISTRY.get_parser(extension)

    if parser is None:
        return []

    source = repository_file.path.read_bytes()

    symbols = parser.parse(source)

    return [_serialize_symbol(symbol) for symbol in symbols]


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()

        if not line:
            continue

        try:
            request = json.loads(line)
            symbols = _parse_request(request)

            response = {
                "ok": True,
                "symbols": symbols,
            }
        except Exception as exc:
            response = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
