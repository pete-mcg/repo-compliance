from collections.abc import Sequence
from pathlib import Path

import pytest

from repo_compliance import cli
from repo_compliance.cli import CliOptions, main


def set_empty_config(path: Path) -> Path:
    path.write_text("repositories: []\n", encoding="utf-8")
    return path


def get_cli_arguments(config: Path, output: Path) -> Sequence[str]:
    return ("--config", str(config), "--output", str(output))


def test_successful_completed_run_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = set_empty_config(tmp_path / "repositories.yml")
    output = tmp_path / "report.md"
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(get_cli_arguments(config, output))

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith(
        "# Repository Compliance Report"
    )


def test_missing_token_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = set_empty_config(tmp_path / "repositories.yml")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    exit_code = main(get_cli_arguments(config, tmp_path / "report.md"))

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

    exit_code = main(get_cli_arguments(config, tmp_path / "report.md"))

    assert exit_code == 1
    assert "not valid YAML" in capsys.readouterr().err


def test_output_failure_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = set_empty_config(tmp_path / "repositories.yml")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(get_cli_arguments(config, tmp_path))

    assert exit_code == 1
    assert "Could not write report" in capsys.readouterr().err


def test_unexpected_checker_bug_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = set_empty_config(tmp_path / "repositories.yml")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def handle_broken_check(_options: CliOptions, _token: str) -> None:
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr(cli, "_handle_compliance_check", handle_broken_check)

    exit_code = main(get_cli_arguments(config, tmp_path / "report.md"))

    assert exit_code == 1
    assert "Unexpected RuntimeError: unexpected bug" in capsys.readouterr().err


def test_default_paths_work_from_current_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_directory = tmp_path / "config"
    config_directory.mkdir()
    set_empty_config(config_directory / "repositories.yml")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    exit_code = main(())

    assert exit_code == 0
    assert (tmp_path / "compliance-report.md").is_file()
