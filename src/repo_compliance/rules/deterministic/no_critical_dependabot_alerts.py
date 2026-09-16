"""Check for open Critical Dependabot alerts."""

from pydantic import TypeAdapter, ValidationError

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import GitHubError
from repo_compliance.github_models import GitHubModel

RULE_ID = "no-critical-dependabot-alerts"
ALERTS_RESOURCE = "/repos/{repository}/dependabot/alerts"


class DependabotAlert(GitHubModel):
    """Dependabot alert fields needed by this rule."""

    number: int


ALERTS_ADAPTER = TypeAdapter(tuple[DependabotAlert, ...])


def check(context: RuleContext) -> RuleEvaluation:
    """Pass only when GitHub returns no open Critical alerts."""
    if _has_critical_dependabot_alerts(context):
        return RuleEvaluation(False, "Open Critical Dependabot alerts exist.")
    return RuleEvaluation(True, "No open Critical Dependabot alerts exist.")


def _has_critical_dependabot_alerts(context: RuleContext) -> bool:
    resource = ALERTS_RESOURCE.format(repository=context.repository)
    payload = context.github.get_json(
        resource,
        params={"state": "open", "severity": "critical", "per_page": 1},
    )
    try:
        alerts = ALERTS_ADAPTER.validate_python(payload)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error
    return bool(alerts)


RULE = RuleDefinition(
    id=RULE_ID,
    title="No Critical Dependabot alerts",
    description="Dependabot must report zero open Critical vulnerabilities.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/no-critical-dependabot-alerts",
    check=check,
)
