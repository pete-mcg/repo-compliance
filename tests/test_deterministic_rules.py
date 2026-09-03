import pytest

from repo_compliance.domain import RuleCheck, RuleContext
from repo_compliance.rules.deterministic.codeowners_present import (
    REQUIRED_PATH as CODEOWNERS_PATH,
)
from repo_compliance.rules.deterministic.codeowners_present import (
    check as check_codeowners,
)
from repo_compliance.rules.deterministic.deploy_workflow_present import (
    REQUIRED_PATH as DEPLOY_PATH,
)
from repo_compliance.rules.deterministic.deploy_workflow_present import (
    check as check_deploy,
)
from repo_compliance.rules.deterministic.main_branch_deletion_protected import (
    check as check_deletion,
)
from repo_compliance.rules.deterministic.no_critical_dependabot_alerts import (
    check as check_dependabot,
)

from .fakes import FakeGitHub

REPOSITORY = "example/service"


def context(github: FakeGitHub) -> RuleContext:
    return RuleContext(REPOSITORY, github)


def test_ruleset_deletion_rule_passes_without_classic_request() -> None:
    github = FakeGitHub(rule_types=frozenset({"deletion"}), allow_deletions=True)

    result = check_deletion(context(github))

    assert result.passed
    assert github.classic_calls == 0


def test_classic_protection_with_deletions_disabled_passes() -> None:
    github = FakeGitHub(allow_deletions=False)

    result = check_deletion(context(github))

    assert result.passed
    assert "Classic" in result.message


@pytest.mark.parametrize("allow_deletions", (True, None))
def test_missing_deletion_protection_fails(allow_deletions: bool | None) -> None:
    result = check_deletion(context(FakeGitHub(allow_deletions=allow_deletions)))

    assert not result.passed


@pytest.mark.parametrize(
    ("check", "path"),
    ((check_codeowners, CODEOWNERS_PATH), (check_deploy, DEPLOY_PATH)),
    ids=("codeowners", "deploy"),
)
def test_required_file_rules_pass_when_exact_file_exists(
    check: RuleCheck,
    path: str,
) -> None:
    github = FakeGitHub(files={path})

    result = check(context(github))

    assert result.passed


@pytest.mark.parametrize(
    "check",
    (check_codeowners, check_deploy),
    ids=("codeowners", "deploy"),
)
def test_required_file_rules_fail_when_file_is_missing(check: RuleCheck) -> None:
    result = check(context(FakeGitHub()))

    assert not result.passed


@pytest.mark.parametrize("has_alerts", (False, True))
def test_dependabot_rule_requires_empty_critical_alerts(has_alerts: bool) -> None:
    result = check_dependabot(context(FakeGitHub(critical_alerts=has_alerts)))

    assert result.passed is not has_alerts
