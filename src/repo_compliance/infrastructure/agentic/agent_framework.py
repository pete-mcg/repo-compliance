"""Evaluate local source with Microsoft Agent Framework, Azure, and Serena."""

import asyncio
import subprocess
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import yaml  # pyrefly: ignore [untyped-import]
from agent_framework import Agent, MCPStdioTool
from agent_framework.exceptions import AgentFrameworkException
from agent_framework_openai import (
    OpenAIChatCompletionClient,
    OpenAIChatCompletionOptions,
)
from azure.core.exceptions import ClientAuthenticationError
from azure.identity.aio import AzureCliCredential, get_bearer_token_provider
from mcp.shared.exceptions import McpError
from openai import APIError, AsyncAzureOpenAI, DefaultAsyncHttpxClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from repo_compliance.domain import Evidence, RuleEvaluation
from repo_compliance.errors import AgentError
from repo_compliance.infrastructure.source.source_snapshot import (
    extracted_source_snapshot,
    safe_relative_path,
)

EVALUATION_TIMEOUT_SECONDS = 120
SERENA_IMAGE = (
    "ghcr.io/oraios/serena:1.7.0@"
    "sha256:6c9459e4246a39c9deaa4f23fb05a526ac6e237b24c8e84a927a098fa1ab6730"
)
# Full Serena Tools catalogue: https://oraios.github.io/serena/01-about/035_tools.html
# Runtime list: tests/integration/test_agent_integration.py:list_tools()
SERENA_TOOLS = ("list_dir", "read_file", "find_file", "search_for_pattern")


