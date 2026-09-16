"""Check for the required CODEOWNERS file."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)

RULE_ID = "codeowners-present"
REQUIRED_PATH = ".github/CODEOWNERS"


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when the exact CODEOWNERS path exists on main."""
    if context.github.file_exists(context.repository, REQUIRED_PATH):
        return RuleEvaluation(True, f"{REQUIRED_PATH} exists on main.")
    return RuleEvaluation(False, f"{REQUIRED_PATH} is missing from main.")


RULE = RuleDefinition(
    id=RULE_ID,
    title="CODEOWNERS present",
    description=f"The main branch must contain {REQUIRED_PATH}.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners",
    check=check,
)
