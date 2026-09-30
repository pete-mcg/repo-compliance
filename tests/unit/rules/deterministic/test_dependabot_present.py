import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.rules.deterministic.dependabot_present import RULE, check
from repo_compliance.rules.registry import RULES
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"


@pytest.mark.parametrize(
    ("files", "passed"),
    [
        ({".github/dependabot.yml"}, True),
        (set(), False),
        ({"dependabot.yml", ".github/dependabot.yaml"}, False),
    ],
)
def test_checks_exact_file_on_main(files: set[str], passed: bool) -> None:
    github = FakeGitHub(files=files)

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed is passed
    assert github.file_calls == [(REPOSITORY, ".github/dependabot.yml")]
    assert RULE in RULES
