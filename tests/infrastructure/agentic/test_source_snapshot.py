import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from repo_compliance.errors import SourceSnapshotError
from repo_compliance.infrastructure.agentic import source_snapshot
from repo_compliance.infrastructure.agentic.source_snapshot import extracted_snapshot


def test_extracts_wrapper_and_cleans_up_after_consumer_failure(tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as archive:
        archive.writestr("owner-repo-sha/", "")
        archive.writestr(
            "owner-repo-sha/.github/workflows/ci.yml", "on: pull_request\n"
        )
    original = snapshot.read_bytes()

    with extracted_snapshot(snapshot) as repository:
        assert (
            repository / ".github/workflows/ci.yml"
        ).read_text() == "on: pull_request\n"
    assert not repository.exists()

    with (
        pytest.raises(RuntimeError, match="consumer failed"),
        extracted_snapshot(snapshot) as repository,
    ):
        raise RuntimeError("consumer failed")

    assert not repository.exists()
    assert snapshot.read_bytes() == original


@pytest.mark.parametrize(
    "filename",
    [
        "../escape",
        "/absolute",
        "root/../../escape",
        "root/./file",
        "root//file",
        "C:/escape",
        "root/C:/escape",
        "root\\escape",
        "root/file:stream",
        "root/NUL",
        "root/file.",
        "root/file ",
        "file-without-wrapper",
    ],
)
def test_rejects_unsafe_paths(tmp_path: Path, filename: str) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as archive:
        entry = ZipInfo(filename)
        entry.filename = filename  # Preserve backslashes even when creating on Windows.
        archive.writestr(entry, "unsafe")
    with (
        pytest.raises(SourceSnapshotError, match="safely extract"),
        extracted_snapshot(snapshot),
    ):
        pytest.fail("Unsafe archive was accepted")
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("file_type", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR])
def test_rejects_links_and_special_files(tmp_path: Path, file_type: int) -> None:
    snapshot = tmp_path / "repository.zip"
    entry = ZipInfo("root/link")
    entry.create_system = 3
    entry.external_attr = (file_type | 0o777) << 16
    with ZipFile(snapshot, "w") as archive:
        archive.writestr(entry, "/etc/passwd")
    with pytest.raises(SourceSnapshotError), extracted_snapshot(snapshot):
        pytest.fail("Special file was accepted")


@pytest.mark.parametrize("names", [[], ["first/a", "second/b"], ["root/a", "root/a/b"]])
def test_rejects_empty_multiple_root_and_conflicting_archives(
    tmp_path: Path, names: list[str]
) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as archive:
        for name in names:
            archive.writestr(name, "content")
    with pytest.raises(SourceSnapshotError), extracted_snapshot(snapshot):
        pytest.fail("Invalid archive was accepted")


@pytest.mark.parametrize("limit", ["MAX_EXTRACTED_BYTES", "MAX_ENTRIES"])
def test_limits_extraction_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: str
) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as archive:
        archive.writestr("root/file", "content")
    monkeypatch.setattr(source_snapshot, limit, 0)
    with pytest.raises(SourceSnapshotError), extracted_snapshot(snapshot):
        pytest.fail("Extraction limit was ignored")


def test_corrupt_zip_is_expected_error(tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    snapshot.write_bytes(b"not a zip")
    with pytest.raises(SourceSnapshotError), extracted_snapshot(snapshot):
        pytest.fail("Corrupt archive was accepted")


def test_corrupt_compressed_content_is_expected_error(tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    filename = "root/file"
    with ZipFile(snapshot, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(filename, "content")
    content = bytearray(snapshot.read_bytes())
    # The file data follows the 30-byte ZIP header and filename.
    content[30 + len(filename)] = 0x07  # Reserved DEFLATE block type.
    snapshot.write_bytes(content)
    with pytest.raises(SourceSnapshotError), extracted_snapshot(snapshot):
        pytest.fail("Corrupt compressed data was accepted")
