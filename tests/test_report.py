from datetime import UTC, datetime, timedelta, timezone

from repo_compliance.config import ComplianceConfig, RepositoryConfig
from repo_compliance.domain import (
    Confidence,
    Evidence,
    ResultStatus,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
    RuleResult,
)
from repo_compliance.report import generate_report


def unused_check(_context: RuleContext) -> RuleEvaluation:
    return RuleEvaluation(True, "unused")


def make_rule(
    rule_id: str,
    category: RuleCategory = RuleCategory.DETERMINISTIC,
    confidence: Confidence = Confidence.HIGH,
) -> RuleDefinition:
    return RuleDefinition(
        id=rule_id,
        title=f"Title {rule_id}",
        description=f"Description {rule_id}",
        category=category,
        confidence=confidence,
        documentation_url=f"https://example.com/{rule_id}",
        check=unused_check,
    )


def test_report_contains_counts_tables_links_details_and_utc_timestamp() -> None:
    deterministic = make_rule("deterministic")
    agentic = make_rule(
        "agentic",
        RuleCategory.AGENTIC,
        Confidence.MEDIUM,
    )
    config = ComplianceConfig(
        repositories=(
            RepositoryConfig(repository="example/first"),
            RepositoryConfig(repository="example/second"),
        )
    )
    results = (
        RuleResult("example/first", deterministic, ResultStatus.PASS, "All good"),
        RuleResult(
            "example/first",
            agentic,
            ResultStatus.FAIL,
            "bad | marker\nfound [link] *bold* <tag>",
            evidence=(Evidence("src/config`file.py", 7, "api-key"),),
            omitted_evidence_count=3,
        ),
        RuleResult("example/second", deterministic, ResultStatus.EXEMPT, "Approved"),
        RuleResult("example/second", agentic, ResultStatus.ERROR, "API unavailable"),
    )
    generated_at = datetime(
        2026,
        9,
        3,
        12,
        30,
        tzinfo=timezone(timedelta(hours=1)),
    )

    report = generate_report(
        config,
        (deterministic, agentic),
        results,
        generated_at=generated_at,
    )

    assert "Generated at `2026-09-03T11:30:00Z`" in report
    assert "- Repositories: 2" in report
    assert "- Checks: 4" in report
    assert "- Pass: 1" in report
    assert "- Fail: 1" in report
    assert "- Exempt: 1" in report
    assert "- Error: 1" in report
    assert "[example/first](https://github.com/example/first)" in report
    assert (
        "`agentic` | [Click here](https://example.com/agentic) | `agentic` | Medium"
        in report
    )
    assert "bad \\| marker found \\[link\\] \\*bold\\* \\<tag\\>" in report
    assert "``src/config`file.py:7`` — `api-key`" in report
    assert "3 additional location(s) omitted" in report
    assert "https://example.com/agentic" in report


def test_report_preserves_registry_and_configuration_order() -> None:
    second_rule = make_rule("second-rule")
    first_rule = make_rule("first-rule")
    config = ComplianceConfig(
        repositories=(
            RepositoryConfig(repository="example/zeta"),
            RepositoryConfig(repository="example/alpha"),
        )
    )
    results = (
        RuleResult("example/zeta", second_rule, ResultStatus.PASS, "ok"),
        RuleResult("example/zeta", first_rule, ResultStatus.PASS, "ok"),
        RuleResult("example/alpha", second_rule, ResultStatus.PASS, "ok"),
        RuleResult("example/alpha", first_rule, ResultStatus.PASS, "ok"),
    )

    report = generate_report(
        config,
        (second_rule, first_rule),
        results,
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    rules_section = report.split("## Rules", maxsplit=1)[1].split(
        "## Results", maxsplit=1
    )[0]
    summary_section = report.split("## Repository summary", maxsplit=1)[1].split(
        "## Rules", maxsplit=1
    )[0]
    assert rules_section.index("second-rule") < rules_section.index("first-rule")
    assert summary_section.index("example/zeta") < summary_section.index(
        "example/alpha"
    )


def test_empty_configuration_still_produces_complete_report() -> None:
    report = generate_report(
        ComplianceConfig(repositories=()),
        (),
        (),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert "_No repositories configured_" in report
    assert "_No rules configured_" in report
    assert "_No checks run_" in report
    assert "_No results._" in report
