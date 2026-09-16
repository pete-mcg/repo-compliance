"""Render compliance results as a stable Markdown report."""

import re
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime

from repo_compliance.config import ComplianceConfig
from repo_compliance.domain import ResultStatus, RuleDefinition, RuleResult


def generate_report(
    config: ComplianceConfig,
    rules: Sequence[RuleDefinition],
    results: Sequence[RuleResult],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Build a complete Markdown compliance report."""
    timestamp = generated_at or datetime.now(UTC)
    sections = [
        "# Repository Compliance Report",
        f"Generated at `{_utc_timestamp(timestamp)}`.",
        _totals(config, results),
        _repository_summary(config, results),
        _rule_catalogue(rules),
        _result_table(results),
        _details(results),
    ]
    return "\n\n".join(sections) + "\n"


def _totals(config: ComplianceConfig, results: Sequence[RuleResult]) -> str:
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


def _repository_summary(
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
        link = _repository_link(repository.repository)
        lines.append(
            f"| {link} | {counts[ResultStatus.PASS]} | {counts[ResultStatus.FAIL]} "
            f"| {counts[ResultStatus.EXEMPT]} | {counts[ResultStatus.ERROR]} |"
        )
    return "\n".join(lines)


def _rule_catalogue(rules: Sequence[RuleDefinition]) -> str:
    lines = [
        "## Rules",
        "",
        "| Rule | Documentation | Category | Confidence | Standard |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rule in rules:
        lines.append(
            f"| `{rule.id}` | [Click here]({rule.documentation_url}) | "
            f"`{rule.category.value}` | {rule.confidence.value.title()} | "
            f"{_table_text(rule.description)} |"
        )
    return "\n".join(lines)


def _result_table(results: Sequence[RuleResult]) -> str:
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
            f"| {_repository_link(result.repository)} | `{result.rule.id}` | "
            f"`{result.rule.category.value}` | {result.rule.confidence.value.title()} | "
            f"**{result.status.value.upper()}** | "
            f"{_table_text(result.message)} |"
        )
    return "\n".join(lines)


def _details(results: Sequence[RuleResult]) -> str:
    lines = ["## Details"]
    if not results:
        lines.extend(("", "_No results._"))
        return "\n".join(lines)

    for result in results:
        lines.extend(
            (
                "",
                f"### {_plain_text(result.repository)} / `{result.rule.id}`",
                "",
                f"- Status: **{result.status.value.upper()}**",
                f"- Details: {_plain_text(result.message)}",
                (
                    f"- Guidance: [{_plain_text(result.rule.title)}]"
                    f"({result.rule.documentation_url})"
                ),
            )
        )
        if result.evidence:
            lines.append("- Evidence:")
            lines.extend(_evidence_lines(result))
        if result.omitted_evidence_count:
            lines.append(
                f"- {result.omitted_evidence_count} additional location(s) omitted."
            )
    return "\n".join(lines)


def _evidence_lines(result: RuleResult) -> list[str]:
    return [
        f"  - {_code_span(f'{item.path}:{item.line}')} — {_code_span(item.marker)}"
        for item in result.evidence
    ]


def _repository_link(repository: str) -> str:
    return f"[{repository}](https://github.com/{repository})"


def _table_text(value: str) -> str:
    return _plain_text(value).replace("|", "\\|")


def _plain_text(value: str) -> str:
    single_line = value.replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_\[\]<>~])", r"\\\1", single_line)


def _code_span(value: str) -> str:
    single_line = value.replace("\r", " ").replace("\n", " ")
    backtick_runs = re.findall(r"`+", single_line)
    fence = "`" * (max(map(len, backtick_runs), default=0) + 1)
    padding = " " if single_line.startswith("`") or single_line.endswith("`") else ""
    return f"{fence}{padding}{single_line}{padding}{fence}"


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
