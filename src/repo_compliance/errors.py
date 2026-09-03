"""Expected application errors."""


class ComplianceError(Exception):
    """Base class for expected compliance checker failures."""


class ConfigError(ComplianceError):
    """Raised when repository configuration is invalid."""


class GitHubError(ComplianceError):
    """Raised when GitHub data cannot be fetched or validated."""


class ArchiveError(ComplianceError):
    """Raised when a downloaded repository archive cannot be inspected."""


class CliError(ComplianceError):
    """Raised when command-line setup is invalid."""
