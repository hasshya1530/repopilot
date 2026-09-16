from pathlib import Path

import pytest

from ingestion.parser.discovery import DiscoveryConfig, discover_files


def test_discover_files_returns_source_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "README.md").write_text("# RepoPilot", encoding="utf-8")
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")

    files = discover_files(tmp_path)

    assert [file.relative_path for file in files] == [
        "README.md",
        "config.json",
        "main.py",
    ]


def test_discover_files_ignores_directories(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    ignored = tmp_path / "node_modules" / "package"
    ignored.mkdir(parents=True)
    (ignored / "index.js").write_text(
        "console.log('ignored')",
        encoding="utf-8",
    )

    files = discover_files(tmp_path)

    assert [file.relative_path for file in files] == [
        "main.py",
    ]


def test_discover_files_ignores_binary_extensions(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "module.pyc").write_bytes(b"binary")

    files = discover_files(tmp_path)

    assert [file.relative_path for file in files] == [
        "main.py",
    ]


def test_discover_files_ignores_large_files(tmp_path: Path) -> None:
    (tmp_path / "small.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "large.py").write_text("x" * 100, encoding="utf-8")

    config = DiscoveryConfig(max_file_size_bytes=50)

    files = discover_files(tmp_path, config)

    assert [file.relative_path for file in files] == [
        "small.py",
    ]


def test_discover_files_is_sorted(tmp_path: Path) -> None:
    (tmp_path / "z.py").write_text("z", encoding="utf-8")
    (tmp_path / "a.py").write_text("a", encoding="utf-8")

    nested = tmp_path / "src"
    nested.mkdir()
    (nested / "m.py").write_text("m", encoding="utf-8")

    files = discover_files(tmp_path)

    assert [file.relative_path for file in files] == [
        "a.py",
        "src/m.py",
        "z.py",
    ]


def test_discover_files_requires_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "repository.txt"
    file_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        discover_files(file_path)


def test_discover_files_requires_existing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        discover_files(missing)

def test_discover_files_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        """
.env
*.log
generated/
""".strip(),
        encoding="utf-8",
    )

    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    (tmp_path / ".env").write_text(
        "SECRET=value",
        encoding="utf-8",
    )

    (tmp_path / "debug.log").write_text(
        "debug",
        encoding="utf-8",
    )

    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "output.py").write_text(
        "generated",
        encoding="utf-8",
    )

    files = discover_files(tmp_path)

    assert [file.relative_path for file in files] == [
        ".gitignore",
        "main.py",
    ]


def test_discover_files_can_disable_gitignore(
    tmp_path: Path,
) -> None:
    (tmp_path / ".gitignore").write_text(
        "*.log",
        encoding="utf-8",
    )

    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    (tmp_path / "debug.log").write_text(
        "debug",
        encoding="utf-8",
    )

    config = DiscoveryConfig(
        respect_gitignore=False,
    )

    files = discover_files(tmp_path, config)

    assert [file.relative_path for file in files] == [
        ".gitignore",
        "debug.log",
        "main.py",
    ]


def test_discover_files_handles_missing_gitignore(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    files = discover_files(tmp_path)

    assert [file.relative_path for file in files] == [
        "main.py",
    ]
