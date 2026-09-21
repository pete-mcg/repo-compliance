"""Load and validate runtime settings from the environment and .env."""

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from repo_compliance.errors import CliError


class Settings(BaseSettings):
    """Required GitHub credentials and Azure OpenAI routing."""

    model_config = SettingsConfigDict(
        env_file=".env",
        frozen=True,
        extra="ignore",
        str_strip_whitespace=True,
        hide_input_in_errors=True,
    )

    github_token: str = Field(alias="GITHUB_TOKEN", min_length=1, repr=False)
    endpoint: str = Field(
        alias="AZURE_OPENAI_ENDPOINT",
        pattern=r"^https://[a-z0-9][a-z0-9-]*\.openai\.azure\.com/?$",
    )
    deployment: str = Field(
        alias="AZURE_OPENAI_DEPLOYMENT", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$"
    )
    api_version: str = Field(
        alias="AZURE_OPENAI_API_VERSION", pattern=r"^\d{4}-\d{2}-\d{2}(-preview)?$"
    )


def get_settings() -> Settings:
    """Read settings and report all validation errors without their input values."""
    try:
        return Settings()
    except ValidationError as error:
        raise CliError(f"Invalid runtime settings:\n{error}") from error
