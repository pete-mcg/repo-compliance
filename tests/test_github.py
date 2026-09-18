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
        return httpx.Response(200, json={"id": 42})

    with GitHubClient("test-token", transport=httpx.MockTransport(handler)) as client:
        client.ensure_accessible_respository(REPOSITORY)


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


def test_get_json_sends_parameters_and_decodes_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["state"] == "open"
        return httpx.Response(200, json={"answer": 42})

    with GitHubClient("token", transport=httpx.MockTransport(handler)) as client:
        assert client.get_json("/example", params={"state": "open"}) == {"answer": 42}


def test_get_json_wraps_invalid_json() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=b"not-json")
    )

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="invalid JSON"),
    ):
        client.get_json("/example")


def test_get_json_can_accept_a_missing_resource() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(404))

    with GitHubClient("token", transport=transport) as client:
        assert client.get_json("/example", missing_ok=True) is None


def test_source_snapshot_download_follows_redirect_and_streams_file(
    tmp_path: Path,
) -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/zipball/main"):
            return httpx.Response(302, headers={"Location": "/source.zip"})
        return httpx.Response(200, content=b"zip-content")

    destination = tmp_path / "repository.zip"
    with GitHubClient("token", transport=httpx.MockTransport(handler)) as client:
        assert (
            client.download_source_snapshot_from_main(REPOSITORY, destination)
            == destination
        )

    assert destination.read_bytes() == b"zip-content"
    assert requested_paths == [
        "/repos/example/service/zipball/main",
        "/source.zip",
    ]


def test_timeout_is_wrapped_as_github_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with (
        GitHubClient("token", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(GitHubError, match="ReadTimeout"),
    ):
        client.ensure_accessible_respository(REPOSITORY)


def test_http_error_is_wrapped_without_response_body() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(500, text="sensitive response")
    )

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="HTTP 500") as captured,
    ):
        client.ensure_accessible_respository(REPOSITORY)

    assert "sensitive response" not in str(captured.value)


@pytest.mark.parametrize(
    ("method", "payload"),
    (
        ("repository", {}),
        ("content", {"path": ".github/CODEOWNERS"}),
    ),
)
def test_invalid_api_responses_are_wrapped(method: str, payload: object) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="invalid data"),
    ):
        call_client_method(client, method)


def test_preflight_accepts_a_repository_regardless_of_default_branch() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"id": 42, "default_branch": "develop"}
        )
    )

    with GitHubClient("token", transport=transport) as client:
        client.ensure_accessible_respository(REPOSITORY)


def test_source_snapshot_output_failure_is_wrapped(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=b"source snapshot")
    )

    with (
        GitHubClient("token", transport=transport) as client,
        pytest.raises(GitHubError, match="FileNotFoundError"),
    ):
        client.download_source_snapshot_from_main(
            REPOSITORY, tmp_path / "missing" / "file.zip"
        )


def call_client_method(client: GitHubClient, method: str) -> None:
    if method == "repository":
        client.ensure_accessible_respository(REPOSITORY)
    else:
        client.file_exists(REPOSITORY, ".github/CODEOWNERS")
