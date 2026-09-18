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


@pytest.mark.asyncio
async def test_create_branch() -> None:
    response = httpx.Response(
        201,
        json={
            "ref": "refs/heads/repopilot/test-branch",
            "object": {
                "sha": "abc123",
            },
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.create_branch(
            "hasshya1530",
            "repopilot",
            "repopilot/test-branch",
            "abc123",
        )

        assert result["ref"] == "refs/heads/repopilot/test-branch"

        mock_client.request.assert_awaited_once_with(
            "POST",
            "/repos/hasshya1530/repopilot/git/refs",
            json={
                "ref": "refs/heads/repopilot/test-branch",
                "sha": "abc123",
            },
        )

        await client.close()


@pytest.mark.asyncio
async def test_create_or_update_file() -> None:
    response = httpx.Response(
        201,
        json={
            "content": {
                "path": "src/example.py",
            },
            "commit": {
                "sha": "commit123",
            },
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.create_or_update_file(
            "hasshya1530",
            "repopilot",
            "src/example.py",
            "print('hello')\n",
            message="feat: add example",
            branch="repopilot/test-branch",
        )

        assert result["commit"]["sha"] == "commit123"

        mock_client.request.assert_awaited_once()

        call = mock_client.request.await_args
        assert call.args == (
            "PUT",
            "/repos/hasshya1530/repopilot/contents/src/example.py",
        )

        payload = call.kwargs["json"]

        assert payload["message"] == "feat: add example"
        assert payload["branch"] == "repopilot/test-branch"
        assert payload["content"] == "cHJpbnQoJ2hlbGxvJykK"

        await client.close()


@pytest.mark.asyncio
async def test_create_pull_request() -> None:
    response = httpx.Response(
        201,
        json={
            "number": 42,
            "title": "feat: add repository indexing",
            "draft": True,
            "html_url": "https://github.com/hasshya1530/repopilot/pull/42",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.create_pull_request(
            "hasshya1530",
            "repopilot",
            title="feat: add repository indexing",
            body="Automated changes generated by RepoPilot.",
            head="repopilot/test-branch",
            base="main",
        )

        assert result["number"] == 42
        assert result["draft"] is True

        mock_client.request.assert_awaited_once_with(
            "POST",
            "/repos/hasshya1530/repopilot/pulls",
            json={
                "title": "feat: add repository indexing",
                "body": "Automated changes generated by RepoPilot.",
                "head": "repopilot/test-branch",
                "base": "main",
                "draft": True,
            },
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_pull_request() -> None:
    response = httpx.Response(
        200,
        json={
            "number": 42,
            "title": "feat: add repository indexing",
            "state": "open",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_pull_request(
            "hasshya1530",
            "repopilot",
            42,
        )

        assert result["number"] == 42
        assert result["state"] == "open"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot/pulls/42",
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_git_ref() -> None:
    response = httpx.Response(
        200,
        json={
            "ref": "refs/heads/main",
            "object": {
                "sha": "abc123",
                "type": "commit",
            },
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_git_ref(
            "hasshya1530",
            "repopilot",
            "heads/main",
        )

        assert result["ref"] == "refs/heads/main"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot/git/ref/heads/main",
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_commit() -> None:
    response = httpx.Response(
        200,
        json={
            "sha": "commit123",
            "tree": {
                "sha": "tree123",
            },
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_commit(
            "hasshya1530",
            "repopilot",
            "commit123",
        )

        assert result["sha"] == "commit123"
        assert result["tree"]["sha"] == "tree123"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot/git/commits/commit123",
        )

        await client.close()


@pytest.mark.asyncio
async def test_get_tree_recursive() -> None:
    response = httpx.Response(
        200,
        json={
            "sha": "tree123",
            "tree": [
                {
                    "path": "src/example.py",
                    "type": "blob",
                    "sha": "blob123",
                },
            ],
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.get_tree(
            "hasshya1530",
            "repopilot",
            "tree123",
            recursive=True,
        )

        assert result["sha"] == "tree123"

        mock_client.request.assert_awaited_once_with(
            "GET",
            "/repos/hasshya1530/repopilot/git/trees/tree123",
            params={"recursive": "1"},
        )

        await client.close()


@pytest.mark.asyncio
async def test_create_blob() -> None:
    response = httpx.Response(
        201,
        json={
            "sha": "blob123",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.create_blob(
            "hasshya1530",
            "repopilot",
            "print('hello')\n",
        )

        assert result["sha"] == "blob123"

        mock_client.request.assert_awaited_once_with(
            "POST",
            "/repos/hasshya1530/repopilot/git/blobs",
            json={
                "content": "print('hello')\n",
                "encoding": "utf-8",
            },
        )

        await client.close()


@pytest.mark.asyncio
async def test_create_tree() -> None:
    response = httpx.Response(
        201,
        json={
            "sha": "tree456",
        },
    )

    entries = [
        {
            "path": "src/example.py",
            "mode": "100644",
            "type": "blob",
            "sha": "blob123",
        },
        {
            "path": "old.py",
            "mode": "100644",
            "type": "blob",
        },
    ]

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.create_tree(
            "hasshya1530",
            "repopilot",
            base_tree="tree123",
            entries=entries,
        )

        assert result["sha"] == "tree456"

        mock_client.request.assert_awaited_once_with(
            "POST",
            "/repos/hasshya1530/repopilot/git/trees",
            json={
                "base_tree": "tree123",
                "tree": entries,
            },
        )

        await client.close()


@pytest.mark.asyncio
async def test_create_commit() -> None:
    response = httpx.Response(
        201,
        json={
            "sha": "commit456",
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.create_commit(
            "hasshya1530",
            "repopilot",
            message="feat: implement change",
            tree="tree456",
            parents=["commit123"],
        )

        assert result["sha"] == "commit456"

        mock_client.request.assert_awaited_once_with(
            "POST",
            "/repos/hasshya1530/repopilot/git/commits",
            json={
                "message": "feat: implement change",
                "tree": "tree456",
                "parents": ["commit123"],
            },
        )

        await client.close()


@pytest.mark.asyncio
async def test_update_git_ref() -> None:
    response = httpx.Response(
        200,
        json={
            "ref": "refs/heads/repopilot/test",
            "object": {
                "sha": "commit456",
            },
        },
    )

    with patch("tools.github.client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.request = AsyncMock(return_value=response)
        mock_client.aclose = AsyncMock()

        client = GitHubClient("test-token")

        result = await client.update_git_ref(
            "hasshya1530",
            "repopilot",
            "heads/repopilot/test",
            "commit456",
        )

        assert result["object"]["sha"] == "commit456"

        mock_client.request.assert_awaited_once_with(
            "PATCH",
            "/repos/hasshya1530/repopilot/git/refs/heads/repopilot/test",
            json={
                "sha": "commit456",
                "force": False,
            },
        )

        await client.close()
