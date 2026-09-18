"""Contracts for external capabilities needed by the checker."""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from repo_compliance.domain import RuleEvaluation


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
