from pathlib import Path

import pytest

from repo_compliance.errors import CliError
from repo_compliance.settings import get_settings

VALID_SETTINGS = {
    "GITHUB_TOKEN": "private-token",
    "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
    "AZURE_OPENAI_DEPLOYMENT": "example-deployment",
    "AZURE_OPENAI_API_VERSION": "2025-04-01-preview",
}


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for name in VALID_SETTINGS:
        monkeypatch.delenv(name, raising=False)


def test_loads_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(f"{name}={value}" for name, value in VALID_SETTINGS.items()),
        encoding="utf-8",
    )

    assert get_settings().model_dump(by_alias=True) == VALID_SETTINGS


def test_loads_environment_without_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in VALID_SETTINGS.items():
        monkeypatch.setenv(name, value)

    assert get_settings().model_dump(by_alias=True) == VALID_SETTINGS


def test_reports_all_missing_settings() -> None:
    with pytest.raises(CliError, match="Invalid runtime settings") as caught:
        get_settings()

    assert all(name in str(caught.value) for name in VALID_SETTINGS)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GITHUB_TOKEN", "   "),
        ("AZURE_OPENAI_ENDPOINT", "http://approved.openai.azure.com"),
        ("AZURE_OPENAI_ENDPOINT", "https://unapproved.example.com"),
        (
            "AZURE_OPENAI_ENDPOINT",
            "https://approved.openai.azure.com/?redirect=elsewhere",
        ),
        ("AZURE_OPENAI_DEPLOYMENT", ""),
        ("AZURE_OPENAI_DEPLOYMENT", "invalid/deployment"),
        ("AZURE_OPENAI_API_VERSION", "placeholder"),
    ],
)
def test_rejects_invalid_settings_without_exposing_values(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    for setting_name, setting_value in VALID_SETTINGS.items():
        monkeypatch.setenv(setting_name, setting_value)
    monkeypatch.setenv(name, value)

    with pytest.raises(CliError) as caught:
        get_settings()

    error = str(caught.value)
    assert name in error
    assert "private-token" not in error
    assert "input_value" not in error
