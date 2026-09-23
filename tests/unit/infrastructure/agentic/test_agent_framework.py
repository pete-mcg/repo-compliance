import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from zipfile import ZipFile

import pytest
from agent_framework.exceptions import ToolException
from azure.core.exceptions import ClientAuthenticationError
from pydantic import ValidationError

from repo_compliance.domain import Evidence
from repo_compliance.errors import AgentError
from repo_compliance.infrastructure.agentic import agent_framework as adapter
from repo_compliance.settings import Settings


def _configure_azure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://approved.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "ci-review")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-10-21")


def _judgment(verdict: str = "pass") -> dict[str, object]:
    return {
        "verdict": verdict,
        "explanation": "CI tests run on pull requests to main.",
        "evidence": [
            {"path": ".github/workflows/ci.yml", "line": 3, "marker": "pr-trigger"}
        ],
    }


@pytest.mark.parametrize("verdict", ["pass", "fail"])
def test_converts_structured_response(verdict: str) -> None:
    result = adapter._to_evaluation(_judgment(verdict))
    assert result.passed is (verdict == "pass")
    assert result.evidence == (Evidence(".github/workflows/ci.yml", 3, "pr-trigger"),)


def test_uncertainty_and_pass_without_evidence_are_errors() -> None:
    with pytest.raises(AgentError, match="could not judge"):
        adapter._to_evaluation(_judgment("uncertain"))
    with pytest.raises(AgentError, match="without supporting evidence"):
        adapter._to_evaluation({**_judgment(), "evidence": []})
    assert not adapter._to_evaluation({**_judgment("fail"), "evidence": []}).passed


@pytest.mark.parametrize(
    "changes",
    [
        {"verdict": "exempt"},
        {"explanation": " "},
        {"explanation": "x" * 1001},
        {"unexpected": "value"},
        {"evidence": [{"path": "../secret", "line": 1, "marker": "trigger"}]},
        {"evidence": [{"path": "ci.yml", "line": 0, "marker": "trigger"}]},
        {"evidence": [{"path": "ci.yml", "line": "2", "marker": "trigger"}]},
        {"evidence": [{"path": "ci.yml", "line": True, "marker": "trigger"}]},
        {"evidence": [{"path": "ci.yml", "line": 1, "marker": " "}]},
    ],
)
def test_rejects_invalid_structured_output(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        adapter._to_evaluation({**_judgment(), **changes})


def test_schema_uses_supported_azure_keywords() -> None:
    schema = json.dumps(adapter.AgentStructuredResponse.model_json_schema())
    for keyword in (
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "maxItems",
        "pattern",
    ):
        assert f'"{keyword}":' not in schema


@pytest.mark.parametrize(
    "error",
    [
        ToolException("private diagnostic"),
        ClientAuthenticationError("private diagnostic"),
        FileNotFoundError("private diagnostic"),
        TimeoutError("private diagnostic"),
    ],
)
def test_expected_failures_are_safe_rule_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    _configure_azure(monkeypatch)
    monkeypatch.setattr(adapter, "_evaluate_snapshot", Mock(side_effect=error))
    with pytest.raises(AgentError) as caught:
        adapter.AgentFrameworkEvaluator(Settings()).evaluate(
            Path("unused.zip"), "prompt"
        )
    assert "private diagnostic" not in str(caught.value)


@pytest.mark.parametrize(
    "output", [_judgment(), None, {"verdict": "pass"}, ToolException("MCP unavailable")]
)
def test_evaluation_validates_output_and_cleans_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: object
) -> None:
    _configure_azure(monkeypatch)
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as source_zip:
        source_zip.writestr("root/.github/workflows/ci.yml", "on: pull_request")
    paths: list[Path] = []

    async def run(
        repository: Path,
        state: Path,
        _name: str,
        _settings: Settings,
        prompt: str,
    ) -> object:
        assert prompt == "rule prompt"
        assert (repository / ".github/workflows/ci.yml").is_file()
        assert (state / "project/project.yml").is_file()
        paths.extend([repository, state])
        if isinstance(output, Exception):
            raise output
        return output

    monkeypatch.setattr(adapter, "_run_agent", run)
    remove = Mock()
    monkeypatch.setattr(adapter, "_remove_container", remove)
    if output == _judgment():
        assert (
            adapter.AgentFrameworkEvaluator(Settings())
            .evaluate(snapshot, "rule prompt")
            .passed
        )
    else:
        with pytest.raises(AgentError, match=r"ValidationError|ToolException"):
            adapter.AgentFrameworkEvaluator(Settings()).evaluate(
                snapshot, "rule prompt"
            )
    assert paths and all(not path.exists() for path in paths)
    remove.assert_called_once()


