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


class AgentEvaluator(Protocol):
    """Reason about a local source ZIP using a supplied rule prompt."""

    def evaluate(self, snapshot_path: Path, prompt: str) -> RuleEvaluation:
        """Return a validated judgment or raise AgentError when unavailable."""


class GitHubApi(Protocol):
    """GitHub operations available to rules and the runner."""

    def ensure_accessible_repository(self, repository: str) -> None:
        """Ensure the repository is accessible and has valid API data."""

    def file_exists_on_main(self, repository: str, path: str) -> bool:
        """Return whether an exact file exists on the main branch."""

    def get_json_response(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: bool = False,
    ) -> object | None:
        """Return decoded JSON, optionally returning None when it is missing."""

    def download_source_snapshot_from_main(
        self, repository: str, destination: Path
    ) -> Path:
        """Stream the main branch source snapshot to a file and return its path."""


@dataclass(frozen=True)
class RuleContext:
    """Inputs supplied to every rule check."""

    repository: str
    github: GitHubApi
    source_snapshot_path: Path | None = None
    agent_evaluator: AgentEvaluator | None = None


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
    requires_source_snapshot: bool = False


@dataclass(frozen=True)
class RuleResult:
    """Final result for one rule on one repository."""

    repository: str
    rule: RuleDefinition
    status: ResultStatus
    message: str
    evidence: tuple[Evidence, ...] = ()
    omitted_evidence_count: int = 0
