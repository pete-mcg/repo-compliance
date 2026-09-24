import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from agent_framework import Content

from repo_compliance.infrastructure.agentic.agent_framework import (
    REPOSITORY_FILE_TOOLS,
    AgentFrameworkEvaluator,
    _create_repository_files_tool,
)
from repo_compliance.settings import get_env_settings

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "agent_repository"


@pytest.mark.mcp
def test_repository_file_server_reads_isolated_source(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(FIXTURE, repository)
    container_name = f"repo-compliance-smoke-{uuid4().hex}"
    try:
        asyncio.run(_inspect_repository_files(repository, container_name))
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            check=False,
            timeout=10,
        )
    assert (repository / "README.md").read_bytes() == (
        FIXTURE / "README.md"
    ).read_bytes()


async def _inspect_repository_files(repository: Path, container_name: str) -> None:
    async with (
        asyncio.timeout(90),
        _create_repository_files_tool(repository, container_name) as repository_files,
    ):
        assert repository_files.session is not None
        tools = await repository_files.session.list_tools()
        assert {tool.name for tool in tools.tools} == set(REPOSITORY_FILE_TOOLS)
        listing = await repository_files.call_tool("list_files")
        assert "README.md" in _tool_text(listing)
        readme = await repository_files.call_tool(
            "read_lines", path="README.md", start_line=1, end_line=3
        )
        assert "Run tests with `python -m unittest discover`." in _tool_text(readme)
        search = await repository_files.call_tool("search_text", query="unittest")
        assert "README.md:3:" in _tool_text(search)
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
                "{{.Config.User}} {{.HostConfig.ReadonlyRootfs}} "
                "{{.HostConfig.NetworkMode}} "
                '{{range .Mounts}}{{if eq .Destination "/repository"}}{{.RW}}{{end}}{{end}}'
            ),
            container_name,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert inspected.stdout.strip() == "65532:65532 true none false"
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
