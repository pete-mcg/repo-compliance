"""Check for open Critical Dependabot alerts."""

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)

RULE_ID = "no-critical-dependabot-alerts"


def check(context: RuleContext) -> RuleEvaluation:
    """Pass only when GitHub returns no open Critical alerts."""
    if context.github.has_critical_dependabot_alerts(context.repository):
        return RuleEvaluation(False, "Open Critical Dependabot alerts exist.")
    return RuleEvaluation(True, "No open Critical Dependabot alerts exist.")


RULE = RuleDefinition(
    id=RULE_ID,
    title="No Critical Dependabot alerts",
    description="Dependabot must report zero open Critical vulnerabilities.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://docs.github.com/en/rest/dependabot/alerts",
    check=check,
)
