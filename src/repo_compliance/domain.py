"""Core immutable types shared by rules, runner, and reporting."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from repo_compliance.ports import AgentEvaluator, GitHubApi


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
