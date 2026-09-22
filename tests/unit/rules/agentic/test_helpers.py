from pathlib import Path

import pytest
from tests.unit.fakes import FakeAgentEvaluator, FakeGitHub

from repo_compliance.domain import RuleContext, RuleEvaluation
from repo_compliance.errors import AgentError
from repo_compliance.rules.agentic.helpers import (
    evaluate_agentic_rule,
    load_rule_prompt,
    rule_prompt_filename,
)


def test_rule_prompt_filename() -> None:
    assert (
        rule_prompt_filename("ci-workflow-on-pull-requests")
        == "ci_workflow_on_pull_requests.md"
    )


def test_load_rule_prompt_outside_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    prompt = load_rule_prompt("ci_workflow_on_pull_requests.md")

    assert prompt.strip()


def test_evaluate_agentic_rule(tmp_path: Path) -> None:
    snapshot = tmp_path / "source.zip"
    snapshot.touch()
    evaluation = RuleEvaluation(True, "Judgment")
    evaluator = FakeAgentEvaluator(evaluation)
    context = RuleContext("example/service", FakeGitHub(), snapshot, evaluator)

    result = evaluate_agentic_rule(context, "ci_workflow_on_pull_requests.md")

    assert result == evaluation
    assert evaluator.calls == [
        (snapshot, load_rule_prompt("ci_workflow_on_pull_requests.md"))
    ]


def test_missing_source_snapshot_is_clear() -> None:
    context = RuleContext("example/service", FakeGitHub())

    with pytest.raises(RuntimeError, match="requires a source snapshot"):
        evaluate_agentic_rule(context, "ci_workflow_on_pull_requests.md")


def test_missing_agent_evaluator_is_clear(tmp_path: Path) -> None:
    context = RuleContext("example/service", FakeGitHub(), tmp_path / "source.zip")

    with pytest.raises(AgentError, match="No agent evaluator"):
        evaluate_agentic_rule(context, "ci_workflow_on_pull_requests.md")