class AzureOpenAISettings(BaseSettings):
    """Required, explicitly approved Azure routing from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="AZURE_OPENAI_",
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )

    endpoint: str = Field(pattern=r"^https://[a-z0-9][a-z0-9-]*\.openai\.azure\.com/?$")
    deployment: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    api_version: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}(-preview)?$")


class AgentVerdict(StrEnum):
    """Judgments accepted from the model."""

    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


class AgentEvidence(BaseModel):
    """Validated location metadata, without source excerpts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Azure structured outputs do not support JSON schema limits such as
    # minLength, maxLength, or minimum, which Field constraints would generate.
    # Descriptions are included in the JSON schema provided to the model;
    # validators enforce them locally AFTER the response is generated.
    path: str = Field(
        description="Evidence path must be relative to the repository.",
        examples=[".github/workflows/ci.yml", "Taskfile.yml", "scripts/test.sh"],
    )
    line: int = Field(
        strict=True,
        description="Source line number must be one-based (1 or greater).",
        examples=[5, 12, 24],
    )
    marker: str = Field(
        description="Short, non-empty evidence label containing 1 to 80 characters.",
        examples=["pull-request-trigger", "test-task", "run-tests"],
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        """Keep evidence paths relative to the repository."""
        return str(safe_relative_path(value))

    @field_validator("line")
    @classmethod
    def validate_line(cls, value: int) -> int:
        """Require one-based source line numbers."""
        if value < 1:
            raise ValueError("Evidence line must be positive.")
        return value

    @field_validator("marker")
    @classmethod
    def validate_marker(cls, value: str) -> str:
        """Require a short, non-empty evidence label."""
        if not value or len(value) > 80:
            raise ValueError("Evidence marker must contain 1 to 80 characters.")
        return value


class AgentStructuredResponse(BaseModel):
    """Structured response requested from the Azure deployment."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: AgentVerdict = Field(examples=["pass", "fail", "uncertain"])
    explanation: str = Field(
        description="Explanation must contain 1 to 600 characters.",
        examples=[
            "CI tests run on pull requests targeting main.",
            "The workflow runs only on pushes, not pull requests.",
            "The referenced test script is missing, so CI cannot be verified.",
        ],
    )
    evidence: list[AgentEvidence] = Field(
        examples=[
            [
                {
                    "path": ".github/workflows/ci.yml",
                    "line": 5,
                    "marker": "pull-request-trigger",
                }
            ],
            [
                {
                    "path": "Taskfile.yml",
                    "line": 12,
                    "marker": "test-task",
                }
            ],
            [
                {
                    "path": "scripts/test.sh",
                    "line": 24,
                    "marker": "run-tests",
                }
            ],
        ]
    )

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        """Require a short, non-empty explanation."""
        if not value or len(value) > 600:
            raise ValueError("Explanation must contain 1 to 600 characters.")
        return value


class AgentFrameworkEvaluator:
    """Keep settings, Docker, and Azure startup lazy until a rule evaluates."""

    def evaluate(self, snapshot_path: Path, prompt: str) -> RuleEvaluation:
        """Run one isolated evaluation and translate expected integration failures."""
        try:
            settings = AzureOpenAISettings()
        except ValidationError as error:
            raise AgentError(
                "Configure valid AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, "
                "and AZURE_OPENAI_API_VERSION."
            ) from error
        try:
            return _evaluate_snapshot(snapshot_path, prompt, settings)
        except TimeoutError as error:
            raise AgentError(
                f"Agent evaluation exceeded {EVALUATION_TIMEOUT_SECONDS} seconds."
            ) from error
        except (
            AgentFrameworkException,
            ClientAuthenticationError,
            APIError,
            McpError,
            OSError,
            ValidationError,
        ) as error:
            raise AgentError(
                f"Agent evaluation failed ({type(error).__name__})."
            ) from error


def _evaluate_snapshot(
    snapshot_path: Path, prompt: str, settings: AzureOpenAISettings
) -> RuleEvaluation:
    with (
        extracted_source_snapshot(snapshot_path) as repository,
        TemporaryDirectory(prefix="repo-compliance-serena-") as temporary_state,
    ):
        state = Path(temporary_state)
        write_serena_configuration(state)
        container_name = f"repo-compliance-{uuid4().hex}"
        try:
            output = asyncio.run(
                _run_agent(repository, state, container_name, settings, prompt)
            )
        finally:
            _remove_container(container_name)
        return _to_evaluation(output)


async def _run_agent(
    repository: Path,
    state: Path,
    container_name: str,
    settings: AzureOpenAISettings,
    prompt: str,
) -> object:
    async with (
        asyncio.timeout(EVALUATION_TIMEOUT_SECONDS),
        AzureCliCredential() as credential,
        create_azure_client(settings, credential) as azure_client,
        create_serena_tool(repository, state, container_name) as serena,
    ):
        client = OpenAIChatCompletionClient(
            model=settings.deployment, async_client=azure_client
        )
        options: OpenAIChatCompletionOptions = {
            "allow_multiple_tool_calls": False,
            "store": False,
        }
        agent = Agent(
            client=client,
            name="repository-compliance",
            tools=[serena],
            default_options=options,
        )
        response = await agent.run(
            prompt, options={"response_format": AgentStructuredResponse}
        )
        return response.value


def create_azure_client(
    settings: AzureOpenAISettings, credential: AzureCliCredential
) -> AsyncAzureOpenAI:
    """Use Entra auth and explicit routing, with no redirects or proxy discovery."""
    return AsyncAzureOpenAI(
        azure_endpoint=settings.endpoint,
        azure_deployment=settings.deployment,
        api_version=settings.api_version,
        azure_ad_token_provider=get_bearer_token_provider(
            # Azure's inherited __aenter__ annotation disagrees with its protocol.
            credential,  # pyrefly: ignore[bad-argument-type]
            "https://cognitiveservices.azure.com/.default",
        ),
        http_client=DefaultAsyncHttpxClient(follow_redirects=False, trust_env=False),
        max_retries=0,
        timeout=EVALUATION_TIMEOUT_SECONDS,
    )


def create_serena_tool(
    repository: Path, state: Path, container_name: str
) -> MCPStdioTool:
    """Expose only local file tools through a locked-down Docker stdio process."""
    return MCPStdioTool(
        name="repository-files",
        command="docker",
        args=serena_docker_arguments(repository, state, container_name),
        allowed_tools=SERENA_TOOLS,
        load_prompts=False,
        request_timeout=30,
    )


def serena_docker_arguments(
    repository: Path, state: Path, container_name: str
) -> list[str]:
    """Keep the replaceable MCP server launch settings in one place."""
    return [
        "run",
        "--rm",
        "-i",
        "--init",
        "--pull",
        "never",
        "--name",
        container_name,
        "--read-only",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--mount",
        f"type=bind,src={repository.resolve()},dst=/repository,readonly",
        "--mount",
        f"type=bind,src={state.resolve()},dst=/state",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--env",
        "SERENA_HOME=/state",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--entrypoint",
        "/workspaces/serena/.venv/bin/serena",
        SERENA_IMAGE,
        "start-mcp-server",
        "--transport",
        "stdio",
        "--project",
        "/repository",
        "--context",
        "/state/context.yml",
    ]


def write_serena_configuration(state: Path) -> None:
    """Precreate separate project state so repository Serena config is never loaded."""
    project_state = state / "project"
    project_state.mkdir()
    configurations: dict[Path, dict[str, str | bool | int | list[str] | None]] = {
        state / "serena_config.yml": {
            "web_dashboard": False,
            "web_dashboard_open_on_launch": False,
            "gui_log_window": False,
            "log_level": 40,
            "token_count_estimator": "CHAR_COUNT",
            "project_serena_folder_location": "/state/project",
            "trusted_project_path_patterns": [],
            "projects": [],
            "base_modes": [],
            "default_modes": [],
            "fixed_tools": list(SERENA_TOOLS),
        },
        project_state / "project.yml": {
            "project_name": "repository",
            "language_servers": [],
            "read_only": True,
            "ignore_all_files_in_gitignore": False,
            "initial_prompt": "",
            "activation_command": None,
        },
        state / "context.yml": {
            "name": "compliance",
            "prompt": "",
            "single_project": True,
        },
    }
    for path, configuration in configurations.items():
        path.write_text(yaml.safe_dump(configuration), encoding="utf-8")


def _remove_container(container_name: str) -> None:
    try:
        result = subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        # Startup already reports missing Docker; there is no container to remove.
        return
    except subprocess.TimeoutExpired as error:
        raise AgentError("Docker container cleanup timed out.") from error
    if result.returncode != 0 and "No such container" not in result.stderr:
        raise AgentError("Could not remove the agent's Docker container.")


def _to_evaluation(output: object) -> RuleEvaluation:
    result = AgentStructuredResponse.model_validate(output)
    if result.verdict is AgentVerdict.UNCERTAIN:
        raise AgentError(f"Agent could not judge: {result.explanation}")
    if result.verdict is AgentVerdict.PASS and not result.evidence:
        raise AgentError("Agent returned a pass without supporting evidence.")
    evidence = tuple(
        Evidence(item.path, item.line, item.marker) for item in result.evidence
    )
    return RuleEvaluation(
        result.verdict is AgentVerdict.PASS, result.explanation, evidence
    )
