import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from agent_framework import Content

from repo_compliance.errors import AgentError
from repo_compliance.infrastructure.agentic.agent_framework import (
    SERENA_TOOLS,
    AgentFrameworkEvaluator,
    create_serena_tool,
    write_serena_configuration,
)
from repo_compliance.rules.agentic.ci_workflow_on_pull_requests import PROMPT_FILENAME
from repo_compliance.rules.agentic.helpers import load_rule_prompt
from repo_compliance.settings import get_env_settings

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures" / "ci_workflows"


@pytest.mark.serena
def test_serena_reads_isolated_source(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(FIXTURES / "qualifying", repository)
    untrusted_config = repository / ".serena"
    untrusted_config.mkdir()
    (untrusted_config / "project.yml").write_text(
        "activation_command: touch /state/repository-config-was-executed\n"
        "language_servers: [python]\nfixed_tools: [execute_shell_command]\n",
        encoding="utf-8",
    )
    (repository / ".gitignore").write_text(".github/\n", encoding="utf-8")
    state = tmp_path / "state"
    state.mkdir()
    write_serena_configuration(state)
    container_name = f"repo-compliance-smoke-{uuid4().hex}"
    try:
        asyncio.run(_inspect_serena(repository, state, container_name))
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            check=False,
            timeout=10,
        )
    assert not (state / "repository-config-was-executed").exists()
    assert (repository / ".github/workflows/ci.yml").read_bytes() == (
        FIXTURES / "qualifying/.github/workflows/ci.yml"
    ).read_bytes()


async def _inspect_serena(repository: Path, state: Path, container_name: str) -> None:
    async with (
        asyncio.timeout(90),
        create_serena_tool(repository, state, container_name) as serena,
    ):
        assert serena.session is not None
        tools = await serena.session.list_tools()
        assert {tool.name for tool in tools.tools} == set(SERENA_TOOLS)
        listing = await serena.call_tool(
            "list_dir", relative_path=".github", recursive=True
        )
        assert "ci.yml" in _tool_text(listing)
        workflow = await serena.call_tool(
            "read_file", relative_path=".github/workflows/ci.yml"
        )
        assert "pull_request" in _tool_text(workflow)
        assert "unittest" in _tool_text(workflow)
        _assert_docker_isolation(container_name)


def _tool_text(result: str | list[Content]) -> str:
    if isinstance(result, str):
        return result
    return "\n".join(content.text or "" for content in result)


def _assert_docker_isolation(container_name: str) -> None:
    inspected = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            (
                "{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.NetworkMode}} "
                '{{range .Mounts}}{{if eq .Destination "/repository"}}{{.RW}}{{end}}{{end}}'
            ),
            container_name,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert inspected.stdout.strip() == "true none false"
    write = subprocess.run(
        ["docker", "exec", container_name, "touch", "/repository/should-not-exist"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert write.returncode != 0
    assert "Read-only file system" in write.stderr


@pytest.mark.azure
@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("qualifying", "pass"),
        ("unrestricted", "pass"),
        ("push_only", "fail"),
        ("wrong_branch", "fail"),
        ("missing_workflow", "fail"),
        ("insufficient_evidence", "uncertain"),
    ],
)
def test_live_prompt(scenario: str, expected: str, tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    source = FIXTURES / scenario
    with ZipFile(snapshot, "w") as source_zip:
        for path in source.rglob("*"):
            if path.is_file():
                source_zip.write(
                    path, f"snapshot/{path.relative_to(source).as_posix()}"
                )
    evaluator = AgentFrameworkEvaluator(get_env_settings())
    prompt = load_rule_prompt(PROMPT_FILENAME)
    if expected == "uncertain":
        with pytest.raises(AgentError, match="Agent could not judge"):
            evaluator.evaluate(snapshot, prompt)
    else:
        result = evaluator.evaluate(snapshot, prompt)
        assert result.passed is (expected == "pass"), result.message
