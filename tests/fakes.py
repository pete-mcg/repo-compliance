from dataclasses import dataclass, field
from pathlib import Path

from repo_compliance.errors import GitHubError


@dataclass
class FakeGitHub:
    files: set[str] = field(default_factory=set)
    json_responses: dict[str, object | None] = field(default_factory=dict)
    source_snapshot_bytes: bytes = b"source snapshot"
    preflight_error_repositories: set[str] = field(default_factory=set)
    source_snapshot_error_repositories: set[str] = field(default_factory=set)
    preflight_calls: list[str] = field(default_factory=list)
    source_snapshot_calls: list[str] = field(default_factory=list)
    file_calls: list[tuple[str, str]] = field(default_factory=list)
    json_calls: list[tuple[str, dict[str, str | int] | None, bool]] = field(
        default_factory=list
    )

    def ensure_accessible_repository(self, repository: str) -> None:
        self.preflight_calls.append(repository)
        if repository in self.preflight_error_repositories:
            raise GitHubError("repository is unavailable")

    def file_exists_on_main(self, repository: str, path: str) -> bool:
        self.file_calls.append((repository, path))
        return path in self.files

    def get_json_response(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: bool = False,
    ) -> object | None:
        self.json_calls.append((resource, params, missing_ok))
        return self.json_responses.get(resource)

    def download_source_snapshot_from_main(
        self, repository: str, destination: Path
    ) -> Path:
        self.source_snapshot_calls.append(repository)
        if repository in self.source_snapshot_error_repositories:
            raise GitHubError("source snapshot is unavailable")
        destination.write_bytes(self.source_snapshot_bytes)
        return destination
