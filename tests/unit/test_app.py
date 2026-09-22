from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from repo_compliance import app
from repo_compliance.app import main
from repo_compliance.errors import CliError
from repo_compliance.rules.agentic.ci_workflow_on_pull_requests import RULE as CI_RULE

from .fakes import FakeAgentEvaluator, FakeGitHub


@pytest.fixture(autouse=True)
def local_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "example-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")


def write_empty_config(path: Path) -> None:
    path.write_text("repositories: []\n", encoding="utf-8")


def test_successful_completed_run_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_empty_config(tmp_path / "config/repositories.yml")
    output = tmp_path / "compliance-report.md"
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main()

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith(
        "# 🛡️ Repository Compliance Report"
    )


def test_invalid_settings_fail_before_connecting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    write_empty_config(tmp_path / "config/repositories.yml")
    monkeypatch.setattr(
        app, "get_env_settings", Mock(side_effect=CliError("Invalid runtime settings"))
    )
    github = Mock()
    monkeypatch.setattr(app, "GitHubClient", github)

    exit_code = main()

    assert exit_code == 1
    assert "Invalid runtime settings" in caplog.text
    github.assert_not_called()


def test_invalid_config_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    config = tmp_path / "config/repositories.yml"
    config.write_text("repositories: [\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main()

    assert exit_code == 1
    assert "not valid YAML" in caplog.text


def test_output_failure_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    write_empty_config(tmp_path / "config/repositories.yml")
    (tmp_path / "compliance-report.md").mkdir()
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main()

    assert exit_code == 1
    assert "Could not write report" in caplog.text


def test_unexpected_checker_bug_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    write_empty_config(tmp_path / "config/repositories.yml")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def broken_run(
        _config: object, _github: object, _rules: object, _evaluator: object
    ) -> None:
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr(app, "run_all_compliance_checks", broken_run)

    exit_code = main()

    assert exit_code == 1
    assert "Unexpected RuntimeError" in caplog.text
    assert "RuntimeError: unexpected bug" in caplog.text


@pytest.mark.parametrize("exempt", [True, False])
def test_app_supplies_lazy_evaluator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exempt: bool
) -> None:
    config = tmp_path / "config/repositories.yml"
    content = "repositories:\n  - repository: example/service\n"
    if exempt:
        content += (
            f"    exemptions:\n      - rule: {CI_RULE.id}\n        reason: Approved\n"
        )
    config.write_text(content, encoding="utf-8")
    output = tmp_path / "compliance-report.md"
    github = MagicMock()
    github.__enter__.return_value = FakeGitHub()
    evaluator = FakeAgentEvaluator()
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr(app, "GitHubClient", Mock(return_value=github))
    monkeypatch.setattr(app, "AgentFrameworkEvaluator", Mock(return_value=evaluator))
    monkeypatch.setattr(app, "RULES", (CI_RULE,))

    assert main() == 0
    assert len(evaluator.calls) == (0 if exempt else 1)
    assert ("EXEMPT" if exempt else "PASS") in output.read_text(encoding="utf-8")
