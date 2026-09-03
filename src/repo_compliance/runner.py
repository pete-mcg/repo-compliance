"""Run the ordered compliance rules for configured repositories."""

from pathlib import Path
from tempfile import TemporaryDirectory

from repo_compliance.config import ComplianceConfig, RepositoryConfig
from repo_compliance.domain import (
    GitHubApi,
    ResultStatus,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
    RuleResult,
)
from repo_compliance.errors import ArchiveError, GitHubError


def run_checks(
    config: ComplianceConfig,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
) -> tuple[RuleResult, ...]:
    """Run all enabled rules in configuration and registry order."""
    results: list[RuleResult] = []
    for repository in config.repositories:
        results.extend(_run_repository(repository, github, rules))
    return tuple(results)


def _run_repository(
    repository: RepositoryConfig,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
) -> tuple[RuleResult, ...]:
    exemptions = {item.rule: item.reason for item in repository.exemptions}
    active_rules = tuple(rule for rule in rules if rule.id not in exemptions)
    if not active_rules:
        return _evaluate_rules(repository.repository, github, rules, exemptions)

    preflight_error = _preflight(repository.repository, github)
    if preflight_error is not None:
        return _preflight_results(
            repository.repository, rules, exemptions, preflight_error
        )

    if not _needs_archive(active_rules):
        return _evaluate_rules(repository.repository, github, rules, exemptions)
    return _evaluate_with_archive(repository.repository, github, rules, exemptions)


def _preflight(repository: str, github: GitHubApi) -> str | None:
    try:
        github.ensure_main_branch(repository)
    except GitHubError as error:
        return str(error)
    return None


def _needs_archive(rules: tuple[RuleDefinition, ...]) -> bool:
    return any(rule.category is RuleCategory.STATIC_ANALYSIS for rule in rules)


def _evaluate_with_archive(
    repository: str,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
) -> tuple[RuleResult, ...]:
    with TemporaryDirectory(prefix="repo-compliance-") as temporary_directory:
        archive_path = Path(temporary_directory) / "repository.zip"
        try:
            github.download_main_archive(repository, archive_path)
        except GitHubError as error:
            return _evaluate_rules(
                repository,
                github,
                rules,
                exemptions,
                archive_error=str(error),
            )
        return _evaluate_rules(
            repository,
            github,
            rules,
            exemptions,
            archive_path=archive_path,
        )


def _evaluate_rules(
    repository: str,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
    *,
    archive_path: Path | None = None,
    archive_error: str | None = None,
) -> tuple[RuleResult, ...]:
    results: list[RuleResult] = []
    for rule in rules:
        exemption_reason = exemptions.get(rule.id)
        if exemption_reason is not None:
            results.append(_exempt_result(repository, rule, exemption_reason))
            continue
        if rule.category is RuleCategory.STATIC_ANALYSIS and archive_error is not None:
            results.append(_error_result(repository, rule, archive_error))
            continue
        results.append(_evaluate_rule(repository, github, rule, archive_path))
    return tuple(results)


def _evaluate_rule(
    repository: str,
    github: GitHubApi,
    rule: RuleDefinition,
    archive_path: Path | None,
) -> RuleResult:
    context = RuleContext(repository, github, archive_path)
    try:
        evaluation = rule.check(context)
    except (ArchiveError, GitHubError) as error:
        return _error_result(repository, rule, str(error))
    return _completed_result(repository, rule, evaluation)


def _completed_result(
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


def _exempt_result(repository: str, rule: RuleDefinition, reason: str) -> RuleResult:
    return RuleResult(repository, rule, ResultStatus.EXEMPT, reason)


def _error_result(repository: str, rule: RuleDefinition, message: str) -> RuleResult:
    return RuleResult(repository, rule, ResultStatus.ERROR, message)


def _preflight_results(
    repository: str,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
    error: str,
) -> tuple[RuleResult, ...]:
    results: list[RuleResult] = []
    for rule in rules:
        reason = exemptions.get(rule.id)
        if reason is not None:
            results.append(_exempt_result(repository, rule, reason))
        else:
            results.append(
                _error_result(repository, rule, f"Preflight failed: {error}")
            )
    return tuple(results)
