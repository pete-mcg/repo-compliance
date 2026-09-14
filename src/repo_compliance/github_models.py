"""Validated models for GitHub REST API responses."""

from pydantic import BaseModel, ConfigDict


class GitHubModel(BaseModel):
    """Base model for the response fields used by the checker."""

    model_config = ConfigDict(extra="ignore", frozen=True)


class GitHubBranch(GitHubModel):
    """GitHub branch response fields used during preflight."""

    name: str


class GitHubRule(GitHubModel):
    """One active GitHub repository rule."""

    type: str


class GitHubEnabledSetting(GitHubModel):
    """GitHub setting represented by an enabled flag."""

    enabled: bool


class GitHubBranchProtection(GitHubModel):
    """Classic branch protection fields used by the deletion rule."""

    allow_deletions: GitHubEnabledSetting


class GitHubContent(GitHubModel):
    """GitHub repository content response fields used by file rules."""

    path: str
    type: str


class GitHubDependabotAlert(GitHubModel):
    """Minimal validated Dependabot alert response."""

    number: int
