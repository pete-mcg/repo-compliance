"""Judge whether project documentation explains its purpose and how to run it."""

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

RULE_ID = "project-documentation-present"
PROMPT_FILENAME = rule_prompt_filename(RULE_ID)


def check(context: RuleContext) -> RuleEvaluation:
    """Ask the supplied evaluator to inspect the shared main-branch ZIP."""
    return evaluate_agentic_rule(context, PROMPT_FILENAME)


RULE = RuleDefinition(
    id=RULE_ID,
    title="Project documentation present",
    description="Project documentation must contain a project overview and setup instructions to run the project, tool, or application.",
    category=RuleCategory.AGENTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/project+documentation+present",
    check=check,
    requires_source_snapshot=True,
)
