from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.main import app


@pytest_asyncio.fixture
async def api_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)


def repository_payload(
    *,
    github_repo_id: int | None = None,
    owner: str = "hasshya1530",
    name: str = "repopilot-test",
) -> dict:
    return {
        "owner": owner,
        "name": name,
        "full_name": f"{owner}/{name}",
        "github_repo_id": github_repo_id or 123456789,
        "default_branch": "main",
        "description": "Test repository",
        "is_private": False,
        "clone_url": f"https://github.com/{owner}/{name}.git",
    }


async def create_repository(
    client: AsyncClient,
    *,
    github_repo_id: int | None = None,
) -> dict:
    response = await client.post(
        "/api/v1/repositories",
        json=repository_payload(
            github_repo_id=github_repo_id,
        ),
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "repopilot-api",
    }


@pytest.mark.asyncio
async def test_create_repository(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/repositories",
        json=repository_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["owner"] == "hasshya1530"
    assert data["name"] == "repopilot-test"
    assert data["full_name"] == "hasshya1530/repopilot-test"
    assert data["github_repo_id"] == 123456789
    assert data["default_branch"] == "main"


@pytest.mark.asyncio
async def test_create_duplicate_repository(
    api_client: AsyncClient,
) -> None:
    await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    response = await api_client.post(
        "/api/v1/repositories",
        json=repository_payload(
            github_repo_id=123456789,
            name="another-repository",
        ),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Repository already exists"


@pytest.mark.asyncio
async def test_list_repositories(
    api_client: AsyncClient,
) -> None:
    await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    response = await api_client.get("/api/v1/repositories")

    assert response.status_code == 200

    repositories = response.json()

    assert len(repositories) == 1
    assert repositories[0]["github_repo_id"] == 123456789


@pytest.mark.asyncio
async def test_get_repository(
    api_client: AsyncClient,
) -> None:
    repository = await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    repository_id = repository["id"]

    response = await api_client.get(
        f"/api/v1/repositories/{repository_id}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == repository_id


@pytest.mark.asyncio
async def test_get_unknown_repository(
    api_client: AsyncClient,
) -> None:
    repository_id = uuid4()

    response = await api_client.get(
        f"/api/v1/repositories/{repository_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found"


@pytest.mark.asyncio
async def test_create_task(
    api_client: AsyncClient,
) -> None:
    repository = await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    response = await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": repository["id"],
            "title": "Fix repository issue",
            "description": "Implement the requested change.",
            "external_issue_id": 1001,
            "issue_number": 42,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["repository_id"] == repository["id"]
    assert data["title"] == "Fix repository issue"
    assert data["description"] == "Implement the requested change."
    assert data["external_issue_id"] == 1001
    assert data["issue_number"] == 42
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_task_unknown_repository(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": str(uuid4()),
            "title": "Fix repository issue",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found"


@pytest.mark.asyncio
async def test_list_tasks(
    api_client: AsyncClient,
) -> None:
    repository = await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": repository["id"],
            "title": "First task",
        },
    )

    await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": repository["id"],
            "title": "Second task",
        },
    )

    response = await api_client.get("/api/v1/tasks")

    assert response.status_code == 200

    tasks = response.json()

    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_get_task(
    api_client: AsyncClient,
) -> None:
    repository = await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    create_response = await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": repository["id"],
            "title": "Get me",
        },
    )

    task = create_response.json()

    response = await api_client.get(
        f"/api/v1/tasks/{task['id']}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]


@pytest.mark.asyncio
async def test_get_unknown_task(
    api_client: AsyncClient,
) -> None:
    task_id = uuid4()

    response = await api_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_update_task_status(
    api_client: AsyncClient,
) -> None:
    repository = await create_repository(
        api_client,
        github_repo_id=123456789,
    )

    create_response = await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": repository["id"],
            "title": "Update me",
        },
    )

    task = create_response.json()

    response = await api_client.patch(
        f"/api/v1/tasks/{task['id']}/status",
        json={
            "status": "planning",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "planning"


@pytest.mark.asyncio
async def test_update_unknown_task(
    api_client: AsyncClient,
) -> None:
    response = await api_client.patch(
        f"/api/v1/tasks/{uuid4()}/status",
        json={
            "status": "planning",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_create_task_validation(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/tasks",
        json={
            "repository_id": str(uuid4()),
            "title": "",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_orchestration_unknown_task(
    api_client: AsyncClient,
) -> None:
    task_id = uuid4()

    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/run",
    )

    assert response.status_code == 404
    assert f"Task {task_id} was not found." == response.json()["detail"]
