"""Small synchronous client for the GitHub REST endpoints used by rules."""

from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Literal, Self, overload

import httpx
from pydantic import TypeAdapter, ValidationError

from repo_compliance.errors import GitHubError
from repo_compliance.github_models import (
    GitHubContent,
    GitHubRepository,
)

API_VERSION = "2026-03-10"
DEFAULT_TIMEOUT_SECONDS = 30.0

REPOSITORY_ADAPTER = TypeAdapter(GitHubRepository)
CONTENT_ADAPTER = TypeAdapter(GitHubContent)


class GitHubClient:
    """Typed, synchronous access to the required GitHub REST endpoints."""

    def __init__(
        self,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        base_url: str = "https://api.github.com",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Create a client using a token supplied by the caller."""
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "repo-compliance",
                "X-GitHub-Api-Version": API_VERSION,
            },
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> Self:
        """Return this client for context-manager use."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close network resources when leaving a context manager."""
        self._client.close()

    def ensure_accessible_respository(self, repository: str) -> None:
        """Ensure the repository is accessible and has valid API data."""
        resource = f"/repos/{repository}"
        response = self._get(resource)
        _validate(response, REPOSITORY_ADAPTER, resource)

    def file_exists(self, repository: str, path: str) -> bool:
        """Return whether an exact file exists on main."""
        resource = f"/repos/{repository}/contents/{path}"
        response = self._get(resource, params={"ref": "main"}, missing_ok=True)
        if response is None:
            return False

        content = _validate(response, CONTENT_ADAPTER, resource)
        return content.path == path and content.type == "file"

    def get_json(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: bool = False,
    ) -> object | None:
        """Return decoded JSON, optionally returning None when it is missing."""
        response = self._get(resource, params=params, missing_ok=missing_ok)
        if response is None:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise GitHubError(
                f"GitHub returned invalid JSON for '{resource}'."
            ) from error

    def download_archive_from_main(self, repository: str, destination: Path) -> Path:
        """Stream a main branch ZIP archive to destination and return its path."""
        resource = f"/repos/{repository}/zipball/main"
        try:
            with self._client.stream("GET", resource) as response:
                response.raise_for_status()
                _write_chunks(destination, response.iter_bytes())
        except (httpx.HTTPError, OSError) as error:
            raise _request_error(resource, error) from error
        return destination

    @overload
    def _get(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: Literal[False] = False,
    ) -> httpx.Response: ...

    @overload
    def _get(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: Literal[True],
    ) -> httpx.Response | None: ...

    def _get(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: bool = False,
    ) -> httpx.Response | None:
        try:
            response = self._client.get(resource, params=params)
        except httpx.RequestError as error:
            raise _request_error(resource, error) from error

        if missing_ok and response.status_code == httpx.codes.NOT_FOUND:
            return None

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise _request_error(resource, error) from error
        return response


def _write_chunks(destination: Path, chunks: Iterator[bytes]) -> None:
    with destination.open("wb") as archive_file:
        for chunk in chunks:
            archive_file.write(chunk)


def _validate[T](
    response: httpx.Response,
    adapter: TypeAdapter[T],
    resource: str,
) -> T:
    try:
        return adapter.validate_json(response.content)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error


def _request_error(
    resource: str,
    error: httpx.HTTPError | OSError,
) -> GitHubError:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return GitHubError(
            f"GitHub request for '{resource}' failed with HTTP {status}."
        )
    return GitHubError(
        f"GitHub request for '{resource}' failed ({type(error).__name__})."
    )
