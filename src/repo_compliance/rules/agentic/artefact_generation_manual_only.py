"""Judge whether artefact generation requires a manual workflow trigger."""

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

RULE_ID = "artefact-generation-manual-only"
PROMPT_FILENAME = rule_prompt_filename(RULE_ID)


def check(context: RuleContext) -> RuleEvaluation:
    """Ask the supplied evaluator to inspect the shared main-branch ZIP."""
    return evaluate_agentic_rule(context, PROMPT_FILENAME)


RULE = RuleDefinition(
    id=RULE_ID,
    title="Artefact generation requires a manual trigger",
    description="GitHub Actions must generate artefacts only when initiated manually.",
    category=RuleCategory.AGENTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/artefact+generation+manual+only",
    check=check,
    requires_source_snapshot=True,
)
