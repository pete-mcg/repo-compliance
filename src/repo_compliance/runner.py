"""Run the ordered compliance rules for configured repositories."""

from pathlib import Path
from tempfile import TemporaryDirectory

from repo_compliance.config import ComplianceConfig, RepositoryConfig
from repo_compliance.domain import (
    ResultStatus,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
    RuleResult,
)
from repo_compliance.errors import AgentError, GitHubError, SourceSnapshotError
from repo_compliance.ports import AgentEvaluator, GitHubApi


def run_all_compliance_checks(
    config: ComplianceConfig,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    agent_evaluator: AgentEvaluator | None = None,
) -> tuple[RuleResult, ...]:
    """Run all enabled rules in configuration and registry order."""
    results: list[RuleResult] = []
    for repository in config.repositories:
        results.extend(
            _run_checks_for_repository(repository, github, rules, agent_evaluator)
        )
    return tuple(results)


def _run_checks_for_repository(
    repository: RepositoryConfig,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    agent_evaluator: AgentEvaluator | None,
) -> tuple[RuleResult, ...]:
    exemptions = {item.rule: item.reason for item in repository.exemptions}
    active_rules = tuple(rule for rule in rules if rule.id not in exemptions)
    if not active_rules:
        return _build_rule_results(
            repository.repository, github, rules, exemptions, agent_evaluator
        )

    preflight_error = _preflight_checks(repository.repository, github)
    if preflight_error is not None:
        return _result_when_preflight_error(
            repository.repository, rules, exemptions, preflight_error
        )

    if not _requires_source_snapshot(active_rules):
        return _build_rule_results(
            repository.repository, github, rules, exemptions, agent_evaluator
        )
    return _build_rule_results_with_source_snapshot(
        repository.repository, github, rules, exemptions, agent_evaluator
    )


def _preflight_checks(repository: str, github: GitHubApi) -> str | None:
    # Potentially more checks to be added in future.
    try:
        github.ensure_accessible_repository(repository)
    except GitHubError as error:
        return str(error)
    return None


def _requires_source_snapshot(rules: tuple[RuleDefinition, ...]) -> bool:
    return any(rule.requires_source_snapshot for rule in rules)


def _build_rule_results_with_source_snapshot(
    repository: str,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
    agent_evaluator: AgentEvaluator | None,
) -> tuple[RuleResult, ...]:
    with TemporaryDirectory(prefix="repo-compliance-") as temporary_directory:
        source_snapshot_path = Path(temporary_directory) / "repository.zip"
        try:
            github.download_source_snapshot_from_main(repository, source_snapshot_path)
        except GitHubError as error:
            return _build_rule_results(
                repository,
                github,
                rules,
                exemptions,
                agent_evaluator,
                source_snapshot_error=str(error),
            )
        return _build_rule_results(
            repository,
            github,
            rules,
            exemptions,
            agent_evaluator,
            source_snapshot_path=source_snapshot_path,
        )


def _build_rule_results(
    repository: str,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
    agent_evaluator: AgentEvaluator | None,
    *,
    source_snapshot_path: Path | None = None,
    source_snapshot_error: str | None = None,
) -> tuple[RuleResult, ...]:
    results: list[RuleResult] = []
    for rule in rules:
        exemption_reason = exemptions.get(rule.id)
        if exemption_reason is not None:
            results.append(
                _result_when_test_exemption(repository, rule, exemption_reason)
            )
            continue
        if rule.requires_source_snapshot and source_snapshot_error is not None:
            results.append(
                _result_when_test_error(repository, rule, source_snapshot_error)
            )
            continue
        results.append(
            _run_rule_test(
                repository, github, rule, source_snapshot_path, agent_evaluator
            )
        )
    return tuple(results)


def _run_rule_test(
    repository: str,
    github: GitHubApi,
    rule: RuleDefinition,
    source_snapshot_path: Path | None,
    agent_evaluator: AgentEvaluator | None,
) -> RuleResult:
    context = RuleContext(repository, github, source_snapshot_path, agent_evaluator)
    try:
        evaluation = rule.check(context)
    except (SourceSnapshotError, GitHubError, AgentError) as error:
        return _result_when_test_error(repository, rule, str(error))
    return _result_when_test_completed(repository, rule, evaluation)


def _result_when_test_completed(
    repository: str,
    rule: RuleDefinition,
    evaluation: RuleEvaluation,
) -> RuleResult:
    status = ResultStatus.PASS if evaluation.passed else ResultStatus.FAIL
    return RuleResult(
        repository=repository,
        rule=rule,
        status=status,
        message=evaluation.message,
        evidence=evaluation.evidence,
        omitted_evidence_count=evaluation.omitted_evidence_count,
    )


def _result_when_test_exemption(
    repository: str,
    rule: RuleDefinition,
    reason: str,
) -> RuleResult:
    return RuleResult(repository, rule, ResultStatus.EXEMPT, reason)


def _result_when_test_error(
    repository: str,
    rule: RuleDefinition,
    message: str,
) -> RuleResult:
    return RuleResult(repository, rule, ResultStatus.ERROR, message)


def _result_when_preflight_error(
    repository: str,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
    error: str,
) -> tuple[RuleResult, ...]:
    results: list[RuleResult] = []
    for rule in rules:
        reason = exemptions.get(rule.id)
        if reason is not None:
            results.append(_result_when_test_exemption(repository, rule, reason))
        else:
            results.append(
                _result_when_test_error(repository, rule, f"Preflight failed: {error}")
            )
    return tuple(results)
