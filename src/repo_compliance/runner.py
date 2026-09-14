"""Run the ordered compliance rules for configured repositories."""

from pathlib import Path
from tempfile import TemporaryDirectory

from repo_compliance.config import ComplianceConfig, RepositoryConfig
from repo_compliance.domain import (
    GitHubApi,
    ResultStatus,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
    RuleResult,
)
from repo_compliance.errors import ArchiveError, GitHubError


def get_compliance_results(
    config: ComplianceConfig,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
) -> tuple[RuleResult, ...]:
    """Run all enabled rules in configuration and registry order."""
    results: list[RuleResult] = []
    for repository in config.repositories:
        results.extend(_get_repository_results(repository, github, rules))
    return tuple(results)


def _get_repository_results(
    repository: RepositoryConfig,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
) -> tuple[RuleResult, ...]:
    exemptions = {item.rule: item.reason for item in repository.exemptions}
    active_rules = tuple(rule for rule in rules if rule.id not in exemptions)
    if not active_rules:
        return _get_rule_results(repository.repository, github, rules, exemptions)

    preflight_error = _get_preflight_error(repository.repository, github)
    if preflight_error is not None:
        return _compose_preflight_results(
            repository.repository, rules, exemptions, preflight_error
        )

    if not _should_get_archive(active_rules):
        return _get_rule_results(repository.repository, github, rules, exemptions)
    return _get_archive_results(repository.repository, github, rules, exemptions)


def _get_preflight_error(repository: str, github: GitHubApi) -> str | None:
    try:
        github.get_main_branch(repository)
    except GitHubError as error:
        return str(error)
    return None


def _should_get_archive(rules: tuple[RuleDefinition, ...]) -> bool:
    return any(rule.requires_archive for rule in rules)


def _get_archive_results(
    repository: str,
    github: GitHubApi,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
) -> tuple[RuleResult, ...]:
    with TemporaryDirectory(prefix="repo-compliance-") as temporary_directory:
        archive_path = Path(temporary_directory) / "repository.zip"
        try:
            github.get_main_archive(repository, archive_path)
        except GitHubError as error:
            return _get_rule_results(
                repository,
                github,
                rules,
                exemptions,
                archive_error=str(error),
            )
        return _get_rule_results(
            repository,
            github,
            rules,
            exemptions,
            archive_path=archive_path,
        )


def _get_rule_results(
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
            results.append(_compose_exempt_result(repository, rule, exemption_reason))
            continue
        if rule.requires_archive and archive_error is not None:
            results.append(_compose_error_result(repository, rule, archive_error))
            continue
        results.append(_get_rule_result(repository, github, rule, archive_path))
    return tuple(results)


def _get_rule_result(
    repository: str,
    github: GitHubApi,
    rule: RuleDefinition,
    archive_path: Path | None,
) -> RuleResult:
    context = RuleContext(repository, github, archive_path)
    try:
        evaluation = rule.get_evaluation(context)
    except (ArchiveError, GitHubError) as error:
        return _compose_error_result(repository, rule, str(error))
    return _compose_completed_result(repository, rule, evaluation)


def _compose_completed_result(
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


def _compose_exempt_result(
    repository: str,
    rule: RuleDefinition,
    reason: str,
) -> RuleResult:
    return RuleResult(repository, rule, ResultStatus.EXEMPT, reason)


def _compose_error_result(
    repository: str,
    rule: RuleDefinition,
    message: str,
) -> RuleResult:
    return RuleResult(repository, rule, ResultStatus.ERROR, message)


def _compose_preflight_results(
    repository: str,
    rules: tuple[RuleDefinition, ...],
    exemptions: dict[str, str],
    error: str,
) -> tuple[RuleResult, ...]:
    results: list[RuleResult] = []
    for rule in rules:
        reason = exemptions.get(rule.id)
        if reason is not None:
            results.append(_compose_exempt_result(repository, rule, reason))
        else:
            results.append(
                _compose_error_result(repository, rule, f"Preflight failed: {error}")
            )
    return tuple(results)
