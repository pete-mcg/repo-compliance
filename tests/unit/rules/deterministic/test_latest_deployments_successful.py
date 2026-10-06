import httpx
import pytest

from repo_compliance.domain import Confidence, RuleCategory, RuleContext
from repo_compliance.errors import GitHubError
from repo_compliance.infrastructure.github.client import GitHubClient
from repo_compliance.rules.deterministic.latest_deployments_successful import (
    RULE,
    check,
)
from repo_compliance.rules.registry import RULES
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"
DEPLOYMENTS_RESOURCE = f"/repos/{REPOSITORY}/deployments"
STATUSES_RESOURCE = f"{DEPLOYMENTS_RESOURCE}/1/statuses"
EARLIER = "2026-10-01T10:00:00Z"
LATER = "2026-10-02T10:00:00Z"


def deployment(
    deployment_id: int = 1, environment: str = "production", created_at: str = EARLIER
) -> dict[str, object]:
    return {"id": deployment_id, "environment": environment, "created_at": created_at}


def status(
    state: str = "success", status_id: int = 1, created_at: str = EARLIER
) -> dict[str, object]:
    return {"id": status_id, "state": state, "created_at": created_at}


@pytest.mark.parametrize(
    "state",
    (
        "success",
        "failure",
        "error",
        "pending",
        "queued",
        "in_progress",
        "inactive",
        "unknown",
    ),
)
def test_only_success_passes(state: str) -> None:
    github = FakeGitHub(
        json_responses={
            DEPLOYMENTS_RESOURCE: [deployment()],
            STATUSES_RESOURCE: [status(state)],
        }
    )

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed == (state == "success")
    assert result.message == f"Latest deployments: production: {state}."


@pytest.mark.parametrize("state", ("success", "failure"))
def test_reports_every_environment_even_after_a_failure(state: str) -> None:
    github = FakeGitHub(
        json_responses={
            DEPLOYMENTS_RESOURCE: [deployment(2, "staging"), deployment()],
            STATUSES_RESOURCE: [status(state)],
            f"{DEPLOYMENTS_RESOURCE}/2/statuses": [status()],
        }
    )

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed == (state == "success")
    assert (
        result.message == f"Latest deployments: production: {state}; staging: success."
    )


@pytest.mark.parametrize("later_time", (EARLIER, LATER))
def test_newest_deployment_and_status_use_creation_time_then_id(
    later_time: str,
) -> None:
    github = FakeGitHub(
        json_responses={
            DEPLOYMENTS_RESOURCE: [
                deployment(2, created_at=later_time),
                {**deployment(), "updated_at": "2026-10-03T10:00:00Z"},
            ],
            STATUSES_RESOURCE: [status()],
            f"{DEPLOYMENTS_RESOURCE}/2/statuses": [
                status(),
                status("pending", 2, later_time),
            ],
        }
    )

    result = check(RuleContext(REPOSITORY, github))

    assert not result.passed
    assert result.message == "Latest deployments: production: pending."
    assert STATUSES_RESOURCE not in [call[0] for call in github.json_calls]


def test_creation_time_takes_precedence_over_id_and_response_order() -> None:
    github = FakeGitHub(
        json_responses={
            DEPLOYMENTS_RESOURCE: [deployment(2), deployment(created_at=LATER)],
            STATUSES_RESOURCE: [status("failure", 2), status(created_at=LATER)],
        }
    )

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert result.message == "Latest deployments: production: success."


def test_no_deployments_passes_without_status_requests() -> None:
    github = FakeGitHub(json_responses={DEPLOYMENTS_RESOURCE: []})

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert result.message == "No deployed environments to check."
    assert github.json_calls == [
        (DEPLOYMENTS_RESOURCE, {"per_page": 100, "page": 1}, False)
    ]


def test_deployment_without_status_fails() -> None:
    github = FakeGitHub(
        json_responses={DEPLOYMENTS_RESOURCE: [deployment()], STATUSES_RESOURCE: []}
    )

    result = check(RuleContext(REPOSITORY, github))

    assert not result.passed
    assert result.message == "Latest deployments: production: no status."


@pytest.mark.parametrize(
    ("resource", "payload"),
    (
        (DEPLOYMENTS_RESOURCE, None),
        (DEPLOYMENTS_RESOURCE, {}),
        (DEPLOYMENTS_RESOURCE, [{}]),
        (DEPLOYMENTS_RESOURCE, [deployment(created_at="invalid")]),
        (STATUSES_RESOURCE, None),
        (STATUSES_RESOURCE, {}),
        (STATUSES_RESOURCE, [{}]),
        (STATUSES_RESOURCE, [{**status(), "state": None}]),
    ),
)
def test_invalid_responses_raise_errors(resource: str, payload: object) -> None:
    github = FakeGitHub(
        json_responses={
            DEPLOYMENTS_RESOURCE: [deployment()],
            STATUSES_RESOURCE: [status()],
        }
    )
    github.json_responses[resource] = payload

    with pytest.raises(GitHubError, match="invalid data"):
        check(RuleContext(REPOSITORY, github))


@pytest.mark.parametrize(
    "paginated_resource", (DEPLOYMENTS_RESOURCE, STATUSES_RESOURCE)
)
def test_second_pages_are_checked(paginated_resource: str) -> None:
    pages: list[int] = []
    responses = {
        DEPLOYMENTS_RESOURCE: [[deployment()]],
        STATUSES_RESOURCE: [[status()]],
        f"{DEPLOYMENTS_RESOURCE}/101/statuses": [[status("failure")]],
        f"{DEPLOYMENTS_RESOURCE}/102/statuses": [[status()]],
    }
    if paginated_resource == DEPLOYMENTS_RESOURCE:
        responses[DEPLOYMENTS_RESOURCE] = [
            [deployment(number) for number in range(1, 101)],
            [deployment(101, created_at=LATER), deployment(102, "staging", LATER)],
        ]
    else:
        responses[STATUSES_RESOURCE] = [
            [status(status_id=number) for number in range(1, 101)],
            [status("failure", 101, LATER)],
        ]

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        page = int(request.url.params["page"])
        if request.url.path == paginated_resource:
            pages.append(page)
        return httpx.Response(200, json=responses[request.url.path][page - 1])

    with GitHubClient("test-token", transport=httpx.MockTransport(respond)) as github:
        result = check(RuleContext(REPOSITORY, github))

    assert not result.passed
    assert "failure" in result.message
    assert pages == [1, 2]


@pytest.mark.parametrize("resource", (DEPLOYMENTS_RESOURCE, STATUSES_RESOURCE))
@pytest.mark.parametrize("status_code", (403, 404, 500))
def test_api_errors_are_not_reported_as_failures(
    resource: str, status_code: int
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == resource:
            return httpx.Response(status_code, json={"message": "unavailable"})
        return httpx.Response(200, json=[deployment()])

    with (
        GitHubClient("test-token", transport=httpx.MockTransport(respond)) as github,
        pytest.raises(GitHubError, match=f"HTTP {status_code}"),
    ):
        check(RuleContext(REPOSITORY, github))


def test_rule_is_enabled_and_deterministic() -> None:
    assert RULE in RULES
    assert RULE.category is RuleCategory.DETERMINISTIC
    assert RULE.confidence is Confidence.HIGH
    assert not RULE.requires_source_snapshot
