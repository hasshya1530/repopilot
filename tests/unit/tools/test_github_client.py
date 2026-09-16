from unittest.mock import AsyncMock, patch

import httpx
import pytest

from tools.github.client import GitHubAPIError, GitHubClient


@pytest.mark.asyncio
async def test_get_authenticated_user() -> None:
    response = httpx.Response(
        200,
        json={
            "id": 123,
            "login": "hasshya1530",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_authenticated_user()

        assert result["id"] == 123
        assert result["login"] == "hasshya1530"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/user",
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_repository() -> None:
    response = httpx.Response(
        200,
        json={
            "id": 123456,
            "name": "repopilot",
            "full_name": "hasshya1530/repopilot",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_repository(
            "hasshya1530",
            "repopilot",
        )

        assert result["id"] == 123456
        assert result["name"] == "repopilot"
        assert result["full_name"] == "hasshya1530/repopilot"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot",
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_issue() -> None:
    response = httpx.Response(
        200,
        json={
            "id": 987654,
            "number": 42,
            "title": "Add repository indexing",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_issue(
            "hasshya1530",
            "repopilot",
            42,
        )

        assert result["id"] == 987654
        assert result["number"] == 42
        assert result["title"] == "Add repository indexing"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot/issues/42",
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_file_with_ref() -> None:
    response = httpx.Response(
        200,
        json={
            "name": "README.md",
            "path": "README.md",
            "content": "SGVsbG8=",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_file(
            "hasshya1530",
            "repopilot",
            "README.md",
            ref="main",
        )

        assert result["name"] == "README.md"
        assert result["path"] == "README.md"
        assert result["content"] == "SGVsbG8="

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot/contents/README.md",
            params={"ref": "main"},
        )

        await client.close()


@pytest.mark.asyncio
async def test_github_api_error() -> None:
    response = httpx.Response(
        404,
        text='{"message":"Not Found"}',
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        with pytest.raises(
            GitHubAPIError,
            match="GitHub API request failed: 404",
        ):
            await client.get_repository(
                "hasshya1530",
                "does-not-exist",
            )

        await client.close()
