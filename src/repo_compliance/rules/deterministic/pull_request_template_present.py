"""Check for the required pull request template."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)

RULE_ID = "pull-request-template-present"
REQUIRED_PATH = ".github/pull_request_template.md"


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when the exact pull request template path exists on main."""
    if context.github.file_exists_on_main(context.repository, REQUIRED_PATH):
        return RuleEvaluation(True, f"{REQUIRED_PATH} exists on main.")
    return RuleEvaluation(False, f"{REQUIRED_PATH} is missing from main.")


RULE = RuleDefinition(
    id=RULE_ID,
    title="Pull request template present",
    description=f"The main branch must contain {REQUIRED_PATH}.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/pull-request-template-present",
    check=check,
)
