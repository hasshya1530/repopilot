from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_create_task_with_unknown_repository() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "repository_id": str(uuid4()),
            "title": "Add pagination",
            "description": "Add pagination to the users endpoint.",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Repository not found",
    }


def test_get_unknown_task() -> None:
    response = client.get(f"/api/v1/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Task not found",
    }


def test_update_unknown_task_status() -> None:
    response = client.patch(
        f"/api/v1/tasks/{uuid4()}/status",
        json={
            "status": "completed",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Task not found",
    }


def test_create_task_requires_title() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "repository_id": str(uuid4()),
        },
    )

    assert response.status_code == 422


def test_create_task_rejects_invalid_repository_id() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "repository_id": "not-a-uuid",
            "title": "Add pagination",
        },
    )

    assert response.status_code == 422
