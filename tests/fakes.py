from dataclasses import dataclass, field
from pathlib import Path

from repo_compliance.errors import GitHubError


@dataclass
class FakeGitHub:
    rule_types: frozenset[str] = frozenset()
    allow_deletions: bool | None = None
    files: set[str] = field(default_factory=set)
    critical_alerts: bool = False
    archive_bytes: bytes = b"archive"
    preflight_error_repositories: set[str] = field(default_factory=set)
    archive_error_repositories: set[str] = field(default_factory=set)
    preflight_calls: list[str] = field(default_factory=list)
    archive_calls: list[str] = field(default_factory=list)
    file_calls: list[tuple[str, str]] = field(default_factory=list)
    classic_calls: int = 0

    def get_main_branch(self, repository: str) -> str:
        self.preflight_calls.append(repository)
        if repository in self.preflight_error_repositories:
            raise GitHubError("main is unavailable")
        return "main"

    def get_active_main_rule_types(self, repository: str) -> frozenset[str]:
        return self.rule_types

    def get_classic_deletion_setting(self, repository: str) -> bool | None:
        self.classic_calls += 1
        return self.allow_deletions

    def has_file(self, repository: str, path: str) -> bool:
        self.file_calls.append((repository, path))
        return path in self.files

    def has_critical_dependabot_alerts(self, repository: str) -> bool:
        return self.critical_alerts

    def get_main_archive(self, repository: str, destination: Path) -> Path:
        self.archive_calls.append(repository)
        if repository in self.archive_error_repositories:
            raise GitHubError("archive is unavailable")
        destination.write_bytes(self.archive_bytes)
        return destination
