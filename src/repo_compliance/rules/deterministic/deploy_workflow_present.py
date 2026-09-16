"""Check for the required deployment workflow."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)

RULE_ID = "deploy-workflow-present"
REQUIRED_PATH = ".github/workflows/deploy.yml"


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when the exact deployment workflow path exists on main."""
    if context.github.file_exists(context.repository, REQUIRED_PATH):
        return RuleEvaluation(True, f"{REQUIRED_PATH} exists on main.")
    return RuleEvaluation(False, f"{REQUIRED_PATH} is missing from main.")


RULE = RuleDefinition(
    id=RULE_ID,
    title="Deployment workflow present",
    description=f"The main branch must contain {REQUIRED_PATH}.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/deploy-workflow-present",
    check=check,
)
