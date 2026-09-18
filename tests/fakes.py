from dataclasses import dataclass, field
from pathlib import Path

from repo_compliance.errors import GitHubError


@dataclass
class FakeGitHub:
    files: set[str] = field(default_factory=set)
    json_responses: dict[str, object | None] = field(default_factory=dict)
    archive_bytes: bytes = b"archive"
    preflight_error_repositories: set[str] = field(default_factory=set)
    archive_error_repositories: set[str] = field(default_factory=set)
    preflight_calls: list[str] = field(default_factory=list)
    archive_calls: list[str] = field(default_factory=list)
    file_calls: list[tuple[str, str]] = field(default_factory=list)
    json_calls: list[tuple[str, dict[str, str | int] | None, bool]] = field(
        default_factory=list
    )

    def ensure_accessible_respository(self, repository: str) -> None:
        self.preflight_calls.append(repository)
        if repository in self.preflight_error_repositories:
            raise GitHubError("repository is unavailable")

    def file_exists(self, repository: str, path: str) -> bool:
        self.file_calls.append((repository, path))
        return path in self.files

    def get_json(
        self,
        resource: str,
        *,
        params: dict[str, str | int] | None = None,
        missing_ok: bool = False,
    ) -> object | None:
        self.json_calls.append((resource, params, missing_ok))
        return self.json_responses.get(resource)

    def download_archive_from_main(self, repository: str, destination: Path) -> Path:
        self.archive_calls.append(repository)
        if repository in self.archive_error_repositories:
            raise GitHubError("archive is unavailable")
        destination.write_bytes(self.archive_bytes)
        return destination
