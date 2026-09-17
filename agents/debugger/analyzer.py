from dataclasses import dataclass

from agents.testing.models import TestResult, TestStatus


@dataclass(frozen=True, slots=True)
class FailureAnalysis:
    failure_type: str
    summary: str
    details: str
    test_command: tuple[str, ...]


class FailureAnalyzer:
    def analyze(self, test_result: TestResult) -> FailureAnalysis:
        if test_result.status == TestStatus.PASSED:
            return FailureAnalysis(
                failure_type="none",
                summary="Tests passed successfully.",
                details="No failure requires debugging.",
                test_command=test_result.command,
            )

        output = self._combined_output(test_result)

        return FailureAnalysis(
            failure_type=self._classify_failure(test_result, output),
            summary=self._build_summary(test_result),
            details=output,
            test_command=test_result.command,
        )

    @staticmethod
    def _combined_output(test_result: TestResult) -> str:
        parts = []

        if test_result.stdout.strip():
            parts.append(test_result.stdout.strip())

        if test_result.stderr.strip():
            parts.append(test_result.stderr.strip())

        return "\n\n".join(parts)

    @staticmethod
    def _classify_failure(
        test_result: TestResult,
        output: str,
    ) -> str:
        if test_result.status == TestStatus.TIMEOUT:
            return "timeout"

        lowered = output.lower()

        if "assertionerror" in lowered:
            return "assertion_error"

        if "modulenotfounderror" in lowered:
            return "module_not_found"

        if "importerror" in lowered:
            return "import_error"

        if "syntaxerror" in lowered:
            return "syntax_error"

        if "typeerror" in lowered:
            return "type_error"

        if "nameerror" in lowered:
            return "name_error"

        if "attributeerror" in lowered:
            return "attribute_error"

        if "keyerror" in lowered:
            return "key_error"

        if "indexerror" in lowered:
            return "index_error"

        if test_result.status == TestStatus.ERROR:
            return "test_error"

        return "test_failure"

    @staticmethod
    def _build_summary(test_result: TestResult) -> str:
        if test_result.status == TestStatus.TIMEOUT:
            return "Test execution timed out."

        if test_result.status == TestStatus.ERROR:
            return "Test execution encountered an error."

        if test_result.exit_code != 0:
            return f"Tests failed with exit code {test_result.exit_code}."

        return "Tests failed."
