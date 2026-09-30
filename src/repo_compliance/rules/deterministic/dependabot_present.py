"""Check for the required Dependabot configuration file."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)

RULE_ID = "dependabot-present"
REQUIRED_PATH = ".github/dependabot.yml"


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when the exact Dependabot configuration path exists on main."""
    if context.github.file_exists_on_main(context.repository, REQUIRED_PATH):
        return RuleEvaluation(True, f"{REQUIRED_PATH} exists on main.")
    return RuleEvaluation(False, f"{REQUIRED_PATH} is missing from main.")


RULE = RuleDefinition(
    id=RULE_ID,
    title="Dependabot configuration present",
    description=f"The main branch must contain {REQUIRED_PATH}.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/dependabot-present",
    check=check,
)
