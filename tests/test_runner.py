from pathlib import Path

import pytest

from repo_compliance.config import ComplianceConfig, ExemptionConfig, RepositoryConfig
from repo_compliance.domain import (
    Confidence,
    ResultStatus,
    RuleCategory,
    RuleCheck,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import ArchiveError, GitHubError
from repo_compliance.runner import run_compliance_checks

from .fakes import FakeGitHub


def make_rule(
    rule_id: str,
    category: RuleCategory,
    check: RuleCheck,
    *,
    requires_archive: bool = False,
) -> RuleDefinition:
    return RuleDefinition(
        id=rule_id,
        title=rule_id,
        description=rule_id,
        category=category,
        confidence=Confidence.HIGH,
        documentation_url="https://example.com/rule",
        check=check,
        requires_archive=requires_archive,
    )


def passing_check(_context: RuleContext) -> RuleEvaluation:
    return RuleEvaluation(True, "passed")


def get_archive_evaluation(context: RuleContext) -> RuleEvaluation:
    assert context.archive_path is not None
    assert context.archive_path.exists()
    return RuleEvaluation(True, "archive inspected")


def file_check(context: RuleContext) -> RuleEvaluation:
    passed = context.github.file_exists(context.repository, "required.txt")
    return RuleEvaluation(passed, "file checked")


def config_for(*repositories: RepositoryConfig) -> ComplianceConfig:
    return ComplianceConfig(repositories=repositories)


def test_fully_exempt_repository_skips_all_github_work() -> None:
    rules = (
        make_rule("first", RuleCategory.DETERMINISTIC, passing_check),
        make_rule(
            "second",
            RuleCategory.DETERMINISTIC,
            get_archive_evaluation,
            requires_archive=True,
        ),
    )
    repository = RepositoryConfig(
        repository="example/service",
        exemptions=(
            ExemptionConfig(rule="first", reason="First exception"),
            ExemptionConfig(rule="second", reason="Second exception"),
        ),
    )
    github = FakeGitHub()

    results = run_compliance_checks(config_for(repository), github, rules)

    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.EXEMPT,
    ]
    assert github.preflight_calls == []
    assert github.archive_calls == []


def test_exemption_skips_only_its_check() -> None:
    rules = (
        make_rule("exempt-file", RuleCategory.DETERMINISTIC, file_check),
        make_rule("active-file", RuleCategory.DETERMINISTIC, file_check),
    )
    repository = RepositoryConfig(
        repository="example/service",
        exemptions=(ExemptionConfig(rule="exempt-file", reason="Not applicable"),),
    )
    github = FakeGitHub(files={"required.txt"})

    results = run_compliance_checks(config_for(repository), github, rules)

    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.PASS,
    ]
    assert github.file_calls == [("example/service", "required.txt")]


def test_preflight_failure_errors_active_rules_only() -> None:
    rules = (
        make_rule("exempt", RuleCategory.DETERMINISTIC, passing_check),
        make_rule(
            "active",
            RuleCategory.DETERMINISTIC,
            get_archive_evaluation,
            requires_archive=True,
        ),
    )
    repository = RepositoryConfig(
        repository="example/service",
        exemptions=(ExemptionConfig(rule="exempt", reason="Approved"),),
    )
    github = FakeGitHub(preflight_error_repositories={"example/service"})

    results = run_compliance_checks(config_for(repository), github, rules)

    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.ERROR,
    ]
    assert "Preflight failed" in results[1].message
    assert github.archive_calls == []


def test_downloads_one_archive_for_multiple_archive_rules() -> None:
    rules = (
        make_rule(
            "archive-one",
            RuleCategory.DETERMINISTIC,
            get_archive_evaluation,
            requires_archive=True,
        ),
        make_rule(
            "archive-two",
            RuleCategory.DETERMINISTIC,
            get_archive_evaluation,
            requires_archive=True,
        ),
    )
    github = FakeGitHub()

    results = run_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        github,
        rules,
    )

    assert [result.status for result in results] == [
        ResultStatus.PASS,
        ResultStatus.PASS,
    ]
    assert github.archive_calls == ["example/service"]


def test_archive_failure_only_errors_archive_rules() -> None:
    rules = (
        make_rule("deterministic", RuleCategory.DETERMINISTIC, passing_check),
        make_rule(
            "archive",
            RuleCategory.DETERMINISTIC,
            get_archive_evaluation,
            requires_archive=True,
        ),
    )
    github = FakeGitHub(archive_error_repositories={"example/service"})

    results = run_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        github,
        rules,
    )

    assert [result.status for result in results] == [
        ResultStatus.PASS,
        ResultStatus.ERROR,
    ]
    assert results[1].message == "archive is unavailable"


def test_expected_rule_error_does_not_stop_rules_or_repositories() -> None:
    def sometimes_errors(context: RuleContext) -> RuleEvaluation:
        if context.repository == "example/first":
            raise GitHubError("API unavailable")
        return RuleEvaluation(True, "passed")

    rules = (
        make_rule(
            "sometimes-errors",
            RuleCategory.DETERMINISTIC,
            sometimes_errors,
        ),
        make_rule("always-passes", RuleCategory.DETERMINISTIC, passing_check),
    )
    config = config_for(
        RepositoryConfig(repository="example/first"),
        RepositoryConfig(repository="example/second"),
    )

    results = run_compliance_checks(config, FakeGitHub(), rules)

    assert [result.status for result in results] == [
        ResultStatus.ERROR,
        ResultStatus.PASS,
        ResultStatus.PASS,
        ResultStatus.PASS,
    ]
    assert [result.repository for result in results] == [
        "example/first",
        "example/first",
        "example/second",
        "example/second",
    ]


def test_archive_rule_error_becomes_result_data() -> None:
    def archive_error(_context: RuleContext) -> RuleEvaluation:
        raise ArchiveError("bad zip")

    rule = make_rule(
        "archive",
        RuleCategory.DETERMINISTIC,
        archive_error,
        requires_archive=True,
    )

    results = run_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        FakeGitHub(),
        (rule,),
    )

    assert results[0].status is ResultStatus.ERROR
    assert results[0].message == "bad zip"


def test_unexpected_rule_bug_remains_fatal() -> None:
    def broken_check(_context: RuleContext) -> RuleEvaluation:
        raise RuntimeError("bug")

    rule = make_rule("broken", RuleCategory.DETERMINISTIC, broken_check)

    with pytest.raises(RuntimeError, match="bug"):
        run_compliance_checks(
            config_for(RepositoryConfig(repository="example/service")),
            FakeGitHub(),
            (rule,),
        )


def test_archive_path_is_temporary() -> None:
    observed_paths: list[Path] = []

    def remember_archive(context: RuleContext) -> RuleEvaluation:
        assert context.archive_path is not None
        observed_paths.append(context.archive_path)
        return RuleEvaluation(True, "seen")

    rule = make_rule(
        "archive",
        RuleCategory.DETERMINISTIC,
        remember_archive,
        requires_archive=True,
    )

    run_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        FakeGitHub(),
        (rule,),
    )

    assert len(observed_paths) == 1
    assert not observed_paths[0].exists()
