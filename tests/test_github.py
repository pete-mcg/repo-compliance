from pathlib import Path

import httpx
import pytest

from repo_compliance.errors import GitHubError
from repo_compliance.github import API_VERSION, DEFAULT_TIMEOUT_SECONDS, GitHubClient

REPOSITORY = "example/service"


def test_sends_authentication_version_and_timeout_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["X-GitHub-Api-Version"] == API_VERSION
        assert request.headers["Accept"] == "application/vnd.github+json"
        assert request.headers["User-Agent"] == "repo-compliance"
        timeout = request.extensions["timeout"]
        assert isinstance(timeout, dict)
        assert timeout["read"] == DEFAULT_TIMEOUT_SECONDS
        return httpx.Response(200, json={"name": "main"})

    with GitHubClient("test-token", transport=httpx.MockTransport(handler)) as client:
        client.ensure_main_branch(REPOSITORY)


def test_reads_rule_and_classic_protection_responses() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/rules/branches/main"):
            assert request.url.params["per_page"] == "100"
            return httpx.Response(200, json=[{"type": "deletion"}, {"type": "update"}])
        return httpx.Response(200, json={"allow_deletions": {"enabled": False}})

    with GitHubClient("token", transport=httpx.MockTransport(handler)) as client:
        assert client.active_main_rule_types(REPOSITORY) == frozenset(
            {"deletion", "update"}
        )
        assert client.classic_allow_deletions(REPOSITORY) is False


def test_classic_protection_404_means_unprotected() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(404))

    with GitHubClient("token", transport=transport) as client:
        assert client.classic_allow_deletions(REPOSITORY) is None


def test_content_404_means_missing_file() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(404))

    with GitHubClient("token", transport=transport) as client:
        assert not client.file_exists(REPOSITORY, ".github/CODEOWNERS")


def test_content_requires_exact_file_response_and_main_ref() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["ref"] == "main"
        requested_paths.append(request.url.path)
        response_path = ".github/CODEOWNERS"
        response_type = "file" if len(requested_paths) == 1 else "dir"
        return httpx.Response(200, json={"path": response_path, "type": response_type})

    with GitHubClient("token", transport=httpx.MockTransport(handler)) as client:
        assert client.file_exists(REPOSITORY, ".github/CODEOWNERS")
        assert not client.file_exists(REPOSITORY, ".github/CODEOWNERS")

    assert requested_paths == [
        "/repos/example/service/contents/.github/CODEOWNERS",
        "/repos/example/service/contents/.github/CODEOWNERS",
    ]


@pytest.mark.parametrize(
    ("payload", "expected"),
    (([], False), ([{"number": 42}], True)),
)
def test_dependabot_critical_alert_filter(payload: object, expected: bool) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["state"] == "open"
        assert request.url.params["severity"] == "critical"
        assert request.url.params["per_page"] == "1"
        return httpx.Response(200, json=payload)

    with GitHubClient("token", transport=httpx.MockTransport(handler)) as client:
        assert client.has_critical_dependabot_alerts(REPOSITORY) is expected


def test_archive_download_follows_redirect_and_streams_file(tmp_path: Path) -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/zipball/main"):
            return httpx.Response(302, headers={"Location": "/archive.zip"})
        return httpx.Response(200, content=b"zip-content")

    destination = tmp_path / "repository.zip"
    with GitHubClient("token", transport=httpx.MockTransport(handler)) as client:
        client.download_main_archive(REPOSITORY, destination)

    assert destination.read_bytes() == b"zip-content"
    assert requested_paths == [
        "/repos/example/service/zipball/main",
        "/archive.zip",
    ]


def test_timeout_is_wrapped_as_github_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with (
        GitHubClient("token", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(GitHubError, match="ReadTimeout"),
    ):
        client.ensure_main_branch(REPOSITORY)


def test_http_error_is_wrapped_without_response_body() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(500, text="sensitive response")
    )

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="HTTP 500") as captured,
    ):
        client.ensure_main_branch(REPOSITORY)

    assert "sensitive response" not in str(captured.value)


@pytest.mark.parametrize(
    ("method", "payload"),
    (
        ("branch", {}),
        ("rules", [{}]),
        ("protection", {"allow_deletions": {}}),
        ("content", {"path": ".github/CODEOWNERS"}),
        ("alerts", [{}]),
    ),
)
def test_invalid_api_responses_are_wrapped(method: str, payload: object) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="invalid data"),
    ):
        call_client_method(client, method)


def test_wrong_preflight_branch_is_an_error() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"name": "develop"})
    )

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="wrong branch"),
    ):
        client.ensure_main_branch(REPOSITORY)


def test_archive_output_failure_is_wrapped(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=b"archive")
    )

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="FileNotFoundError"),
    ):
        client.download_main_archive(REPOSITORY, tmp_path / "missing" / "file.zip")


def call_client_method(client: GitHubClient, method: str) -> None:
    if method == "branch":
        client.ensure_main_branch(REPOSITORY)
    elif method == "rules":
        client.active_main_rule_types(REPOSITORY)
    elif method == "protection":
        client.classic_allow_deletions(REPOSITORY)
    elif method == "content":
        client.file_exists(REPOSITORY, ".github/CODEOWNERS")
    else:
        client.has_critical_dependabot_alerts(REPOSITORY)
