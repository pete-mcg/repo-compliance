"""Check all reported checks on the latest main commit."""

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

RULE_ID = "main-latest-commit-checks-passed"
COMMIT_RESOURCE = "/repos/{repository}/commits/main"
CHECK_RUNS_RESOURCE = "/repos/{repository}/commits/{sha}/check-runs"
STATUS_RESOURCE = "/repos/{repository}/commits/{sha}/status"
PAGE_SIZE = 100
PASSING_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})


class Commit(GitHubModel):
    """Commit identifier used to keep requests on the same commit."""

    sha: str


class CheckRun(GitHubModel):
    """Reported check outcome."""

    name: str
    status: str
    conclusion: str | None


class CheckRuns(GitHubModel):
    """One page of check runs."""

    check_runs: tuple[CheckRun, ...]


class CombinedStatus(GitHubModel):
    """Overall result of the latest commit status in each context."""

    state: str
    total_count: int


COMMIT_ADAPTER = TypeAdapter(Commit)
CHECK_RUNS_ADAPTER = TypeAdapter(CheckRuns)
STATUS_ADAPTER = TypeAdapter(CombinedStatus)


def check(context: RuleContext) -> RuleEvaluation:
    """Pass when all reported checks pass, including when there are none."""
    resource = COMMIT_RESOURCE.format(repository=context.repository)
    payload = context.github.get_json_response(resource, missing_ok=True)
    if payload is None:
        return RuleEvaluation(False, "The main branch has no accessible latest commit.")
    commit = _validate_response(payload, COMMIT_ADAPTER, resource)
    runs = _check_runs(context, commit.sha)
    resource = STATUS_RESOURCE.format(repository=context.repository, sha=commit.sha)
    payload = context.github.get_json_response(resource)
    status = _validate_response(payload, STATUS_ADAPTER, resource)
    return _evaluate_checks(commit.sha, runs, status)


def _evaluate_checks(
    sha: str, runs: list[CheckRun], status: CombinedStatus
) -> RuleEvaluation:
    for run in runs:
        if run.status != "completed" or run.conclusion not in PASSING_CONCLUSIONS:
            return RuleEvaluation(
                False,
                f"Latest main commit {sha}: check '{run.name}' has "
                f"status {run.status} and conclusion {run.conclusion}.",
            )
    if status.total_count and status.state != "success":
        return RuleEvaluation(
            False,
            f"Latest main commit {sha}: commit statuses are {status.state}.",
        )
    if not runs and not status.total_count:
        return RuleEvaluation(True, f"Latest main commit {sha} has no checks.")
    return RuleEvaluation(True, f"All checks passed on latest main commit {sha}.")


def _check_runs(context: RuleContext, sha: str) -> list[CheckRun]:
    resource = CHECK_RUNS_RESOURCE.format(repository=context.repository, sha=sha)
    runs: list[CheckRun] = []
    page = 1
    while True:
        payload = context.github.get_json_response(
            resource,
            params={"filter": "latest", "per_page": PAGE_SIZE, "page": page},
        )
        response = _validate_response(payload, CHECK_RUNS_ADAPTER, resource)
        runs.extend(response.check_runs)
        if len(response.check_runs) < PAGE_SIZE:
            return runs
        page += 1


def _validate_response[T](payload: object, adapter: TypeAdapter[T], resource: str) -> T:
    try:
        return adapter.validate_python(payload)
    except ValidationError as error:
        raise GitHubError(f"GitHub returned invalid data for '{resource}'.") from error


RULE = RuleDefinition(
    id=RULE_ID,
    title="Latest main commit checks passed",
    description="All reported checks on the latest commit on main must pass.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.HIGH,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/latest-commit-passes",
    check=check,
)
