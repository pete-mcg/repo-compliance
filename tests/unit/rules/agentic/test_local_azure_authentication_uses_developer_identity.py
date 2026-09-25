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
from repo_compliance.rules.agentic.helpers import load_rule_prompt
from repo_compliance.rules.agentic.local_azure_authentication_uses_developer_identity import (
    PROMPT_FILENAME,
    RULE,
    check,
)
from repo_compliance.rules.registry import RULES


@pytest.mark.parametrize("passed", [True, False])
def test_rule_loads_prompt_outside_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, passed: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    snapshot = tmp_path / "source.zip"
    snapshot.touch()
    evaluation = RuleEvaluation(
        passed, "Judgement", (Evidence("src/auth.py", 10, "local credential"),)
    )
    evaluator = FakeAgentEvaluator(evaluation)
    context = RuleContext("example/service", FakeGitHub(), snapshot, evaluator)

    assert check(context) == evaluation
    assert evaluator.calls == [(snapshot, load_rule_prompt(PROMPT_FILENAME))]
    assert RULE in RULES
    assert RULE.category is RuleCategory.AGENTIC
    assert RULE.confidence is Confidence.MEDIUM
    assert RULE.requires_source_snapshot