@pytest.mark.parametrize("times_out", [False, True])
def test_agent_requests_schema_and_closes_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, times_out: bool
) -> None:
    _configure_azure(monkeypatch)
    credential = AsyncMock()
    monkeypatch.chdir(tmp_path)
    azure = AsyncMock()
    serena = AsyncMock()
    run = AsyncMock(return_value=SimpleNamespace(value=_judgment()))
    agent = Mock(return_value=SimpleNamespace(run=run))
    monkeypatch.setattr(adapter, "AzureCliCredential", Mock(return_value=credential))
    monkeypatch.setattr(adapter, "_create_azure_client", Mock(return_value=azure))
    monkeypatch.setattr(adapter, "_create_serena_tool", Mock(return_value=serena))
    monkeypatch.setattr(adapter, "OpenAIChatCompletionClient", Mock())
    monkeypatch.setattr(adapter, "Agent", agent)
    if times_out:
        monkeypatch.setattr(adapter, "EVALUATION_TIMEOUT_SECONDS", 0.01)

        async def slow_run(*_args: object, **_kwargs: object) -> None:
            await asyncio.sleep(1)

        run.side_effect = slow_run
        with pytest.raises(TimeoutError):
            asyncio.run(
                adapter._run_agent(tmp_path, tmp_path, "test", Settings(), "prompt")
            )
    else:
        output = asyncio.run(
            adapter._run_agent(tmp_path, tmp_path, "test", Settings(), "prompt")
        )
        assert output == _judgment()
        run.assert_awaited_once_with(
            "prompt", options={"response_format": adapter.AgentStructuredResponse}
        )
    system_prompt = adapter._load_system_prompt()
    assert agent.call_args.kwargs["instructions"] == system_prompt
    assert agent.call_args.kwargs["default_options"] == {
        "allow_multiple_tool_calls": False,
        "store": False,
    }
    for resource in (serena, azure, credential):
        resource.__aexit__.assert_awaited_once()


def test_azure_routing_ignores_unrelated_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_azure(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_BASE_URL", "https://unapproved.example.com")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://unapproved.example.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "unused-key")
    monkeypatch.setenv("AZURE_OPENAI_AD_TOKEN", "unused-token")
    monkeypatch.setenv("OPENAI_API_KEY", "unused-key")

    async def inspect() -> None:
        async with (
            adapter.AzureCliCredential() as credential,
            adapter._create_azure_client(Settings(), credential) as client,
        ):
            assert (
                str(client.base_url)
                == "https://approved.openai.azure.com/openai/deployments/ci-review/"
            )
            assert client.default_query == {"api-version": "2024-10-21"}
            assert "unused-key" not in client.auth_headers.values()

    asyncio.run(inspect())


def test_serena_launch_is_local_and_restricted(tmp_path: Path) -> None:
    tool = adapter._create_serena_tool(tmp_path / "source", tmp_path / "state", "test")
    arguments = tool.args
    assert tool.command == "docker"
    assert tool.allowed_tools == adapter.SERENA_TOOLS
    assert not tool.load_prompts_flag
    assert "--read-only" in arguments
    assert arguments[arguments.index("--network") + 1] == "none"
    assert arguments[arguments.index("--pull") + 1] == "never"
    assert adapter.SERENA_IMAGE in arguments and "@sha256:" in adapter.SERENA_IMAGE
    assert any(argument.endswith("dst=/repository,readonly") for argument in arguments)
    assert not any("TOKEN" in argument or "AZURE" in argument for argument in arguments)
