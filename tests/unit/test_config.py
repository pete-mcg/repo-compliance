from pathlib import Path

import pytest

from repo_compliance.config import get_config
from repo_compliance.errors import ConfigError

RULE_IDS = frozenset({"codeowners-present", "deploy-workflow-present"})


def write_config(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    return path


def test_loads_empty_configuration(tmp_path: Path) -> None:
    path = write_config(tmp_path / "repositories.yml", "repositories: []\n")

    config = get_config(path, RULE_IDS)

    assert config.repositories == ()


def test_loads_populated_configuration_and_strips_reasons(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        """
repositories:
  - repository: example/service-api
    exemptions:
      - rule: deploy-workflow-present
        reason: "  No deployment.  "
""",
    )

    config = get_config(path, RULE_IDS)

    assert config.repositories[0].repository == "example/service-api"
    assert config.repositories[0].exemptions[0].reason == "No deployment."


@pytest.mark.parametrize("owner", ("a", "A1", "my-org", "my-org-2", "a" * 39))
def test_accepts_valid_repository_owners(tmp_path: Path, owner: str) -> None:
    repository = f"{owner}/repo"
    path = write_config(
        tmp_path / "repositories.yml",
        f"repositories:\n  - repository: {repository}\n",
    )

    config = get_config(path, RULE_IDS)

    assert config.repositories[0].repository == repository


@pytest.mark.parametrize(
    "repository",
    (
        "missing-slash",
        "too/many/slashes",
        "-owner/repo",
        "owner-/repo",
        "my--org/repo",
        "my---org/repo",
        f"{'a' * 40}/repo",
        "owner/",
        "owner/repo name",
    ),
)
def test_rejects_malformed_repository_names(
    tmp_path: Path,
    repository: str,
) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        f"repositories:\n  - repository: {repository}\n",
    )

    with pytest.raises(ConfigError, match="invalid"):
        get_config(path, RULE_IDS)


def test_rejects_malformed_yaml(tmp_path: Path) -> None:
    path = write_config(tmp_path / "repositories.yml", "repositories: [\n")

    with pytest.raises(ConfigError, match="not valid YAML"):
        get_config(path, RULE_IDS)


def test_rejects_missing_configuration_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Could not read"):
        get_config(tmp_path / "missing.yml", RULE_IDS)


def test_rejects_duplicate_repositories_case_insensitively(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        """
repositories:
  - repository: Example/Service
  - repository: example/service
""",
    )

    with pytest.raises(ConfigError, match="duplicate repositories"):
        get_config(path, RULE_IDS)


def test_rejects_duplicate_exemptions(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        """
repositories:
  - repository: example/service
    exemptions:
      - rule: codeowners-present
        reason: First
      - rule: codeowners-present
        reason: Second
""",
    )

    with pytest.raises(ConfigError, match="duplicate exemptions"):
        get_config(path, RULE_IDS)


def test_rejects_unknown_rule_id(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        """
repositories:
  - repository: example/service
    exemptions:
      - rule: unknown-rule
        reason: Not applicable
""",
    )

    with pytest.raises(ConfigError, match="unknown rule ID 'unknown-rule'"):
        get_config(path, RULE_IDS)


def test_rejects_blank_exemption_reason(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        """
repositories:
  - repository: example/service
    exemptions:
      - rule: codeowners-present
        reason: "   "
""",
    )

    with pytest.raises(ConfigError, match="invalid"):
        get_config(path, RULE_IDS)


def test_rejects_unknown_configuration_fields(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "repositories.yml",
        "repositories: []\nunexpected: true\n",
    )

    with pytest.raises(ConfigError, match="invalid"):
        get_config(path, RULE_IDS)
