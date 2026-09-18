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
        if not token.strip():
            raise ValueError("GitHub token must not be empty.")

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
        params: dict[str, str] = {}

        if ref is not None:
            params["ref"] = ref

        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/contents/{path}",
            params=params,
        )

    async def get_branch(
        self,
        owner: str,
        name: str,
        branch: str,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/branches/{branch}",
        )

    async def create_branch(
        self,
        owner: str,
        name: str,
        branch: str,
        sha: str,
    ) -> dict[str, Any]:
        if not branch.strip():
            raise ValueError("Branch name must not be empty.")

        if not sha.strip():
            raise ValueError("Branch SHA must not be empty.")

        return await self._request(
            "POST",
            f"/repos/{owner}/{name}/git/refs",
            json={
                "ref": f"refs/heads/{branch}",
                "sha": sha,
            },
        )

    async def create_or_update_file(
        self,
        owner: str,
        name: str,
        path: str,
        content: str,
        *,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        import base64

        if not path.strip():
            raise ValueError("File path must not be empty.")

        if not message.strip():
            raise ValueError("Commit message must not be empty.")

        if not branch.strip():
            raise ValueError("Branch name must not be empty.")

        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(
                content.encode("utf-8")
            ).decode("ascii"),
            "branch": branch,
        }

        if sha is not None:
            payload["sha"] = sha

        return await self._request(
            "PUT",
            f"/repos/{owner}/{name}/contents/{path}",
            json=payload,
        )

    async def create_pull_request(
        self,
        owner: str,
        name: str,
        *,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = True,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("Pull request title must not be empty.")

        if not head.strip():
            raise ValueError(
                "Pull request head branch must not be empty."
            )

        if not base.strip():
            raise ValueError(
                "Pull request base branch must not be empty."
            )

        return await self._request(
            "POST",
            f"/repos/{owner}/{name}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            },
        )

    async def get_pull_request(
        self,
        owner: str,
        name: str,
        pull_number: int,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/pulls/{pull_number}",
        )

    async def get_git_ref(
        self,
        owner: str,
        name: str,
        ref: str,
    ) -> dict[str, Any]:
        if not ref.strip():
            raise ValueError("Git reference must not be empty.")

        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/git/ref/{ref}",
        )

    async def get_commit(
        self,
        owner: str,
        name: str,
        sha: str,
    ) -> dict[str, Any]:
        if not sha.strip():
            raise ValueError("Commit SHA must not be empty.")

        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/git/commits/{sha}",
        )

    async def get_tree(
        self,
        owner: str,
        name: str,
        tree_sha: str,
        *,
        recursive: bool = False,
    ) -> dict[str, Any]:
        if not tree_sha.strip():
            raise ValueError("Tree SHA must not be empty.")

        params: dict[str, str] = {}

        if recursive:
            params["recursive"] = "1"

        return await self._request(
            "GET",
            f"/repos/{owner}/{name}/git/trees/{tree_sha}",
            params=params,
        )

    async def create_blob(
        self,
        owner: str,
        name: str,
        content: str,
    ) -> dict[str, Any]:
        if not content:
            raise ValueError("Blob content must not be empty.")

        return await self._request(
            "POST",
            f"/repos/{owner}/{name}/git/blobs",
            json={
                "content": content,
                "encoding": "utf-8",
            },
        )

    async def create_tree(
        self,
        owner: str,
        name: str,
        *,
        base_tree: str,
        entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not base_tree.strip():
            raise ValueError("Base tree SHA must not be empty.")

        if not entries:
            raise ValueError("Tree must contain at least one entry.")

        return await self._request(
            "POST",
            f"/repos/{owner}/{name}/git/trees",
            json={
                "base_tree": base_tree,
                "tree": entries,
            },
        )

    async def create_commit(
        self,
        owner: str,
        name: str,
        *,
        message: str,
        tree: str,
        parents: list[str],
    ) -> dict[str, Any]:
        if not message.strip():
            raise ValueError("Commit message must not be empty.")

        if not tree.strip():
            raise ValueError("Tree SHA must not be empty.")

        if not parents:
            raise ValueError("Commit must have at least one parent.")

        return await self._request(
            "POST",
            f"/repos/{owner}/{name}/git/commits",
            json={
                "message": message,
                "tree": tree,
                "parents": parents,
            },
        )

    async def update_git_ref(
        self,
        owner: str,
        name: str,
        ref: str,
        sha: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        if not ref.strip():
            raise ValueError("Git reference must not be empty.")

        if not sha.strip():
            raise ValueError("Commit SHA must not be empty.")

        return await self._request(
            "PATCH",
            f"/repos/{owner}/{name}/git/refs/{ref}",
            json={
                "sha": sha,
                "force": force,
            },
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
                f"GitHub API request failed: "
                f"{response.status_code} {response.text}"
            )

        data = response.json()

        if not isinstance(data, dict):
            raise GitHubAPIError(
                "GitHub API returned an unexpected response format"
            )

        return data
