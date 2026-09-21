from pathlib import Path

import pytest
from tests.unit.fakes import FakeAgentEvaluator, FakeGitHub

from repo_compliance.domain import (
    Confidence,
    Evidence,
    RuleCategory,
    RuleContext,
    RuleEvaluation,
)
from repo_compliance.errors import AgentError
from repo_compliance.rules.agentic.ci_workflow_on_pull_requests import (
    RULE,
    check,
    load_prompt,
)
from repo_compliance.rules.registry import RULES


@pytest.mark.parametrize("passed", [True, False])
def test_rule_loads_prompt_outside_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, passed: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    snapshot = tmp_path / "source.zip"
    snapshot.touch()
    evaluation = RuleEvaluation(passed, "Judgment", (Evidence("ci.yml", 1, "trigger"),))
    evaluator = FakeAgentEvaluator(evaluation)
    context = RuleContext("example/service", FakeGitHub(), snapshot, evaluator)

    assert check(context) == evaluation
    assert evaluator.calls == [(snapshot, load_prompt())]
    assert RULE in RULES
    assert RULE.category is RuleCategory.AGENTIC
    assert RULE.confidence is Confidence.MEDIUM
    assert RULE.requires_source_snapshot


def test_missing_dependencies_are_clear(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires a source snapshot"):
        check(RuleContext("example/service", FakeGitHub()))
    with pytest.raises(AgentError, match="No agent evaluator"):
        check(RuleContext("example/service", FakeGitHub(), tmp_path / "source.zip"))
