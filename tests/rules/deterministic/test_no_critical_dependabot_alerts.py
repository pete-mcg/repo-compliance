import pytest

from repo_compliance.domain import RuleContext
from repo_compliance.rules.deterministic.no_critical_dependabot_alerts import (
    get_evaluation,
)
from tests.fakes import FakeGitHub

REPOSITORY = "example/service"


@pytest.mark.parametrize("has_alerts", (False, True))
def test_requires_empty_critical_alerts(has_alerts: bool) -> None:
    github = FakeGitHub(critical_alerts=has_alerts)

    result = get_evaluation(RuleContext(REPOSITORY, github))

    assert result.passed is not has_alerts
