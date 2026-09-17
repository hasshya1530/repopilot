from __future__ import annotations

from pathlib import Path

from agents.testing.errors import TestDetectionError


class TestDetector:
    """Detect the test command supported by a repository."""

    def detect(self, repository_path: Path) -> list[str]:
        repository = repository_path.resolve()

        if not repository.exists():
            raise TestDetectionError(
                f"Repository does not exist: {repository}"
            )

        if not repository.is_dir():
            raise TestDetectionError(
                f"Repository is not a directory: {repository}"
            )

        if (repository / "pytest.ini").exists():
            return ["python", "-m", "pytest"]

        if (repository / "pyproject.toml").exists():
            pyproject = (repository / "pyproject.toml").read_text(
                encoding="utf-8"
            )

            if "pytest" in pyproject:
                return ["python", "-m", "pytest"]

        if (repository / "tests").is_dir():
            python_files = list((repository / "tests").rglob("*.py"))

            if python_files:
                return ["python", "-m", "pytest"]

        if (repository / "package.json").exists():
            return ["npm", "test"]

        if (repository / "go.mod").exists():
            return ["go", "test", "./..."]

        if (repository / "Cargo.toml").exists():
            return ["cargo", "test"]

        raise TestDetectionError(
            "Unable to detect a supported test framework."
        )
