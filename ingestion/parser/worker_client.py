from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from ingestion.parser.files import RepositoryFile
from ingestion.parser.languages.base import CodeSymbol, SymbolType


class ParserWorkerError(RuntimeError):
    """Raised when the isolated parser worker fails."""


@dataclass(frozen=True, slots=True)
class ParserWorkerResponse:
    symbols: list[CodeSymbol]


class ParserWorkerClient:
    """Persistent subprocess client for native Tree-sitter parsing."""

    def __init__(self) -> None:
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ingestion.parser.worker",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def parse(self, repository_file: RepositoryFile) -> list[CodeSymbol]:
        if self._process.poll() is not None:
            raise ParserWorkerError(
                "Parser worker exited before parsing could complete."
            )

        if self._process.stdin is None or self._process.stdout is None:
            raise ParserWorkerError("Parser worker pipes are unavailable.")

        request = {
            "path": str(repository_file.path),
            "relative_path": repository_file.relative_path,
            "size_bytes": repository_file.size_bytes,
            "extension": repository_file.extension,
        }

        try:
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise ParserWorkerError(
                "Failed to send request to parser worker."
            ) from exc

        response_line = self._process.stdout.readline()

        if not response_line:
            stderr = self._read_stderr()
            raise ParserWorkerError(
                "Parser worker exited without a response."
                + (f" stderr: {stderr}" if stderr else "")
            )

        try:
            response = json.loads(response_line)
        except json.JSONDecodeError as exc:
            raise ParserWorkerError(
                f"Parser worker returned invalid JSON: {response_line!r}"
            ) from exc

        if not response.get("ok", False):
            raise ParserWorkerError(
                str(response.get("error", "Unknown parser worker error"))
            )

        return [
            self._deserialize_symbol(symbol)
            for symbol in response.get("symbols", [])
        ]

    def close(self) -> None:
        if self._process.poll() is not None:
            return

        try:
            if self._process.stdin is not None:
                self._process.stdin.close()

            self._process.wait(timeout=5)
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
            self._process.kill()
            self._process.wait()

    def __enter__(self) -> ParserWorkerClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        self.close()

    @staticmethod
    def _deserialize_symbol(data: dict[str, Any]) -> CodeSymbol:
        return CodeSymbol(
            name=str(data["name"]),
            symbol_type=SymbolType(str(data["symbol_type"])),
            start_line=int(data["start_line"]),
            end_line=int(data["end_line"]),
            parent=(
                None
                if data.get("parent") is None
                else str(data["parent"])
            ),
        )

    def _read_stderr(self) -> str:
        if self._process.stderr is None:
            return ""

        # stderr is intentionally only inspected after the worker exits.
        return self._process.stderr.read().strip()


def is_native_tree_sitter_extension(extension: str) -> bool:
    return extension.lower() in {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
    }
