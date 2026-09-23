import logging
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
from repo_compliance.errors import AgentError, GitHubError, SourceSnapshotError
from repo_compliance.rules.agentic.ci_workflow_on_pull_requests import RULE as CI_RULE
from repo_compliance.runner import run_all_compliance_checks

from .fakes import FakeAgentEvaluator, FakeGitHub


def make_rule(
    rule_id: str,
    category: RuleCategory,
    check: RuleCheck,
    *,
    requires_source_snapshot: bool = False,
) -> RuleDefinition:
    return RuleDefinition(
        id=rule_id,
        title=rule_id,
        description=rule_id,
        category=category,
        confidence=Confidence.HIGH,
        documentation_url="https://example.com/rule",
        check=check,
        requires_source_snapshot=requires_source_snapshot,
    )


def passing_check(_context: RuleContext) -> RuleEvaluation:
    return RuleEvaluation(True, "passed")


def get_source_snapshot_evaluation(context: RuleContext) -> RuleEvaluation:
    assert context.source_snapshot_path is not None
    assert context.source_snapshot_path.exists()
    return RuleEvaluation(True, "source snapshot inspected")


def file_check(context: RuleContext) -> RuleEvaluation:
    passed = context.github.file_exists_on_main(context.repository, "required.txt")
    return RuleEvaluation(passed, "file checked")


def config_for(*repositories: RepositoryConfig) -> ComplianceConfig:
    return ComplianceConfig(repositories=repositories)


def test_logs_progress_and_distinguishes_failure_from_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def failing_check(_context: RuleContext) -> RuleEvaluation:
        return RuleEvaluation(False, "Required file missing")

    def unavailable_check(_context: RuleContext) -> RuleEvaluation:
        raise GitHubError("Service unavailable")

    rules = (
        make_rule("fails", RuleCategory.DETERMINISTIC, failing_check),
        make_rule("errors", RuleCategory.DETERMINISTIC, unavailable_check),
    )
    with caplog.at_level(logging.INFO, logger="repo_compliance.runner"):
        run_all_compliance_checks(
            config_for(RepositoryConfig(repository="example/service")),
            FakeGitHub(),
            rules,
        )

    assert caplog.messages == [
        "Checking repository example/service",
        "Running fails for example/service",
        "example/service fails: fail (Required file missing)",
        "Running errors for example/service",
        "example/service errors: error (Service unavailable)",
    ]
    result_records = [caplog.records[2], caplog.records[4]]
    assert [record.levelno for record in result_records] == [
        logging.INFO,
        logging.ERROR,
    ]
    assert "Required file missing" in result_records[0].getMessage()
    assert "Service unavailable" in result_records[1].getMessage()


def test_fully_exempt_repository_skips_all_github_work() -> None:
    rules = (
        make_rule("first", RuleCategory.DETERMINISTIC, passing_check),
        make_rule(
            "second",
            RuleCategory.DETERMINISTIC,
            get_source_snapshot_evaluation,
            requires_source_snapshot=True,
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

    results = run_all_compliance_checks(config_for(repository), github, rules)

    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.EXEMPT,
    ]
    assert github.preflight_calls == []
    assert github.source_snapshot_calls == []


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

    results = run_all_compliance_checks(config_for(repository), github, rules)

    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.PASS,
    ]
    assert github.file_calls == [("example/service", "required.txt")]


def test_preflight_failure_errors_active_rules_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    rules = (
        make_rule("exempt", RuleCategory.DETERMINISTIC, passing_check),
        make_rule(
            "active",
            RuleCategory.DETERMINISTIC,
            get_source_snapshot_evaluation,
            requires_source_snapshot=True,
        ),
    )
    repository = RepositoryConfig(
        repository="example/service",
        exemptions=(ExemptionConfig(rule="exempt", reason="Approved"),),
    )
    github = FakeGitHub(preflight_error_repositories={"example/service"})

    with caplog.at_level(logging.INFO, logger="repo_compliance.runner"):
        results = run_all_compliance_checks(config_for(repository), github, rules)

    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.ERROR,
    ]
    assert "Preflight failed" in results[1].message
    assert github.source_snapshot_calls == []
    assert caplog.messages == [
        "Checking repository example/service",
        "example/service exempt: exempt (Approved)",
        f"example/service active: error ({results[1].message})",
    ]


def test_downloads_one_source_snapshot_for_multiple_source_snapshot_rules() -> None:
    rules = (
        make_rule(
            "source-snapshot-one",
            RuleCategory.DETERMINISTIC,
            get_source_snapshot_evaluation,
            requires_source_snapshot=True,
        ),
        make_rule(
            "source-snapshot-two",
            RuleCategory.DETERMINISTIC,
            get_source_snapshot_evaluation,
            requires_source_snapshot=True,
        ),
    )
    github = FakeGitHub()

    results = run_all_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        github,
        rules,
    )

    assert [result.status for result in results] == [
        ResultStatus.PASS,
        ResultStatus.PASS,
    ]
    assert github.source_snapshot_calls == ["example/service"]


