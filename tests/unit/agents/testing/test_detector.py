from pathlib import Path

import pytest

from agents.testing.detector import TestDetector
from agents.testing.errors import TestDetectionError as DetectionError


def test_detects_pytest_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\ndependencies = ['pytest']\n"
    )

    command = TestDetector().detect(tmp_path)

    assert command == ["python", "-m", "pytest"]


def test_detects_pytest_from_pytest_ini(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")

    command = TestDetector().detect(tmp_path)

    assert command == ["python", "-m", "pytest"]


def test_detects_pytest_from_tests_directory(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text("def test_example(): pass\n")

    command = TestDetector().detect(tmp_path)

    assert command == ["python", "-m", "pytest"]


def test_detects_npm(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"scripts": {"test": "vitest"}}'
    )

    command = TestDetector().detect(tmp_path)

    assert command == ["npm", "test"]


def test_detects_go(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example\n")

    command = TestDetector().detect(tmp_path)

    assert command == ["go", "test", "./..."]


def test_detects_cargo(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'example'\n")

    command = TestDetector().detect(tmp_path)

    assert command == ["cargo", "test"]


def test_rejects_missing_repository(tmp_path: Path) -> None:
    with pytest.raises(DetectionError):
        TestDetector().detect(tmp_path / "missing")


def test_rejects_unsupported_repository(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Example\n")

    with pytest.raises(DetectionError):
        TestDetector().detect(tmp_path)
