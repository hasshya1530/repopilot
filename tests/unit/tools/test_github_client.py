import httpx
import pytest

from tools.github.client import GitHubAPIError, GitHubClient


@pytest.mark.asyncio
async def test_get_authenticated_user() -> None:
    client = GitHubClient("test-token")

    response = httpx.Response(
        200,
        json={
            "id": 123,
            "login": "test-user",
        },
    )

    async def mock_request(
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        assert method == "GET"
        assert url == "/user"

        return response

    client._client.request = mock_request  # type: ignore[method-assign]

    result = await client.get_authenticated_user()

    assert result == {
        "id": 123,
        "login": "test-user",
    }

    await client.close()


@pytest.mark.asyncio
async def test_get_repository() -> None:
    client = GitHubClient("test-token")

    response = httpx.Response(
        200,
        json={
            "id": 123,
            "full_name": "owner/repository",
        },
    )

    async def mock_request(
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        assert method == "GET"
        assert url == "/repos/owner/repository"

        return response

    client._client.request = mock_request  # type: ignore[method-assign]

    result = await client.get_repository(
        "owner",
        "repository",
    )

    assert result["full_name"] == "owner/repository"

    await client.close()


@pytest.mark.asyncio
async def test_get_issue() -> None:
    client = GitHubClient("test-token")

    response = httpx.Response(
        200,
        json={
            "number": 42,
            "title": "Add pagination",
        },
    )

    async def mock_request(
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        assert method == "GET"
        assert url == "/repos/owner/repository/issues/42"

        return response

    client._client.request = mock_request  # type: ignore[method-assign]

    result = await client.get_issue(
        "owner",
        "repository",
        42,
    )

    assert result["number"] == 42
    assert result["title"] == "Add pagination"

    await client.close()


@pytest.mark.asyncio
async def test_get_file_with_ref() -> None:
    client = GitHubClient("test-token")

    response = httpx.Response(
        200,
        json={
            "name": "main.py",
            "path": "src/main.py",
        },
    )

    async def mock_request(
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        assert method == "GET"
        assert url == "/repos/owner/repository/contents/src/main.py"
        assert kwargs["params"] == {"ref": "main"}

        return response

    client._client.request = mock_request  # type: ignore[method-assign]

    result = await client.get_file(
        "owner",
        "repository",
        "src/main.py",
        ref="main",
    )

    assert result["path"] == "src/main.py"

    await client.close()


@pytest.mark.asyncio
async def test_api_error() -> None:
    client = GitHubClient("test-token")

    response = httpx.Response(
        404,
        text='{"message":"Not Found"}',
    )

    async def mock_request(
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        return response

    client._client.request = mock_request  # type: ignore[method-assign]

    with pytest.raises(GitHubAPIError, match="404"):
        await client.get_repository(
            "owner",
            "repository",
        )

    await client.close()
