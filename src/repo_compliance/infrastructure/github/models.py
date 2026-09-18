"""Validated models for GitHub REST API responses."""

from pydantic import BaseModel, ConfigDict


class GitHubModel(BaseModel):
    """Base model for the response fields used by the checker."""

    model_config = ConfigDict(extra="ignore", frozen=True)


class GitHubRepository(GitHubModel):
    """GitHub repository response fields used during preflight."""

    id: int


class GitHubContent(GitHubModel):
    """GitHub repository content response fields used by file rules."""

    path: str
    type: str
