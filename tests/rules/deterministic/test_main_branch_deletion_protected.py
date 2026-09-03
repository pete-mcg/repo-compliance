import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.rules.deterministic.main_branch_deletion_protected import check
from tests.fakes import FakeGitHub

REPOSITORY = "example/service"


def test_ruleset_deletion_rule_passes_without_classic_request() -> None:
    github = FakeGitHub(rule_types=frozenset({"deletion"}), allow_deletions=True)

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert github.classic_calls == 0


def test_classic_protection_with_deletions_disabled_passes() -> None:
    github = FakeGitHub(allow_deletions=False)

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed
    assert "Classic" in result.message


@pytest.mark.parametrize("allow_deletions", (True, None))
def test_missing_deletion_protection_fails(allow_deletions: bool | None) -> None:
    github = FakeGitHub(allow_deletions=allow_deletions)

    result = check(RuleContext(REPOSITORY, github))

    assert not result.passed
