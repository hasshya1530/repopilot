from typing import Any

import httpx


class GitHubAPIError(Exception):
    """Raised when the GitHub API returns an unsuccessful response."""


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_authenticated_user(self) -> dict[str, Any]:
        return await self._request("GET", "/user")

    async def get_repository(
        self,
        owner: str,
        name: str,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/repos/{owner}/{name}",
        )

    async def get_issue(
        self,
        owner: str,
        name: str,
        issue_number: int,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/issues/{issue_number}",
        )

    async def get_file(
        self,
        owner: str,
        name: str,
        path: str,
        *,
        ref: str | None = None,
    ) -> dict[str, Any]:
        params = {}

        if ref is not None:
            params["ref"] = ref

        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/contents/{path}",
            params=params,
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = await self._client.request(
            method,
            path,
            **kwargs,
        )

        if response.is_error:
            raise GitHubAPIError(
                f"GitHub API request failed: {response.status_code} {response.text}"
            )

        data = response.json()

        if not isinstance(data, dict):
            raise GitHubAPIError("GitHub API returned an unexpected response format")

        return data
