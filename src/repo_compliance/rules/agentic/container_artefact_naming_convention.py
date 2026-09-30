"""Judge whether container builds follow the image tag naming convention."""

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

RULE_ID = "container-artefact-naming-convention"
PROMPT_FILENAME = rule_prompt_filename(RULE_ID)


def check(context: RuleContext) -> RuleEvaluation:
    """Ask the supplied evaluator to inspect the shared main-branch ZIP."""
    return evaluate_agentic_rule(context, PROMPT_FILENAME)


RULE = RuleDefinition(
    id=RULE_ID,
    title="Container artefacts follow the image tag naming convention",
    description=(
        "Container builds must publish branch-latest and branch-date.run-number tags, "
        "plus latest for main builds and the matching Git tag for tag builds."
    ),
    category=RuleCategory.AGENTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/container+artefact+naming+convention",
    check=check,
    requires_source_snapshot=True,
)
