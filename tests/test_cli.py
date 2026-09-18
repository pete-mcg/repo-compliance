from collections.abc import Sequence
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from repo_compliance import cli
from repo_compliance.cli import main
from repo_compliance.rules.agentic.ci_workflow_on_pull_requests import RULE as CI_RULE

from .fakes import FakeAgentEvaluator, FakeGitHub


def write_empty_config(path: Path) -> Path:
    path.write_text("repositories: []\n", encoding="utf-8")
    return path


def arguments(config: Path, output: Path) -> Sequence[str]:
    return ("--config", str(config), "--output", str(output))


def test_successful_completed_run_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = write_empty_config(tmp_path / "repositories.yml")
    output = tmp_path / "report.md"
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(arguments(config, output))

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith(
        "# Repository Compliance Report"
    )


def test_missing_token_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = write_empty_config(tmp_path / "repositories.yml")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    exit_code = main(arguments(config, tmp_path / "report.md"))

    assert exit_code == 1
    assert "GITHUB_TOKEN is required" in capsys.readouterr().err


def test_invalid_config_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "repositories.yml"
    config.write_text("repositories: [\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(arguments(config, tmp_path / "report.md"))

    assert exit_code == 1
    assert "not valid YAML" in capsys.readouterr().err


def test_output_failure_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = write_empty_config(tmp_path / "repositories.yml")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(arguments(config, tmp_path))

    assert exit_code == 1
    assert "Could not write report" in capsys.readouterr().err


def test_unexpected_checker_bug_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = write_empty_config(tmp_path / "repositories.yml")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def broken_run(
        _config: object, _github: object, _rules: object, _evaluator: object
    ) -> None:
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr(cli, "run_all_compliance_checks", broken_run)

    exit_code = main(arguments(config, tmp_path / "report.md"))

    assert exit_code == 1
    assert "Unexpected RuntimeError: unexpected bug" in capsys.readouterr().err


def test_default_paths_work_from_current_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_directory = tmp_path / "config"
    config_directory.mkdir()
    write_empty_config(config_directory / "repositories.yml")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(())

    assert exit_code == 0
    assert (tmp_path / "compliance-report.md").is_file()


@pytest.mark.parametrize("exempt", [True, False])
def test_cli_supplies_lazy_evaluator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exempt: bool
) -> None:
    config = tmp_path / "repositories.yml"
    content = "repositories:\n  - repository: example/service\n"
    if exempt:
        content += (
            f"    exemptions:\n      - rule: {CI_RULE.id}\n        reason: Approved\n"
        )
    config.write_text(content, encoding="utf-8")
    output = tmp_path / "report.md"
    github = MagicMock()
    github.__enter__.return_value = FakeGitHub()
    evaluator = FakeAgentEvaluator()
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr(cli, "GitHubClient", Mock(return_value=github))
    monkeypatch.setattr(cli, "AgentFrameworkEvaluator", Mock(return_value=evaluator))
    monkeypatch.setattr(cli, "RULES", (CI_RULE,))

    assert main(arguments(config, output)) == 0
    assert len(evaluator.calls) == (0 if exempt else 1)
    assert ("EXEMPT" if exempt else "PASS") in output.read_text(encoding="utf-8")
