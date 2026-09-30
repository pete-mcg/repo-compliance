"""Judge whether GitHub Actions declares CI for pull requests and pushes to development."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.rules.agentic.helpers import (
    evaluate_agentic_rule,
    rule_prompt_filename,
)

RULE_ID = "ci-workflow-targeting-development"
PROMPT_FILENAME = rule_prompt_filename(RULE_ID)


def check(context: RuleContext) -> RuleEvaluation:
    """Ask the supplied evaluator to inspect the shared main-branch ZIP."""
    return evaluate_agentic_rule(context, PROMPT_FILENAME)


RULE = RuleDefinition(
    id=RULE_ID,
    title="CI runs on pull requests and pushes to development",
    description="A GitHub Actions CI workflow must run for every pull request and push to development.",
    category=RuleCategory.AGENTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/ci+workflow+targeting+development",
    check=check,
    requires_source_snapshot=True,
)
