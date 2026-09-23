from pathlib import Path
from uuid import UUID

from agents.implementer.context.errors import (
    ImplementationContextConfigurationError,
    ImplementationContextRetrievalError,
)
from agents.implementer.context.models import (
    ImplementationContext,
    ImplementationContextDependency,
    ImplementationContextFile,
    ImplementationContextSymbol,
)
from agents.planner.plan_models import ImplementationPlan
from ingestion.change_context.models import RepositoryChangeContext


class ImplementationContextService:
    """Build source-level context required by the implementation agent."""

    def build(
        self,
        *,
        repository_id: UUID,
        repository_path: Path,
        task_description: str,
        change_context: RepositoryChangeContext,
        plan: ImplementationPlan,
    ) -> ImplementationContext:
        self._validate_inputs(
            repository_id=repository_id,
            repository_path=repository_path,
            task_description=task_description,
        )

        files: list[ImplementationContextFile] = []
        symbols: list[ImplementationContextSymbol] = []

        planned_modify_paths = {
            item.file_path
            for item in plan.files_to_modify
        }

        planned_create_paths = {
            item.file_path
            for item in plan.files_to_create
        }

        test_paths = {
            item.file_path
            for item in plan.test_files
        }

        self._validate_plan_file_operations(
            repository_path=repository_path,
            modify_paths=planned_modify_paths,
            create_paths=planned_create_paths,
            test_paths=test_paths,
        )

        requested_files = tuple(
            dict.fromkeys(
                
                    item.file_path
                    for item in (
                        list(plan.files_to_modify)
                        + list(plan.test_files)
                    )
                    if item.file_path.strip()
                
            )
        )

        change_context_by_path = {
            item.file_path: item
            for item in change_context.files
        }

        for file_path in requested_files:
            source_path = repository_path / file_path

            if not source_path.is_file():
                raise ImplementationContextRetrievalError(
                    f"Repository file does not exist: {file_path}"
                )

            try:
                content = source_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ImplementationContextRetrievalError(
                    f"Unable to read repository file: {file_path}"
                ) from exc

            context_file = change_context_by_path.get(file_path)

            if context_file is not None:
                reason = context_file.reason
            else:
                reason = self._file_reason(
                    file_path=file_path,
                    change_context=change_context,
                    plan=plan,
                )

            files.append(
                ImplementationContextFile(
                    file_path=file_path,
                    content=content,
                    reason=reason,
                )
            )

        file_content_by_path = {
            item.file_path: item.content
            for item in files
        }

        planned_symbol_ids = {
            symbol.symbol_id
            for symbol in change_context.symbols
            if symbol.file_path in planned_modify_paths
        }

        for symbol in change_context.symbols:
            if symbol.file_path not in planned_modify_paths:
                continue

            symbol_source = file_content_by_path.get(symbol.file_path)

            if symbol_source is None:
                continue

            symbol_content = self._extract_lines(
                symbol_source,
                symbol.start_line,
                symbol.end_line,
            )

            symbols.append(
                ImplementationContextSymbol(
                    symbol_id=symbol.symbol_id,
                    file_path=symbol.file_path,
                    name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    content=symbol_content,
                    reason=symbol.reason,
                )
            )

        dependencies = tuple(
            ImplementationContextDependency(
                source_symbol_id=item.source_symbol_id,
                target_symbol_id=item.target_symbol_id,
                relation=item.relation,
                depth=item.depth,
            )
            for item in change_context.dependencies
            if (
                item.source_symbol_id in planned_symbol_ids
                or item.target_symbol_id in planned_symbol_ids
            )
        )

        return ImplementationContext(
            repository_id=repository_id,
            task_description=task_description,
            files=tuple(files),
            symbols=tuple(symbols),
            dependencies=dependencies,
        )

    @staticmethod
    def _validate_plan_file_operations(
        *,
        repository_path: Path,
        modify_paths: set[str],
        create_paths: set[str],
        test_paths: set[str],
    ) -> None:
        existing_create_paths = sorted(
            path
            for path in create_paths
            if (repository_path / path).is_file()
        )

        if existing_create_paths:
            joined = ", ".join(existing_create_paths)
            raise ImplementationContextRetrievalError(
                "Implementation plan incorrectly classifies existing "
                f"repository files as creations: {joined}"
            )

        missing_modify_paths = sorted(
            path
            for path in modify_paths
            if not (repository_path / path).is_file()
        )

        if missing_modify_paths:
            joined = ", ".join(missing_modify_paths)
            raise ImplementationContextRetrievalError(
                "Implementation plan references missing files for modification: "
                f"{joined}"
            )

        missing_test_paths = sorted(
            path
            for path in test_paths
            if not (repository_path / path).is_file()
            and path not in create_paths
        )

        if missing_test_paths:
            joined = ", ".join(missing_test_paths)
            raise ImplementationContextRetrievalError(
                "Implementation plan references test files that do not "
                f"exist and are not planned for creation: {joined}"
            )

    @staticmethod
    def _validate_inputs(
        *,
        repository_id: UUID,
        repository_path: Path,
        task_description: str,
    ) -> None:
        if not repository_id:
            raise ImplementationContextConfigurationError(
                "repository_id is required."
            )

        if not repository_path.is_dir():
            raise ImplementationContextConfigurationError(
                f"Repository path is not a directory: {repository_path}"
            )

        if not task_description.strip():
            raise ImplementationContextConfigurationError(
                "task_description must not be empty."
            )

    @staticmethod
    def _file_reason(
        *,
        file_path: str,
        change_context: RepositoryChangeContext,
        plan: ImplementationPlan,
    ) -> str:
        for context_file in change_context.files:
            if context_file.file_path == file_path:
                return context_file.reason

        for planned_file in plan.files_to_modify:
            if planned_file.file_path == file_path:
                return planned_file.reason

        for test_file in plan.test_files:
            if test_file.file_path == file_path:
                return test_file.reason

        for created_file in plan.files_to_create:
            if created_file.file_path == file_path:
                return created_file.reason

        return "Included as relevant repository context."

    @staticmethod
    def _extract_lines(
        content: str,
        start_line: int,
        end_line: int,
    ) -> str:
        lines = content.splitlines()

        if start_line < 1 or end_line < start_line:
            raise ImplementationContextRetrievalError(
                f"Invalid symbol line range: {start_line}-{end_line}"
            )

        if start_line > len(lines):
            raise ImplementationContextRetrievalError(
                f"Symbol start line {start_line} exceeds file length {len(lines)}."
            )

        end_line = min(end_line, len(lines))

        return "\n".join(lines[start_line - 1 : end_line])
