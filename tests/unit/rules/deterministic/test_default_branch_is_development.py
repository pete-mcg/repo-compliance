import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.errors import GitHubError
from repo_compliance.rules.deterministic.default_branch_is_development import (
    RULE,
    check,
)
from repo_compliance.rules.registry import RULES
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"
RESOURCE = "/repos/example/service"


@pytest.mark.parametrize(
    ("default_branch", "passed"),
    [
        ("development", True),
        ("main", False),
        ("develop", False),
        ("Development", False),
    ],
)
def test_checks_exact_default_branch(default_branch: str, passed: bool) -> None:
    github = FakeGitHub(json_responses={RESOURCE: {"default_branch": default_branch}})

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed is passed
    assert default_branch in result.message
    assert "development" in result.message
    assert github.json_calls == [(RESOURCE, None, False)]
    assert RULE in RULES


@pytest.mark.parametrize(
    "payload", [None, {}, {"default_branch": None}, {"default_branch": 42}]
)
def test_rejects_invalid_github_response(payload: object) -> None:
    github = FakeGitHub(json_responses={RESOURCE: payload})

    with pytest.raises(GitHubError, match="invalid data"):
        check(RuleContext(REPOSITORY, github))
