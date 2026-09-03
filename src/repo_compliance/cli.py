"""Command-line interface for repository compliance checks."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from repo_compliance.config import get_config
from repo_compliance.errors import CliError, ComplianceError
from repo_compliance.github import GitHubClient
from repo_compliance.report import compose_report
from repo_compliance.rules.registry import RULE_IDS, RULES
from repo_compliance.runner import get_compliance_results


class CliOptions(BaseModel):
    """Validated command-line paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config: Path
    output: Path


def main(argv: Sequence[str] | None = None) -> int:
    """Run checks, write the report, and return a process exit code."""
    try:
        options = _get_cli_options(argv)
        token = _get_github_token()
        _handle_compliance_check(options, token)
    except ComplianceError as error:
        print(f"repo-compliance: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"repo-compliance: Could not write report ({error}).", file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001  # Checker bugs must fail the command.
        print(
            f"repo-compliance: Unexpected {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    return 0


def _get_cli_options(argv: Sequence[str] | None) -> CliOptions:
    parser = argparse.ArgumentParser(
        description="Check configured GitHub repositories for compliance.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/repositories.yml"),
    )
    parser.add_argument("--output", type=Path, default=Path("compliance-report.md"))
    arguments = parser.parse_args(argv)
    return CliOptions.model_validate(vars(arguments))


def _get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise CliError("GITHUB_TOKEN is required.")
    return token


def _handle_compliance_check(options: CliOptions, token: str) -> None:
    config = get_config(options.config, RULE_IDS)
    with GitHubClient(token) as github:
        results = get_compliance_results(config, github, RULES)
    report = compose_report(config, RULES, results)
    options.output.write_text(report, encoding="utf-8")
