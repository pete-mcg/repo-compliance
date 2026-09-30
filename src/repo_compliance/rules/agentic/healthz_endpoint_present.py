"""Judge whether the HTTP application exposes the standard health endpoint."""

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

RULE_ID = "healthz-endpoint-present"
PROMPT_FILENAME = rule_prompt_filename(RULE_ID)


def check(context: RuleContext) -> RuleEvaluation:
    """Ask the supplied evaluator to inspect the shared main-branch ZIP."""
    return evaluate_agentic_rule(context, PROMPT_FILENAME)


RULE = RuleDefinition(
    id=RULE_ID,
    title="Healthz endpoint present",
    description=(
        "The HTTP application must expose /healthz, returning HTTP 200 when "
        "available and usable, with Healthy in the default successful response body."
    ),
    category=RuleCategory.AGENTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/healthz+endpoint+present",
    check=check,
    requires_source_snapshot=True,
)
