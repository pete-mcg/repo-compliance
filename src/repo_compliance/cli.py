"""Command-line interface for repository compliance checks."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from repo_compliance.config import get_config
from repo_compliance.errors import ComplianceError
from repo_compliance.infrastructure.agentic.agent_framework import (
    AgentFrameworkEvaluator,
)
from repo_compliance.infrastructure.github.client import GitHubClient
from repo_compliance.report import build_report
from repo_compliance.rules.registry import RULE_IDS, RULES
from repo_compliance.runner import run_all_compliance_checks
from repo_compliance.settings import get_env_settings


class CliOptions(BaseModel):
    """Validated command-line paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config: Path
    output: Path


def main(argv: Sequence[str] | None = None) -> int:
    """Run checks, write the report, and return a process exit code."""
    try:
        options = _get_cli_options(argv)
        settings = get_env_settings()
        config = get_config(options.config, RULE_IDS)
        with GitHubClient(settings.github_token) as github:
            results = run_all_compliance_checks(
                config, github, RULES, AgentFrameworkEvaluator(settings)
            )
        report = build_report(config, RULES, results)
        options.output.write_text(report, encoding="utf-8")
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
    parser.add_argument("--config", type=Path, default=Path("config/repositories.yml"))
    parser.add_argument("--output", type=Path, default=Path("compliance-report.md"))
    arguments = parser.parse_args(argv)
    return CliOptions.model_validate(vars(arguments))
