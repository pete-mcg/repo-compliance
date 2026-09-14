"""Small synchronous client for the GitHub REST endpoints used by rules."""

from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Literal, Self, overload

import httpx
from pydantic import TypeAdapter, ValidationError

from repo_compliance.errors import GitHubError
from repo_compliance.github_models import (
    GitHubBranch,
    GitHubBranchProtection,
    GitHubContent,
    GitHubDependabotAlert,
    GitHubRule,
)

API_VERSION = "2026-03-10"
DEFAULT_TIMEOUT_SECONDS = 30.0

BRANCH_ADAPTER = TypeAdapter(GitHubBranch)
RULES_ADAPTER = TypeAdapter(tuple[GitHubRule, ...])
PROTECTION_ADAPTER = TypeAdapter(GitHubBranchProtection)
CONTENT_ADAPTER = TypeAdapter(GitHubContent)
ALERTS_ADAPTER = TypeAdapter(tuple[GitHubDependabotAlert, ...])


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

    def get_main_branch(self, repository: str) -> str:
        """Return the accessible main branch name."""
        resource = f"/repos/{repository}/branches/main"
        response = self._get(resource)
        branch = _get_valid_response(response, BRANCH_ADAPTER, resource)
        if branch.name != "main":
            raise GitHubError(f"GitHub returned the wrong branch for '{repository}'.")
        return branch.name

    def get_active_main_rule_types(self, repository: str) -> frozenset[str]:
        """Return active ruleset rule types applying to main."""
        resource = f"/repos/{repository}/rules/branches/main"
        response = self._get(resource, params={"per_page": 100})
        rules = _get_valid_response(response, RULES_ADAPTER, resource)
        return frozenset(rule.type for rule in rules)

    def get_classic_deletion_setting(self, repository: str) -> bool | None:
        """Return classic deletion setting, or None when main is unprotected."""
        resource = f"/repos/{repository}/branches/main/protection"
        response = self._get(resource, missing_ok=True)
        if response is None:
            return None

        protection = _get_valid_response(response, PROTECTION_ADAPTER, resource)
        return protection.allow_deletions.enabled

    def has_file(self, repository: str, path: str) -> bool:
        """Return whether an exact file exists on main."""
        resource = f"/repos/{repository}/contents/{path}"
        response = self._get(resource, params={"ref": "main"}, missing_ok=True)
        if response is None:
            return False

        content = _get_valid_response(response, CONTENT_ADAPTER, resource)
        return content.path == path and content.type == "file"

    def has_critical_dependabot_alerts(self, repository: str) -> bool:
        """Return whether any open Critical Dependabot alert exists."""
        resource = f"/repos/{repository}/dependabot/alerts"
        response = self._get(
            resource,
            params={"state": "open", "severity": "critical", "per_page": 1},
        )
        alerts = _get_valid_response(response, ALERTS_ADAPTER, resource)
        return bool(alerts)

    def get_main_archive(self, repository: str, destination: Path) -> Path:
        """Stream a main branch ZIP archive to destination and return its path."""
        resource = f"/repos/{repository}/zipball/main"
        try:
            with self._client.stream("GET", resource) as response:
                response.raise_for_status()
                _set_archive_content(destination, response.iter_bytes())
        except (httpx.HTTPError, OSError) as error:
            raise _compose_request_error(resource, error) from error
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
            raise _compose_request_error(resource, error) from error

        if missing_ok and response.status_code == httpx.codes.NOT_FOUND:
            return None

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise _compose_request_error(resource, error) from error
        return response


def _set_archive_content(destination: Path, chunks: Iterator[bytes]) -> None:
    with destination.open("wb") as archive_file:
        for chunk in chunks:
            archive_file.write(chunk)


def _get_valid_response[T](
    response: httpx.Response,
    adapter: TypeAdapter[T],
    resource: str,
) -> T:
    try:
        return adapter.validate_json(response.content)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error


def _compose_request_error(
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
