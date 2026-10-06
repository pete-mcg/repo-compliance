"""Check the latest deployment status in each deployed environment."""

from pydantic import AwareDatetime, TypeAdapter, ValidationError

from repo_compliance.domain import (
    Confidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import GitHubError
from repo_compliance.infrastructure.github.models import GitHubModel

RULE_ID = "latest-deployments-successful"
DEPLOYMENTS_RESOURCE = "/repos/{repository}/deployments"
STATUSES_RESOURCE = "/repos/{repository}/deployments/{deployment_id}/statuses"
PAGE_SIZE = 100


class Deployment(GitHubModel):
    """Deployment fields used to find the newest deployment per environment."""

    id: int
    environment: str
    created_at: AwareDatetime


class DeploymentStatus(GitHubModel):
    """Status fields used to find a deployment's newest status."""

    id: int
    state: str
    created_at: AwareDatetime


DEPLOYMENTS_ADAPTER = TypeAdapter(tuple[Deployment, ...])
STATUSES_ADAPTER = TypeAdapter(tuple[DeploymentStatus, ...])


def check(context: RuleContext) -> RuleEvaluation:
    """Pass only when every environment's latest deployment has status success."""
    deployments = _latest_deployments(context)
    if not deployments:
        return RuleEvaluation(True, "No deployed environments to check.")

    passed = True
    details: list[str] = []
    for environment, deployment in sorted(deployments.items()):
        state = _latest_status(context, deployment.id)
        details.append(f"{environment}: {state}")
        if state != "success":
            passed = False
    return RuleEvaluation(passed, "Latest deployments: " + "; ".join(details) + ".")


def _latest_deployments(context: RuleContext) -> dict[str, Deployment]:
    resource = DEPLOYMENTS_RESOURCE.format(repository=context.repository)
    latest: dict[str, Deployment] = {}
    for deployment in _get_records(context, resource, DEPLOYMENTS_ADAPTER):
        previous = latest.get(deployment.environment)
        if previous is None or (deployment.created_at, deployment.id) > (
            previous.created_at,
            previous.id,
        ):
            latest[deployment.environment] = deployment
    return latest


def _latest_status(context: RuleContext, deployment_id: int) -> str:
    resource = STATUSES_RESOURCE.format(
        repository=context.repository, deployment_id=deployment_id
    )
    statuses = _get_records(context, resource, STATUSES_ADAPTER)
    if not statuses:
        return "no status"
    latest = max(statuses, key=lambda status: (status.created_at, status.id))
    return latest.state


def _get_records[T](
    context: RuleContext, resource: str, adapter: TypeAdapter[tuple[T, ...]]
) -> list[T]:
    records: list[T] = []
    page = 1
    while True:
        payload = context.github.get_json_response(
            resource, params={"per_page": PAGE_SIZE, "page": page}
        )
        try:
            response = adapter.validate_python(payload)
        except ValidationError as error:
            raise GitHubError(
                f"GitHub returned invalid data for '{resource}'."
            ) from error
        records.extend(response)
        if len(response) < PAGE_SIZE:
            return records
        page += 1


RULE = RuleDefinition(
    id=RULE_ID,
    title="Latest deployments successful",
    description="The latest deployment to each environment must have status success.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/latest-deployments-successful",
    check=check,
)
