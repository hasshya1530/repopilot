from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_get_unknown_repository() -> None:
    response = client.get(f"/api/v1/repositories/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Repository not found",
    }


def test_create_repository_requires_owner() -> None:
    response = client.post(
        "/api/v1/repositories",
        json={
            "name": "repopilot",
            "full_name": "hasshya1530/repopilot",
            "github_repo_id": 123456,
            "clone_url": "https://github.com/hasshya1530/repopilot.git",
        },
    )

    assert response.status_code == 422


def test_create_repository_requires_name() -> None:
    response = client.post(
        "/api/v1/repositories",
        json={
            "owner": "hasshya1530",
            "full_name": "hasshya1530/repopilot",
            "github_repo_id": 123456,
            "clone_url": "https://github.com/hasshya1530/repopilot.git",
        },
    )

    assert response.status_code == 422


def test_create_repository_rejects_invalid_github_repo_id() -> None:
    response = client.post(
        "/api/v1/repositories",
        json={
            "owner": "hasshya1530",
            "name": "repopilot",
            "full_name": "hasshya1530/repopilot",
            "github_repo_id": "invalid",
            "clone_url": "https://github.com/hasshya1530/repopilot.git",
        },
    )

    assert response.status_code == 422


def test_create_repository_rejects_empty_name() -> None:
    response = client.post(
        "/api/v1/repositories",
        json={
            "owner": "hasshya1530",
            "name": "",
            "full_name": "hasshya1530/repopilot",
            "github_repo_id": 123456,
            "clone_url": "https://github.com/hasshya1530/repopilot.git",
        },
    )

    assert response.status_code == 422
