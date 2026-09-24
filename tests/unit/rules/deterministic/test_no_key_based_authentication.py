from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from repo_compliance.domain import RuleContext, RuleEvaluation
from repo_compliance.errors import SourceSnapshotError
from repo_compliance.rules.deterministic.no_key_based_authentication import (
    MAX_EVIDENCE,
    MAX_FILE_BYTES,
    check,
)
from tests.unit.fakes import FakeGitHub

REPOSITORY = "example/service"


def write_source_snapshot(path: Path, source_items: dict[str, bytes]) -> Path:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as source_snapshot:
        for name, content in source_items.items():
            source_snapshot.writestr(name, content)
    return path


def run_check(source_snapshot_path: Path) -> RuleEvaluation:
    return check(RuleContext(REPOSITORY, FakeGitHub(), source_snapshot_path))


def test_detects_all_markers_case_separators_and_camel_case(tmp_path: Path) -> None:
    lines = (
        "api-key=value",
        "API_KEY=value",
        "apiKey=value",
        "x-api-key: value",
        "xApiKey: value",
        "access_key=value",
        "accessKey=value",
        "secret-key=value",
        "secretKey=value",
        "account_key=value",
        "accountKey=value",
        "subscription-key=value",
        "subscriptionKey=value",
        "SharedAccessKey=value",
        "shared_access_key_name=value",
        "sharedAccessKeyName=value",
    )
    source_snapshot_path = write_source_snapshot(
        tmp_path / "repository.zip",
        {"service-root/src/settings.py": "\n".join(lines).encode()},
    )

    result = run_check(source_snapshot_path)

    assert not result.passed
    assert len(result.evidence) == len(lines)
    assert result.evidence[0].description == "api-key"
    assert result.evidence[3].description == "x-api-key"
    assert result.evidence[-1].description == "shared-access-key"
    assert result.evidence[-1].line == len(lines)


def test_skips_dependency_build_binary_non_utf8_and_oversized_files(
    tmp_path: Path,
) -> None:
    marker = b"apiKey=never-report-this"
    source_snapshot_path = write_source_snapshot(
        tmp_path / "repository.zip",
        {
            "root/src/clean.py": b"print('clean')",
            "root/node_modules/package.js": marker,
            "root/vendor/library.py": marker,
            "root/build/generated.txt": marker,
            "root/image.bin": b"\x89PNG\0" + marker,
            "root/non-utf8.txt": b"\xff" + marker,
            "root/large.txt": marker + b"x" * MAX_FILE_BYTES,
        },
    )

    result = run_check(source_snapshot_path)

    assert result.passed
    assert result.evidence == ()


def test_scans_file_at_exact_size_limit(tmp_path: Path) -> None:
    content = b"apiKey=value" + b"x" * (MAX_FILE_BYTES - len(b"apiKey=value"))
    source_snapshot_path = write_source_snapshot(
        tmp_path / "repository.zip",
        {"root/settings.txt": content},
    )

    result = run_check(source_snapshot_path)

    assert not result.passed
    assert len(result.evidence) == 1


def test_caps_evidence_and_reports_omitted_count_without_secret_content(
    tmp_path: Path,
) -> None:
    secret = "DO_NOT_INCLUDE_THIS_SECRET"
    source = "\n".join(f'apiKey="{secret}-{index}"' for index in range(25))
    source_snapshot_path = write_source_snapshot(
        tmp_path / "repository.zip",
        {"root/src/config.py": source.encode()},
    )

    result = run_check(source_snapshot_path)

    assert len(result.evidence) == MAX_EVIDENCE
    assert result.omitted_evidence_count == 5
    assert result.evidence[-1].line == MAX_EVIDENCE
    assert secret not in repr(result)


def test_reports_each_distinct_marker_once_per_line(tmp_path: Path) -> None:
    source_snapshot_path = write_source_snapshot(
        tmp_path / "repository.zip",
        {"root/config.txt": b"apiKey=x; api_key=y; secretKey=z"},
    )

    result = run_check(source_snapshot_path)

    assert [item.description for item in result.evidence] == ["api-key", "secret-key"]


def test_clean_source_snapshot_passes(tmp_path: Path) -> None:
    source_snapshot_path = write_source_snapshot(
        tmp_path / "repository.zip",
        {"root/src/app.py": b"token = credential_provider.get_token()"},
    )

    result = run_check(source_snapshot_path)

    assert result.passed
    assert "No key-based" in result.message


def test_missing_source_snapshot_context_is_programming_error() -> None:
    with pytest.raises(RuntimeError, match="requires a source snapshot"):
        check(RuleContext(REPOSITORY, FakeGitHub()))


def test_invalid_zip_is_a_source_snapshot_error(tmp_path: Path) -> None:
    source_snapshot_path = tmp_path / "repository.zip"
    source_snapshot_path.write_bytes(b"not a zip")

    with pytest.raises(SourceSnapshotError, match="Could not inspect"):
        run_check(source_snapshot_path)
