from repo_compliance.domain import RuleContext
from repo_compliance.rules.deterministic.deploy_workflow_present import (
    REQUIRED_PATH,
    check,
)
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"


def test_passes_when_exact_file_exists_on_main() -> None:
    github = FakeGitHub(files={REQUIRED_PATH})

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed


def test_fails_when_file_is_missing() -> None:
    result = check(RuleContext(REPOSITORY, FakeGitHub()))

    assert not result.passed
