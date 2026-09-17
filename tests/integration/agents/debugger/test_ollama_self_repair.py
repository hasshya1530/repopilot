from pathlib import Path
from uuid import UUID

import pytest

from agents.debugger.analyzer import FailureAnalyzer
from agents.debugger.models import DebuggerStatus
from agents.debugger.repair_generator import RepairGenerator
from agents.debugger.service import DebuggerService
from agents.implementer.applier.service import ChangeApplier
from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextFile,
)
from agents.llm.factory import create_llm_provider
from agents.llm.provider import LLMProvider
from agents.testing import runner as testing_runner
from apps.api.app.core.config import get_settings

BROKEN_APP = """\
def add(a: int, b: int) -> int:
    return a - b
"""


TEST_FILE = """\
from app import add


def test_add():
    assert add(2, 3) == 5
"""


@pytest.mark.integration
@pytest.mark.ollama
@pytest.mark.asyncio
async def test_ollama_self_repair(
    tmp_path: Path,
) -> None:
    settings = get_settings()

    if settings.model_provider != "ollama":
        pytest.skip(
            "Ollama E2E requires MODEL_PROVIDER=ollama."
        )

    if settings.model_name != "qwen2.5-coder:3b":
        pytest.skip(
            "Ollama E2E expects MODEL_NAME=qwen2.5-coder:3b."
        )

    repository = tmp_path / "repository"
    repository.mkdir()

    (repository / "app.py").write_text(
        BROKEN_APP,
        encoding="utf-8",
    )

    tests_directory = repository / "tests"
    tests_directory.mkdir()

    (tests_directory / "test_app.py").write_text(
        TEST_FILE,
        encoding="utf-8",
    )

    runner = testing_runner.TestRunner()

    initial_result = runner.run(repository)

    assert initial_result.succeeded is False
    assert initial_result.exit_code != 0

    context = ImplementationContext(
        repository_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        task_description=(
            "Fix the failing add function so that "
            "the test passes."
        ),
        files=(
            ImplementationContextFile(
                file_path="app.py",
                content=(repository / "app.py").read_text(
                    encoding="utf-8"
                ),
                reason="Contains the failing implementation.",
            ),
        ),
        symbols=(),
        dependencies=(),
    )

    provider: LLMProvider = create_llm_provider(
        provider=settings.model_provider,
        model_name=settings.model_name,
        ollama_base_url=settings.ollama_base_url,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
    )

    generator = RepairGenerator(provider)

    service = DebuggerService(
        analyzer=FailureAnalyzer(),
        repair_generator=generator,
        change_applier_factory=ChangeApplier,
        test_runner=runner,
        max_attempts=2,
    )

    result = await service.debug(
        repository,
        context,
    )

    assert result.status == DebuggerStatus.FIXED
    assert result.succeeded is True
    assert result.final_test_result.succeeded is True

    final_content = (repository / "app.py").read_text(
        encoding="utf-8"
    )

    assert "return a + b" in final_content
