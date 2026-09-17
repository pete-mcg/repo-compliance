"""Render compliance results as a stable Markdown report."""

import re
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime

from repo_compliance.config import ComplianceConfig
from repo_compliance.domain import ResultStatus, RuleDefinition, RuleResult


def build_report(
    config: ComplianceConfig,
    rules: Sequence[RuleDefinition],
    results: Sequence[RuleResult],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Build a compliance report in Markdown."""
    timestamp = generated_at or datetime.now(UTC)
    sections = [
        "# Repository Compliance Report",
        f"Generated at `{_format_timestamp_as_utc(timestamp)}`",
        _build_totals_section(config, results),
        _build_repository_summary_section(config, results),
        _build_rules_section(rules),
        _build_results_table_section(results),
        _build_details_section(results),
    ]
    return "\n\n".join(sections) + "\n"


def _build_totals_section(
    config: ComplianceConfig, results: Sequence[RuleResult]
) -> str:
    counts = Counter(result.status for result in results)
    return "\n".join(
        (
            "## Totals",
            "",
            f"- Repositories: {len(config.repositories)}",
            f"- Checks: {len(results)}",
            f"- Pass: {counts[ResultStatus.PASS]}",
            f"- Fail: {counts[ResultStatus.FAIL]}",
            f"- Exempt: {counts[ResultStatus.EXEMPT]}",
            f"- Error: {counts[ResultStatus.ERROR]}",
        )
    )


def _build_repository_summary_section(
    config: ComplianceConfig,
    results: Sequence[RuleResult],
) -> str:
    lines = [
        "## Repository summary",
        "",
        "| Repository | Pass | Fail | Exempt | Error |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    if not config.repositories:
        lines.append("| _No repositories configured_ | 0 | 0 | 0 | 0 |")
        return "\n".join(lines)

    for repository in config.repositories:
        repository_results = [
            result for result in results if result.repository == repository.repository
        ]
        counts = Counter(result.status for result in repository_results)
        link = _build_repository_hyperlink(repository.repository)
        lines.append(
            f"| {link} "
            f"| {counts[ResultStatus.PASS]} "
            f"| {counts[ResultStatus.FAIL]} "
            f"| {counts[ResultStatus.EXEMPT]} "
            f"| {counts[ResultStatus.ERROR]} |"
        )
    return "\n".join(lines)


def _build_rules_section(rules: Sequence[RuleDefinition]) -> str:
    lines = [
        "## Rules",
        "",
        "| Rule | Documentation | Category | Confidence | Standard |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not rules:
        lines.append("| _None_ | _None_ | _None_ | _None_ | _No rules configured_ |")
        return "\n".join(lines)

    for rule in rules:
        lines.append(
            f"| `{rule.id}` "
            f"| [Click here]({rule.documentation_url}) "
            f"| `{rule.category.value}` "
            f"| {rule.confidence.value.title()} "
            f"| {_format_text_for_markdown_table(rule.description)} |"
        )
    return "\n".join(lines)


def _build_results_table_section(results: Sequence[RuleResult]) -> str:
    lines = [
        "## Results",
        "",
        "| Repository | Rule | Category | Confidence | Status | Details |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if not results:
        lines.append("| _None_ | _None_ | _None_ | _None_ | _None_ | _No checks run_ |")
        return "\n".join(lines)

    for result in results:
        lines.append(
            f"| {_build_repository_hyperlink(result.repository)} "
            f"| `{result.rule.id}` "
            f"| `{result.rule.category.value}` "
            f"| {result.rule.confidence.value.title()} "
            f"| **{result.status.value.upper()}** "
            f"| {_format_text_for_markdown_table(result.message)} |"
        )
    return "\n".join(lines)


def _build_details_section(results: Sequence[RuleResult]) -> str:
    lines = ["## Details"]
    if not results:
        lines.extend(("", "_No results._"))
        return "\n".join(lines)

    for result in results:
        lines.extend(
            [
                "",
                f"### {_format_plain_markdown_text(result.repository)} / `{result.rule.id}`",
                "",
                f"- Status: **{result.status.value.upper()}**",
                f"- Details: {_format_plain_markdown_text(result.message)}",
                f"- Guidance: [{_format_plain_markdown_text(result.rule.title)}]({result.rule.documentation_url})",
            ]
        )
        if result.evidence:
            lines.append("- Evidence:")
            lines.extend(_build_evidence_list(result))
        if result.omitted_evidence_count:
            lines.append(
                f"- {result.omitted_evidence_count} additional location(s) omitted."
            )
    return "\n".join(lines)


def _build_evidence_list(result: RuleResult) -> list[str]:
    return [
        f"  - {_format_markdown_code_span(f'{item.path}:{item.line}')} — {_format_markdown_code_span(item.marker)}"
        for item in result.evidence
    ]


def _build_repository_hyperlink(repository: str) -> str:
    return f"[{repository}](https://github.com/{repository})"


def _format_text_for_markdown_table(value: str) -> str:
    # Escapes | for Markdown tables
    return _format_plain_markdown_text(value).replace("|", "\\|")


def _format_plain_markdown_text(value: str) -> str:
    single_line = value.replace("\r", " ").replace("\n", " ")
    # Escapes \, `, *, _, [, ], <, >, and ~ for Markdown
    return re.sub(r"([\\`*_\[\]<>~])", r"\\\1", single_line)


def _format_markdown_code_span(value: str) -> str:
    # Escapes ` for Markdown code spans, and wraps the value in backticks
    single_line = value.replace("\r", " ").replace("\n", " ")
    backtick_runs = re.findall(r"`+", single_line)
    fence = "`" * (max(map(len, backtick_runs), default=0) + 1)
    padding = " " if single_line.startswith("`") or single_line.endswith("`") else ""
    return f"{fence}{padding}{single_line}{padding}{fence}"


def _format_timestamp_as_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
