"""Check that the main branch cannot be deleted."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)

RULE_ID = "main-branch-deletion-protected"


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when a ruleset or classic protection blocks main deletion."""
    if "deletion" in context.github.active_main_rule_types(context.repository):
        return RuleEvaluation(
            passed=True,
            message="An active ruleset prevents main branch deletion.",
        )

    is_deletion_allowed = context.github.classic_allow_deletions(context.repository)
    if is_deletion_allowed is False:
        return RuleEvaluation(
            passed=True,
            message="Classic branch protection prevents main branch deletion.",
        )

    return RuleEvaluation(
        passed=False,
        message="The main branch is not protected against deletion.",
    )


RULE = RuleDefinition(
    id=RULE_ID,
    title="Main branch deletion protected",
    description="The main branch must be protected against deletion.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://docs.github.com/en/rest/repos/rules",
    check=check,
)
