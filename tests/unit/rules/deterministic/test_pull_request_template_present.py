import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.rules.deterministic.pull_request_template_present import (
    RULE,
    check,
)
from repo_compliance.rules.registry import RULES
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"


@pytest.mark.parametrize(
    ("files", "passed"),
    [
        ({"github/pull_request_template.md"}, True),
        (set(), False),
        ({"pull_request_template.md", ".github/pull_request_template.md"}, False),
    ],
)
def test_checks_exact_file_on_main(files: set[str], passed: bool) -> None:
    github = FakeGitHub(files=files)

    result = check(RuleContext(REPOSITORY, github))

    assert result.passed is passed
    assert github.file_calls == [(REPOSITORY, "github/pull_request_template.md")]
    assert RULE in RULES
