import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.errors import GitHubError
from repo_compliance.rules.deterministic.main_branch_deletion_protected import (
    check,
)
from tests.fakes import FakeGitHub

REPOSITORY = "example/service"
RULESET_RESOURCE = "/repos/example/service/rules/branches/main"
CLASSIC_RESOURCE = "/repos/example/service/branches/main/protection"


def test_ruleset_deletion_rule_passes_without_classic_request() -> None:
    github = FakeGitHub(json_responses={RULESET_RESOURCE: [{"type": "deletion"}]})

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert github.json_calls == [(RULESET_RESOURCE, {"per_page": 100}, False)]


def test_classic_protection_with_deletions_disabled_passes() -> None:
    github = FakeGitHub(
        json_responses={
            RULESET_RESOURCE: [],
            CLASSIC_RESOURCE: {"allow_deletions": {"enabled": False}},
        }
    )

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert "Classic" in result.message
    assert github.json_calls[-1] == (CLASSIC_RESOURCE, None, True)


@pytest.mark.parametrize("allow_deletions", (True, None))
def test_missing_deletion_protection_fails(allow_deletions: bool | None) -> None:
    protection = (
        None
        if allow_deletions is None
        else {"allow_deletions": {"enabled": allow_deletions}}
    )
    github = FakeGitHub(
        json_responses={RULESET_RESOURCE: [], CLASSIC_RESOURCE: protection}
    )

    result = check(RuleContext(REPOSITORY, github))

    assert not result.passed


@pytest.mark.parametrize(
    "responses",
    (
        {RULESET_RESOURCE: [{}]},
        {
            RULESET_RESOURCE: [],
            CLASSIC_RESOURCE: {"allow_deletions": {}},
        },
    ),
)
def test_rejects_invalid_github_response(
    responses: dict[str, object | None],
) -> None:
    with pytest.raises(GitHubError, match="invalid data"):
        check(RuleContext(REPOSITORY, FakeGitHub(json_responses=responses)))
