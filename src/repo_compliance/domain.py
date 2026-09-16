"""Core immutable types shared by rules, runner, and reporting."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class RuleCategory(StrEnum):
    """Method used to evaluate a rule."""

    DETERMINISTIC = "deterministic"
    AGENTIC = "agentic"


class Confidence(StrEnum):
    """Expected confidence in a rule result."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResultStatus(StrEnum):
    """Outcome of one repository rule check."""

    PASS = "pass"
    FAIL = "fail"
    EXEMPT = "exempt"
    ERROR = "error"


class GitHubApi(Protocol):
    """GitHub operations available to rules and the runner."""

    def ensure_main_branch(self, repository: str) -> str:
        """Return the accessible main branch name."""

    def active_main_rule_types(self, repository: str) -> frozenset[str]:
        """Return active ruleset rule types for the main branch."""

    def classic_allow_deletions(self, repository: str) -> bool | None:
        """Return classic branch deletion setting, or None if unprotected."""

    def file_exists(self, repository: str, path: str) -> bool:
        """Return whether an exact file exists on the main branch."""

    def has_critical_dependabot_alerts(self, repository: str) -> bool:
        """Return whether a repository has any open Critical alert."""

    def download_main_archive(self, repository: str, destination: Path) -> Path:
        """Stream the main branch ZIP archive to a file and return its path."""


@dataclass(frozen=True)
class Evidence:
    """Safe location metadata supporting a rule result."""

    path: str
    line: int
    marker: str


@dataclass(frozen=True)
class RuleEvaluation:
    """Raw evaluation returned by a rule check."""

    passed: bool
    message: str
    evidence: tuple[Evidence, ...] = ()
    omitted_evidence_count: int = 0


@dataclass(frozen=True)
class RuleContext:
    """Inputs supplied to every rule check."""

    repository: str
    github: GitHubApi
    archive_path: Path | None = None


RuleCheck = Callable[[RuleContext], RuleEvaluation]


@dataclass(frozen=True)
class RuleDefinition:
    """Immutable rule metadata and its check function."""

    id: str
    title: str
    description: str
    category: RuleCategory
    confidence: Confidence
    documentation_url: str
    check: RuleCheck
    requires_archive: bool = False


@dataclass(frozen=True)
class RuleResult:
    """Final result for one rule on one repository."""

    repository: str
    rule: RuleDefinition
    status: ResultStatus
    message: str
    evidence: tuple[Evidence, ...] = ()
    omitted_evidence_count: int = 0
