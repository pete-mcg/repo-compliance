import httpx
import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.errors import GitHubError
from repo_compliance.infrastructure.github.client import GitHubClient
from repo_compliance.rules.deterministic.main_latest_commit_checks_passed import (
    RULE,
    check,
)
from repo_compliance.rules.registry import RULES
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"
SHA = "a" * 40
COMMIT_RESOURCE = f"/repos/{REPOSITORY}/commits/main"
CHECK_RUNS_RESOURCE = f"/repos/{REPOSITORY}/commits/{SHA}/check-runs"
STATUS_RESOURCE = f"/repos/{REPOSITORY}/commits/{SHA}/status"


def github_with_checks(
    runs: list[dict[str, object]], state: str = "pending", count: int = 0
) -> FakeGitHub:
    return FakeGitHub(
        json_responses={
            COMMIT_RESOURCE: {"sha": SHA},
            CHECK_RUNS_RESOURCE: {"check_runs": runs},
            STATUS_RESOURCE: {"state": state, "total_count": count},
        }
    )


@pytest.mark.parametrize("conclusion", ("success", "neutral", "skipped"))
def test_completed_passing_checks_use_latest_main_sha(conclusion: str) -> None:
    github = github_with_checks(
        [{"name": "CI", "status": "completed", "conclusion": conclusion}]
    )

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert SHA in result.message
    assert github.json_calls == [
        (COMMIT_RESOURCE, None, True),
        (CHECK_RUNS_RESOURCE, {"filter": "latest", "per_page": 100, "page": 1}, False),
        (STATUS_RESOURCE, None, False),
    ]


@pytest.mark.parametrize(
    ("status", "conclusion"),
    (
        ("completed", "failure"),
        ("completed", "cancelled"),
        ("completed", "timed_out"),
        ("completed", "action_required"),
        ("completed", "stale"),
        ("completed", None),
        ("completed", "unknown"),
        ("in_progress", None),
        ("queued", None),
        ("waiting", "success"),
    ),
)
def test_one_unsuccessful_check_fails(status: str, conclusion: str | None) -> None:
    github = github_with_checks(
        [
            {"name": "lint", "status": "completed", "conclusion": "success"},
            {"name": "tests", "status": status, "conclusion": conclusion},
        ],
        state="success",
        count=1,
    )

    result = check(RuleContext(REPOSITORY, github))

    assert not result.passed
    assert "tests" in result.message


@pytest.mark.parametrize("with_run", (True, False))
@pytest.mark.parametrize("state", ("success", "pending", "failure", "error"))
def test_commit_statuses_must_also_pass(state: str, with_run: bool) -> None:
    runs: list[dict[str, object]] = [
        {"name": "CI", "status": "completed", "conclusion": "success"}
    ]
    github = github_with_checks(runs if with_run else [], state=state, count=2)

    assert check(RuleContext(REPOSITORY, github)).passed == (state == "success")


def test_no_checks_passes() -> None:
    result = check(RuleContext(REPOSITORY, github_with_checks([])))

    assert result.passed
    assert "no checks" in result.message


def test_missing_main_commit_fails() -> None:
    github = FakeGitHub()

    assert not check(RuleContext(REPOSITORY, github)).passed
    assert github.json_calls == [(COMMIT_RESOURCE, None, True)]


@pytest.mark.parametrize(
    ("resource", "payload"),
    (
        (COMMIT_RESOURCE, {}),
        (CHECK_RUNS_RESOURCE, {}),
        (CHECK_RUNS_RESOURCE, {"check_runs": [{}]}),
        (STATUS_RESOURCE, {}),
    ),
)
def test_invalid_responses_raise_errors(resource: str, payload: object) -> None:
    github = github_with_checks([])
    github.json_responses[resource] = payload

    with pytest.raises(GitHubError, match="invalid data"):
        check(RuleContext(REPOSITORY, github))


def test_failed_check_on_second_page_is_not_missed() -> None:
    pages: list[int] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == COMMIT_RESOURCE:
            return httpx.Response(200, json={"sha": SHA})
        if request.url.path == STATUS_RESOURCE:
            return httpx.Response(200, json={"state": "pending", "total_count": 0})
        assert request.url.path == CHECK_RUNS_RESOURCE
        assert request.url.params["filter"] == "latest"
        page = int(request.url.params["page"])
        pages.append(page)
        run = {"name": "CI", "status": "completed", "conclusion": "success"}
        runs = [run] * 100 if page == 1 else [{**run, "conclusion": "failure"}]
        return httpx.Response(200, json={"check_runs": runs})

    with GitHubClient("test-token", transport=httpx.MockTransport(respond)) as github:
        result = check(RuleContext(REPOSITORY, github))

    assert not result.passed
    assert pages == [1, 2]


@pytest.mark.parametrize("status_code", (403, 500))
def test_api_errors_are_not_reported_as_failures(status_code: int) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"message": "unavailable"})

    with (
        GitHubClient("test-token", transport=httpx.MockTransport(respond)) as github,
        pytest.raises(GitHubError, match=f"HTTP {status_code}"),
    ):
        check(RuleContext(REPOSITORY, github))


def test_rule_is_enabled() -> None:
    assert RULE in RULES
