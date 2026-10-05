"""Check that the repository's default branch is development."""

from pydantic import ValidationError

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import GitHubError
from repo_compliance.infrastructure.github.models import GitHubModel

RULE_ID = "default-branch-is-development"
EXPECTED_BRANCH = "development"
REPOSITORY_RESOURCE = "/repos/{repository}"


class Repository(GitHubModel):
    """Repository fields needed by this rule."""

    default_branch: str


def check(context: RuleContext) -> RuleEvaluation:
    """Pass only when the default branch is exactly development."""
    default_branch = _default_branch(context)
    return RuleEvaluation(
        passed=default_branch == EXPECTED_BRANCH,
        message=f"The default branch is '{default_branch}'; expected '{EXPECTED_BRANCH}'.",
    )


def _default_branch(context: RuleContext) -> str:
    resource = REPOSITORY_RESOURCE.format(repository=context.repository)
    payload = context.github.get_json_response(resource)
    try:
        repository = Repository.model_validate(payload)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error
    return repository.default_branch


RULE = RuleDefinition(
    id=RULE_ID,
    title="Default branch is development",
    description="The repository's default branch must be development.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/default-branch-is-development",
    check=check,
)
