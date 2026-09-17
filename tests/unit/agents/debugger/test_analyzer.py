from agents.debugger.analyzer import FailureAnalyzer
from agents.testing import models as testing_models


def make_result(
    status: testing_models.TestStatus,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 1,
) -> testing_models.TestResult:
    return testing_models.TestResult(
        status=status,
        command=("pytest", "-q"),
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=0.5,
    )


def test_analyze_assertion_failure() -> None:
    result = make_result(
        testing_models.TestStatus.FAILED,
        stdout="FAILED tests/test_auth.py::test_login\n",
        stderr="AssertionError: expected 200 but got 401",
    )

    analysis = FailureAnalyzer().analyze(result)

    assert analysis.failure_type == "assertion_error"
    assert "Tests failed" in analysis.summary
    assert "AssertionError" in analysis.details
    assert analysis.test_command == ("pytest", "-q")


def test_analyze_syntax_error() -> None:
    result = make_result(
        testing_models.TestStatus.FAILED,
        stderr="SyntaxError: invalid syntax",
    )

    analysis = FailureAnalyzer().analyze(result)

    assert analysis.failure_type == "syntax_error"


def test_analyze_timeout() -> None:
    result = make_result(
        testing_models.TestStatus.TIMEOUT,
        stderr="Command timed out",
    )

    analysis = FailureAnalyzer().analyze(result)

    assert analysis.failure_type == "timeout"
    assert analysis.summary == "Test execution timed out."


def test_analyze_passed_result() -> None:
    result = make_result(
        testing_models.TestStatus.PASSED,
        stdout="1 passed",
        exit_code=0,
    )

    analysis = FailureAnalyzer().analyze(result)

    assert analysis.failure_type == "none"
    assert analysis.summary == "Tests passed successfully."
    assert analysis.details == "No failure requires debugging."
