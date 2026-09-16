import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.errors import GitHubError
from repo_compliance.rules.deterministic.no_critical_dependabot_alerts import (
    check,
)
from tests.fakes import FakeGitHub

REPOSITORY = "example/service"


@pytest.mark.parametrize(
    ("payload", "expected"),
    (([], True), ([{"number": 42}], False)),
)
def test_requires_empty_critical_alerts(payload: object, expected: bool) -> None:
    github = FakeGitHub(
        json_responses={"/repos/example/service/dependabot/alerts": payload}
    )

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed is expected
    assert github.json_calls == [
        (
            "/repos/example/service/dependabot/alerts",
            {"state": "open", "severity": "critical", "per_page": 1},
            False,
        )
    ]


def test_rejects_invalid_dependabot_response() -> None:
    github = FakeGitHub(
        json_responses={"/repos/example/service/dependabot/alerts": [{}]}
    )

    with pytest.raises(GitHubError, match="invalid data"):
        check(RuleContext(REPOSITORY, github))
