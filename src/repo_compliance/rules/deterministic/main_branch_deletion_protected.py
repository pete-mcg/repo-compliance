"""Check that the main branch cannot be deleted."""

from pydantic import TypeAdapter, ValidationError

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import GitHubError
from repo_compliance.infrastructure.github.models import GitHubModel

RULE_ID = "main-branch-deletion-protected"
RULESET_RESOURCE = "/repos/{repository}/rules/branches/main"
CLASSIC_PROTECTION_RESOURCE = "/repos/{repository}/branches/main/protection"


class BranchRule(GitHubModel):
    """Active repository rule fields needed by this rule."""

    type: str


class EnabledSetting(GitHubModel):
    """GitHub setting represented by an enabled flag."""

    enabled: bool


class BranchProtection(GitHubModel):
    """Classic branch protection fields needed by this rule."""

    allow_deletions: EnabledSetting


RULES_ADAPTER = TypeAdapter(tuple[BranchRule, ...])
PROTECTION_ADAPTER = TypeAdapter(BranchProtection)


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when a ruleset or classic protection blocks main deletion."""
    if "deletion" in _active_main_rule_types(context):
        return RuleEvaluation(
            passed=True,
            message="An active ruleset prevents main branch deletion.",
        )

    is_deletion_allowed = _classic_allow_deletions(context)
    if is_deletion_allowed is False:
        return RuleEvaluation(
            passed=True,
            message="Classic branch protection prevents main branch deletion.",
        )

    return RuleEvaluation(
        passed=False,
        message="The main branch is not protected against deletion.",
    )


def _active_main_rule_types(context: RuleContext) -> frozenset[str]:
    resource = RULESET_RESOURCE.format(repository=context.repository)
    payload = context.github.get_json_response(resource, params={"per_page": 100})
    try:
        rules = RULES_ADAPTER.validate_python(payload)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error
    return frozenset(rule.type for rule in rules)


def _classic_allow_deletions(context: RuleContext) -> bool | None:
    resource = CLASSIC_PROTECTION_RESOURCE.format(repository=context.repository)
    payload = context.github.get_json_response(resource, missing_ok=True)
    if payload is None:
        return None
    try:
        protection = PROTECTION_ADAPTER.validate_python(payload)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error
    return protection.allow_deletions.enabled


RULE = RuleDefinition(
    id=RULE_ID,
    title="Main branch deletion protected",
    description="The main branch must be protected against deletion.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/main-branch-deletion-protected",
    check=check,
)
