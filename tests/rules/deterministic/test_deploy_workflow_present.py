from repo_compliance.domain import RuleContext
from repo_compliance.rules.deterministic.deploy_workflow_present import (
    REQUIRED_PATH,
    get_evaluation,
)
from tests.fakes import FakeGitHub

REPOSITORY = "example/service"


def test_passes_when_exact_file_exists() -> None:
    github = FakeGitHub(files={REQUIRED_PATH})

    result = get_evaluation(RuleContext(REPOSITORY, github))

    assert result.passed


def test_fails_when_file_is_missing() -> None:
    result = get_evaluation(RuleContext(REPOSITORY, FakeGitHub()))

    assert not result.passed