def test_source_snapshot_failure_only_errors_source_snapshot_rules() -> None:
    rules = (
        make_rule("deterministic", RuleCategory.DETERMINISTIC, passing_check),
        make_rule(
            "source-snapshot",
            RuleCategory.DETERMINISTIC,
            get_source_snapshot_evaluation,
            requires_source_snapshot=True,
        ),
    )
    github = FakeGitHub(source_snapshot_error_repositories={"example/service"})

    results = run_all_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        github,
        rules,
    )

    assert [result.status for result in results] == [
        ResultStatus.PASS,
        ResultStatus.ERROR,
    ]
    assert results[1].message == "source snapshot is unavailable"


@pytest.mark.parametrize("error", [GitHubError, AgentError])
def test_expected_rule_error_does_not_stop_rules_or_repositories(
    error: type[GitHubError | AgentError],
) -> None:
    def sometimes_errors(context: RuleContext) -> RuleEvaluation:
        if context.repository == "example/first":
            raise error("Service unavailable")
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

    results = run_all_compliance_checks(config, FakeGitHub(), rules)

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


def test_source_snapshot_rule_error_becomes_result_data() -> None:
    def source_snapshot_error(_context: RuleContext) -> RuleEvaluation:
        raise SourceSnapshotError("bad zip")

    rule = make_rule(
        "source-snapshot",
        RuleCategory.DETERMINISTIC,
        source_snapshot_error,
        requires_source_snapshot=True,
    )

    results = run_all_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        FakeGitHub(),
        (rule,),
    )

    assert results[0].status is ResultStatus.ERROR
    assert results[0].message == "bad zip"


def test_unexpected_rule_bug_remains_fatal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def broken_check(_context: RuleContext) -> RuleEvaluation:
        assert "example/service first: pass (passed)" in caplog.messages
        raise RuntimeError("bug")

    rules = (
        make_rule("first", RuleCategory.DETERMINISTIC, passing_check),
        make_rule("broken", RuleCategory.DETERMINISTIC, broken_check),
    )

    with (
        caplog.at_level(logging.INFO, logger="repo_compliance.runner"),
        pytest.raises(RuntimeError, match="bug"),
    ):
        run_all_compliance_checks(
            config_for(RepositoryConfig(repository="example/service")),
            FakeGitHub(),
            rules,
        )


def test_source_snapshot_path_is_temporary() -> None:
    observed_paths: list[Path] = []

    def remember_source_snapshot(context: RuleContext) -> RuleEvaluation:
        assert context.source_snapshot_path is not None
        observed_paths.append(context.source_snapshot_path)
        return RuleEvaluation(True, "seen")

    rule = make_rule(
        "source-snapshot",
        RuleCategory.DETERMINISTIC,
        remember_source_snapshot,
        requires_source_snapshot=True,
    )

    run_all_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        FakeGitHub(),
        (rule,),
    )

    assert len(observed_paths) == 1
    assert not observed_paths[0].exists()


@pytest.mark.parametrize("agent_error", [None, AgentError("Agent unavailable")])
def test_agent_shares_snapshot_and_does_not_stop_other_checks(
    agent_error: AgentError | None,
) -> None:
    source_rule = make_rule(
        "other-source",
        RuleCategory.DETERMINISTIC,
        get_source_snapshot_evaluation,
        requires_source_snapshot=True,
    )
    github = FakeGitHub()
    evaluator = FakeAgentEvaluator(error=agent_error)
    results = run_all_compliance_checks(
        config_for(RepositoryConfig(repository="example/service")),
        github,
        (CI_RULE, source_rule),
        evaluator,
    )
    assert results[0].status is (
        ResultStatus.ERROR if agent_error else ResultStatus.PASS
    )
    assert results[1].status is ResultStatus.PASS
    assert github.source_snapshot_calls == ["example/service"]
    assert len(evaluator.calls) == 1
    assert not evaluator.calls[0][0].exists()


def test_exempt_agent_starts_no_evaluation_or_snapshot_download() -> None:
    repository = RepositoryConfig(
        repository="example/service",
        exemptions=(ExemptionConfig(rule=CI_RULE.id, reason="Approved exception"),),
    )
    github = FakeGitHub()
    evaluator = FakeAgentEvaluator()
    other_rule = make_rule("other", RuleCategory.DETERMINISTIC, passing_check)
    results = run_all_compliance_checks(
        config_for(repository), github, (CI_RULE, other_rule), evaluator
    )
    assert [result.status for result in results] == [
        ResultStatus.EXEMPT,
        ResultStatus.PASS,
    ]
    assert evaluator.calls == []
    assert github.source_snapshot_calls == []
