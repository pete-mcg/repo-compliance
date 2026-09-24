"""Evaluate local source with Microsoft Agent Framework, Azure, and Serena."""

import asyncio
import subprocess
from enum import StrEnum
from importlib.resources import files
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

from repo_compliance.domain import Evidence, RuleEvaluation
from repo_compliance.errors import AgentError
from repo_compliance.infrastructure.source.source_snapshot import (
    extracted_source_snapshot,
    safe_relative_path,
)
from repo_compliance.settings import Settings

EVALUATION_TIMEOUT_SECONDS = 120
MCP_REQUEST_TIMEOUT_SECONDS = 30
DOCKER_CLEANUP_TIMEOUT_SECONDS = 10
MAX_EVIDENCE_DESCRIPTION_LENGTH = 200
MAX_EXPLANATION_LENGTH = 1000
SERENA_IMAGE = (
    "ghcr.io/oraios/serena:1.7.0@"
    "sha256:6c9459e4246a39c9deaa4f23fb05a526ac6e237b24c8e84a927a098fa1ab6730"
)
# Full Serena Tools catalogue: https://oraios.github.io/serena/01-about/035_tools.html
# Runtime list: tests/integration/test_agent_integration.py:list_tools()
SERENA_TOOLS = ("list_dir", "read_file", "find_file", "search_for_pattern")


class AgentVerdict(StrEnum):
    """Judgements accepted from the model."""

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
    description: str = Field(
        description="One short sentence explaining the significance of the cited line. No fluff or waffle; straight to the point.",
        examples=["This workflow runs on pull requests.", "This task runs the tests."],
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

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        """Require a short, non-empty evidence description."""
        if not value or len(value) > MAX_EVIDENCE_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Evidence description must contain 1 to {MAX_EVIDENCE_DESCRIPTION_LENGTH} characters."
            )
        return value


