"""Load and validate repository compliance configuration."""

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
    """Shared settings for configuration models."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ExemptionConfig(ConfigModel):
    """A rule exemption for one repository."""

    rule: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RepositoryConfig(ConfigModel):
    """A GitHub repository and its rule exemptions."""

    repository: str
    exemptions: tuple[ExemptionConfig, ...] = ()

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, value: str) -> str:
        """Ensure the repository uses owner/name format and matches GitHub naming rules."""
        parts = value.split("/")
        if len(parts) != 2:
            raise ValueError("repository must use owner/name format")

        owner, name = parts
        if not OWNER_PATTERN.fullmatch(owner):
            raise ValueError("repository owner is invalid")
        if not REPOSITORY_PATTERN.fullmatch(name):
            raise ValueError("repository name is invalid")
        return value

    @model_validator(mode="after")
    def validate_unique_exemptions(self) -> Self:
        """Ensure a repository does not exempt the same rule twice."""
        rule_ids = [exemption.rule for exemption in self.exemptions]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("repository contains duplicate exemptions")
        return self


class ComplianceConfig(ConfigModel):
    """Configuration for all repositories to check."""

    repositories: tuple[RepositoryConfig, ...]

    @model_validator(mode="after")
    def validate_unique_repositories(self) -> Self:
        """Ensure each repository appears only once, ignoring case."""
        names = [item.repository.casefold() for item in self.repositories]
        if len(names) != len(set(names)):
            raise ValueError("configuration contains duplicate repositories")
        return self


def load_config(path: Path, rule_ids: frozenset[str]) -> ComplianceConfig:
    """Load and validate configuration from a YAML file."""
    source = _read_config_source(path)
    raw_config = _parse_yaml(source, path)
    config = _validate_config(raw_config, path)
    _validate_exemption_rule_ids(config, rule_ids, path)
    return config


def _read_config_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"Could not read configuration '{path}'.") from error


def _parse_yaml(source: str, path: Path) -> object:
    try:
        return yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise ConfigError(f"Configuration '{path}' is not valid YAML.") from error


def _validate_config(raw_config: object, path: Path) -> ComplianceConfig:
    try:
        return ComplianceConfig.model_validate(raw_config)
    except ValidationError as error:
        raise ConfigError(f"Configuration '{path}' is invalid: {error}") from error


def _validate_exemption_rule_ids(
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
