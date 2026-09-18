"""Expected application errors."""


class ComplianceError(Exception):
    """Base class for expected compliance checker failures."""


class ConfigError(ComplianceError):
    """Raised when repository configuration is invalid."""


class GitHubError(ComplianceError):
    """Raised when GitHub data cannot be fetched or validated."""


class SourceSnapshotError(ComplianceError):
    """Raised when a downloaded source snapshot cannot be inspected."""


class AgentError(ComplianceError):
    """Raised when an agent cannot provide a reliable rule judgment."""


class CliError(ComplianceError):
    """Raised when command-line setup is invalid."""
