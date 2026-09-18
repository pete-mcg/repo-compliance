"""Judge whether GitHub Actions declares CI for pull requests to main."""

from importlib.resources import files

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import AgentError


def load_prompt() -> str:
    """Load the packaged rule instructions independently of the current directory."""
    return (
        files("repo_compliance.rules.agentic")
        .joinpath("ci_workflow_on_pull_requests.md")
        .read_text(encoding="utf-8")
    )


def check(context: RuleContext) -> RuleEvaluation:
    """Ask the supplied evaluator to inspect the shared main-branch ZIP."""
    if context.source_snapshot_path is None:
        raise RuntimeError("Rule requires a source snapshot.")
    if context.agent_evaluator is None:
        raise AgentError("No agent evaluator is configured.")
    return context.agent_evaluator.evaluate(context.source_snapshot_path, load_prompt())


RULE = RuleDefinition(
    id="ci-workflow-on-pull-requests",
    title="CI runs on pull requests to main",
    description="A GitHub Actions CI workflow must run for every pull request to main.",
    category=RuleCategory.AGENTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/ci+workflow+on+pull+requests",
    check=check,
    requires_source_snapshot=True,
)