class AgentStructuredResponse(BaseModel):
    """Structured response requested from the Azure deployment."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: AgentVerdict = Field(examples=["pass", "fail", "uncertain"])
    explanation: str = Field(
        description="Succinct, efficient explanation. No fluff or waffle; straight to the point. One paragraph."
    )
    evidence: list[AgentEvidence]

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        """Require a short, non-empty explanation."""
        if not value or len(value) > MAX_EXPLANATION_LENGTH:
            raise ValueError(
                f"Explanation must contain 1 to {MAX_EXPLANATION_LENGTH:,} characters."
            )
        return value


class AgentFrameworkEvaluator:
    """Keep Docker and Azure startup lazy until a rule evaluates."""

    def __init__(self, settings: Settings) -> None:
        """Use the settings validated at application startup."""
        self.settings = settings

    def evaluate(self, snapshot_path: Path, prompt: str) -> RuleEvaluation:
        """Run one isolated evaluation and translate expected integration failures."""
        try:
            return _evaluate_source_snapshot_with_agent(
                snapshot_path, prompt, self.settings
            )
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


def _load_system_prompt() -> str:
    return (
        files("repo_compliance.infrastructure.agentic")
        .joinpath("system_prompt.md")
        .read_text(encoding="utf-8")
    )


def _evaluate_source_snapshot_with_agent(
    snapshot_path: Path, prompt: str, settings: Settings
) -> RuleEvaluation:
    with (
        extracted_source_snapshot(snapshot_path) as repository,
        TemporaryDirectory(prefix="repo-compliance-serena-") as temporary_state,
    ):
        state = Path(temporary_state)
        _write_serena_configurations(state)
        container_name = f"repo-compliance-{uuid4().hex}"
        try:
            output = asyncio.run(
                _get_agent_response(repository, state, container_name, settings, prompt)
            )
        finally:
            _remove_container(container_name)
        return _parse_agent_response(output)


async def _get_agent_response(
    repository: Path,
    state: Path,
    container_name: str,
    settings: Settings,
    prompt: str,
) -> object:
    async with (
        asyncio.timeout(EVALUATION_TIMEOUT_SECONDS),
        AzureCliCredential() as credential,
        _create_azure_client(settings, credential) as azure_client,
        _create_serena_tool(repository, state, container_name) as serena,
    ):
        agent = _create_agent(settings, azure_client, serena)
        response = await agent.run(
            prompt, options={"response_format": AgentStructuredResponse}
        )
        return response.value


def _create_agent(
    settings: Settings, azure_client: AsyncAzureOpenAI, serena: MCPStdioTool
) -> Agent:
    client = OpenAIChatCompletionClient(
        model=settings.deployment, async_client=azure_client
    )
    options: OpenAIChatCompletionOptions = {
        "allow_multiple_tool_calls": False,
        "store": False,
    }
    return Agent(
        client=client,
        name="repository-compliance",
        instructions=_load_system_prompt(),
        tools=[serena],
        default_options=options,
    )


def _create_azure_client(
    settings: Settings, credential: AzureCliCredential
) -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.endpoint,
        azure_deployment=settings.deployment,
        api_version=settings.api_version,
        azure_ad_token_provider=get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default",
        ),
        http_client=DefaultAsyncHttpxClient(follow_redirects=False, trust_env=False),
        max_retries=0,
        timeout=EVALUATION_TIMEOUT_SECONDS,
    )


def _create_serena_tool(
    repository: Path, state: Path, container_name: str
) -> MCPStdioTool:
    return MCPStdioTool(
        name="repository-files",
        command="docker",
        args=_serena_docker_arguments(repository, state, container_name),
        allowed_tools=SERENA_TOOLS,
        load_prompts=False,
        request_timeout=MCP_REQUEST_TIMEOUT_SECONDS,
    )


def _serena_docker_arguments(
    repository: Path, state: Path, container_name: str
) -> list[str]:
    # Keep each option beside its value for readability.
    # fmt: off
    return [
        # Start the container and manage communication and cleanup.
        "run",
        "-i",
        "--init",
        "--pull", "never",
        "--name", container_name,

        # Restrict filesystem changes, network access, and Linux privileges.
        "--read-only",
        "--network", "none",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",

        # Share repository files and provide writable working storage.
        "--mount", f"type=bind,src={repository.resolve()},dst=/repository,readonly",
        "--mount", f"type=bind,src={state.resolve()},dst=/state",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",

        # Set Serena's home folder and disable Python cache files.
        "--env", "SERENA_HOME=/state",
        "--env", "PYTHONDONTWRITEBYTECODE=1",

        # Select Serena's executable and image, then configure its tool server.
        "--entrypoint", "/workspaces/serena/.venv/bin/serena",
        SERENA_IMAGE,
        "start-mcp-server",
        "--transport", "stdio",
        "--project", "/repository",
        "--context", "/state/context.yml",
    ]
    # fmt: on


def _write_serena_configurations(state: Path) -> None:
    project_state = _create_serena_project_state(state)
    _write_yaml(state / "serena_config.yml", _serena_global_configuration())
    _write_yaml(project_state / "project.yml", _serena_project_configuration())
    _write_yaml(state / "context.yml", _serena_context_configuration())


def _create_serena_project_state(state: Path) -> Path:
    project_state = state / "project"
    project_state.mkdir()
    return project_state


def _serena_global_configuration() -> dict[str, str | bool | int | list[str]]:
    # See: https://github.com/oraios/serena/blob/main/src/serena/resources/serena_config.template.yml
    return {
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
    }


def _serena_project_configuration() -> dict[str, str | bool | list[str] | None]:
    # See: https://github.com/oraios/serena/blob/main/src/serena/resources/project.template.yml
    return {
        "project_name": "repository",
        "language_servers": [],
        "read_only": True,
        "ignore_all_files_in_gitignore": False,
        "initial_prompt": "",
        "activation_command": None,
    }


def _serena_context_configuration() -> dict[str, str | bool]:
    # See: https://github.com/oraios/serena/blob/main/src/serena/resources/config/contexts/context.template.yml
    return {
        "name": "compliance",
        "prompt": "",
        "single_project": True,
    }


def _write_yaml(path: Path, configuration: object) -> None:
    path.write_text(yaml.safe_dump(configuration), encoding="utf-8")


def _remove_container(container_name: str) -> None:
    try:
        result = _force_remove_container(container_name)
    except FileNotFoundError:
        # Startup already reports missing Docker; there is no container to remove.
        return
    except subprocess.TimeoutExpired as error:
        raise AgentError("Docker container cleanup timed out.") from error
    _ensure_container_removed(result)


def _force_remove_container(container_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "rm", "--force", container_name],
        capture_output=True,
        text=True,
        timeout=DOCKER_CLEANUP_TIMEOUT_SECONDS,
        check=False,
    )


def _ensure_container_removed(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0 and "No such container" not in result.stderr:
        raise AgentError("Could not remove the agent's Docker container.")


def _parse_agent_response(output: object) -> RuleEvaluation:
    result = AgentStructuredResponse.model_validate(output)
    _ensure_usable_agent_verdict(result)
    return _convert_agent_verdict_to_rule_evaluation(result)


def _ensure_usable_agent_verdict(result: AgentStructuredResponse) -> None:
    if result.verdict is AgentVerdict.UNCERTAIN:
        raise AgentError(f"Agent could not judge: {result.explanation}")
    if result.verdict is AgentVerdict.PASS and not result.evidence:
        raise AgentError("Agent returned a pass without supporting evidence.")


def _convert_agent_verdict_to_rule_evaluation(
    result: AgentStructuredResponse,
) -> RuleEvaluation:
    evidence = tuple(
        Evidence(item.path, item.line, item.description) for item in result.evidence
    )
    return RuleEvaluation(
        result.verdict is AgentVerdict.PASS, result.explanation, evidence
    )
