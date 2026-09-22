"""Command-line interface for repository compliance checks."""

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CliOptions:
    """Paths supplied to the command-line interface."""

    config: Path
    output: Path


def main(argv: Sequence[str] | None = None) -> int:
    """Run checks, write the report, and return a process exit code."""
    try:
        options = _get_cli_options(argv)
        _configure_logging()
        settings = get_env_settings()
        config = get_config(options.config, RULE_IDS)
        with GitHubClient(settings.github_token) as github:
            results = run_all_compliance_checks(
                config, github, RULES, AgentFrameworkEvaluator(settings)
            )
        report = build_report(config, RULES, results)
        options.output.write_text(report, encoding="utf-8")
        logger.info("Report written to %s", options.output)
    except ComplianceError as error:
        logger.error("%s", error)
        return 1
    except OSError as error:
        logger.error("Could not write report (%s).", error)
        return 1
    except Exception as error:  # Checker bugs must fail the command.
        logger.exception("Unexpected %s", type(error).__name__)
        return 1
    return 0


def _configure_logging() -> None:
    # Keep dependency logs (such as httpcore and httpx) at WARNING and above,
    # while enabling DEBUG messages and timings for our checker.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("repo_compliance").setLevel(logging.DEBUG)


def _get_cli_options(argv: Sequence[str] | None) -> CliOptions:
    parser = argparse.ArgumentParser(
        description="Check configured GitHub repositories for compliance.",
    )
    parser.add_argument("--config", type=Path, default=Path("config/repositories.yml"))
    parser.add_argument("--output", type=Path, default=Path("compliance-report.md"))
    arguments = parser.parse_args(argv)
    return CliOptions(config=arguments.config, output=arguments.output)
