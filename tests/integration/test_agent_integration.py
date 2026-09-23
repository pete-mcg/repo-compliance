import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from agent_framework import Content

from repo_compliance.infrastructure.agentic.agent_framework import (
    SERENA_TOOLS,
    AgentFrameworkEvaluator,
    _create_serena_tool,
    _write_serena_configurations,
)
from repo_compliance.settings import get_env_settings

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "agent_repository"


@pytest.mark.serena
def test_serena_reads_isolated_source(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(FIXTURE, repository)
    untrusted_config = repository / ".serena"
    untrusted_config.mkdir()
    (untrusted_config / "project.yml").write_text(
        "activation_command: touch /state/repository-config-was-executed\n"
        "language_servers: [python]\nfixed_tools: [execute_shell_command]\n",
        encoding="utf-8",
    )
    (repository / ".gitignore").write_text("README.md\n", encoding="utf-8")
    state = tmp_path / "state"
    state.mkdir()
    _write_serena_configurations(state)
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
    assert (repository / "README.md").read_bytes() == (
        FIXTURE / "README.md"
    ).read_bytes()


async def _inspect_serena(repository: Path, state: Path, container_name: str) -> None:
    async with (
        asyncio.timeout(90),
        _create_serena_tool(repository, state, container_name) as serena,
    ):
        assert serena.session is not None
        tools = await serena.session.list_tools()
        assert {tool.name for tool in tools.tools} == set(SERENA_TOOLS)
        listing = await serena.call_tool("list_dir", relative_path=".", recursive=True)
        assert "README.md" in _tool_text(listing)
        readme = await serena.call_tool("read_file", relative_path="README.md")
        assert "Run tests with `python -m unittest discover`." in _tool_text(readme)
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
def test_agent_evaluates_source_snapshot(tmp_path: Path) -> None:
    # Exercise the infrastructure shared by all agentic rules with one live evaluation.
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as source_zip:
        source_zip.write(FIXTURE / "README.md", "snapshot/README.md")
    evaluator = AgentFrameworkEvaluator(get_env_settings())
    prompt = (
        "Inspect README.md and determine whether it contains instructions for running "
        "tests. Pass if it does; fail if it does not. Cite the line containing the "
        "test command as evidence."
    )
    result = evaluator.evaluate(snapshot, prompt)
    assert result.passed is True, result.message
    assert any(
        evidence.path == "README.md" and evidence.line == 3
        for evidence in result.evidence
    ), result.evidence
