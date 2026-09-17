from uuid import uuid4

from ingestion.architecture.models import (
    ArchitectureComponent,
    ArchitectureComponentType,
    ArchitectureDependency,
    ArchitectureDependencyType,
    ArchitectureReport,
)


def test_architecture_component_is_immutable() -> None:
    component = ArchitectureComponent(
        name="auth",
        component_type=ArchitectureComponentType.MODULE,
        files=("auth.py",),
        symbols=("AuthService", "login"),
    )

    assert component.name == "auth"
    assert component.component_type == ArchitectureComponentType.MODULE
    assert component.files == ("auth.py",)
    assert component.symbols == ("AuthService", "login")


def test_architecture_dependency_contains_relationship_metadata() -> None:
    dependency = ArchitectureDependency(
        source="api",
        target="auth",
        dependency_type=ArchitectureDependencyType.IMPORTS,
    )

    assert dependency.source == "api"
    assert dependency.target == "auth"
    assert dependency.dependency_type == ArchitectureDependencyType.IMPORTS


def test_architecture_report_contains_repository_structure() -> None:
    repository_id = uuid4()

    report = ArchitectureReport(
        repository_id=repository_id,
        components=(
            ArchitectureComponent(
                name="auth",
                component_type=ArchitectureComponentType.MODULE,
                files=("auth.py",),
                symbols=("AuthService",),
            ),
        ),
        dependencies=(
            ArchitectureDependency(
                source="api",
                target="auth",
                dependency_type=ArchitectureDependencyType.IMPORTS,
            ),
        ),
        entry_points=("api.py",),
    )

    assert report.repository_id == repository_id
    assert len(report.components) == 1
    assert len(report.dependencies) == 1
    assert report.entry_points == ("api.py",)
