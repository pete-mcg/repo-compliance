"""Load and validate repository configuration."""

import re
from pathlib import Path
from typing import Self

import yaml  # pyrefly: ignore [untyped-import]
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from repo_compliance.errors import ConfigError

OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,100}")


class ConfigModel(BaseModel):
    """Base settings shared by configuration models."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ExemptionConfig(ConfigModel):
    """One repository-specific rule exemption."""

    rule: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RepositoryConfig(ConfigModel):
    """One configured GitHub repository and its exemptions."""

    repository: str
    exemptions: tuple[ExemptionConfig, ...] = ()

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        """Reject values that are not an owner/name pair."""
        parts = value.split("/")
        if len(parts) != 2:
            raise ValueError("repository must use owner/name format")

        owner, name = parts
        if not OWNER_PATTERN.fullmatch(owner):
            raise ValueError("repository owner is invalid")
        if not REPOSITORY_PATTERN.fullmatch(name) or name in {".", ".."}:
            raise ValueError("repository name is invalid")
        return value

    @model_validator(mode="after")
    def reject_duplicate_exemptions(self) -> Self:
        """Reject repeated rule exemptions within a repository."""
        rule_ids = [exemption.rule for exemption in self.exemptions]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("repository contains duplicate exemptions")
        return self


class ComplianceConfig(ConfigModel):
    """Top-level repository compliance configuration."""

    repositories: tuple[RepositoryConfig, ...]

    @model_validator(mode="after")
    def reject_duplicate_repositories(self) -> Self:
        """Reject duplicate repositories using GitHub's case-insensitive names."""
        names = [item.repository.casefold() for item in self.repositories]
        if len(names) != len(set(names)):
            raise ValueError("configuration contains duplicate repositories")
        return self


def load_config(path: Path, rule_ids: frozenset[str]) -> ComplianceConfig:
    """Read YAML configuration and validate all repositories and exemptions."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"Could not read configuration '{path}'.") from error

    try:
        raw_config: object = yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise ConfigError(f"Configuration '{path}' is not valid YAML.") from error

    try:
        config = ComplianceConfig.model_validate(raw_config)
    except ValidationError as error:
        raise ConfigError(f"Configuration '{path}' is invalid: {error}") from error

    _validate_rule_ids(config, rule_ids, path)
    return config


def _validate_rule_ids(
    config: ComplianceConfig,
    rule_ids: frozenset[str],
    path: Path,
) -> None:
    for repository in config.repositories:
        for exemption in repository.exemptions:
            if exemption.rule not in rule_ids:
                raise ConfigError(
                    f"Configuration '{path}' uses unknown rule ID '{exemption.rule}'."
                )
