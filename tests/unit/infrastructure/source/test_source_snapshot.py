import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from repo_compliance.errors import SourceSnapshotError
from repo_compliance.infrastructure.source import source_snapshot
from repo_compliance.infrastructure.source.source_snapshot import (
    extracted_source_snapshot,
)


def test_extracts_wrapper_and_cleans_up_after_consumer_failure(tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as source_zip:
        source_zip.writestr("owner-repo-sha/", "")
        source_zip.writestr(
            "owner-repo-sha/.github/workflows/ci.yml", "on: pull_request\n"
        )
    original = snapshot.read_bytes()

    with extracted_source_snapshot(snapshot) as repository:
        assert (
            repository / ".github/workflows/ci.yml"
        ).read_text() == "on: pull_request\n"
    assert not repository.exists()

    with (
        pytest.raises(RuntimeError, match="consumer failed"),
        extracted_source_snapshot(snapshot) as repository,
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
    with ZipFile(snapshot, "w") as source_zip:
        source_item = ZipInfo(filename)
        source_item.filename = (
            filename  # Preserve backslashes when creating on Windows.
        )
        source_zip.writestr(source_item, "unsafe")
    with (
        pytest.raises(SourceSnapshotError, match="safely extract"),
        extracted_source_snapshot(snapshot),
    ):
        pytest.fail("Unsafe source ZIP was accepted")
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("file_type", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR])
def test_rejects_links_and_special_files(tmp_path: Path, file_type: int) -> None:
    snapshot = tmp_path / "repository.zip"
    source_item = ZipInfo("root/link")
    source_item.create_system = 3
    source_item.external_attr = (file_type | 0o777) << 16
    with ZipFile(snapshot, "w") as source_zip:
        source_zip.writestr(source_item, "/etc/passwd")
    with pytest.raises(SourceSnapshotError), extracted_source_snapshot(snapshot):
        pytest.fail("Special file was accepted")


@pytest.mark.parametrize("names", [[], ["first/a", "second/b"], ["root/a", "root/a/b"]])
def test_rejects_empty_multiple_root_and_conflicting_archives(
    tmp_path: Path, names: list[str]
) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as source_zip:
        for name in names:
            source_zip.writestr(name, "content")
    with pytest.raises(SourceSnapshotError), extracted_source_snapshot(snapshot):
        pytest.fail("Invalid source ZIP was accepted")


@pytest.mark.parametrize("limit", ["MAX_EXTRACTED_BYTES", "MAX_EXTRACTED_ITEMS"])
def test_limits_extraction_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: str
) -> None:
    snapshot = tmp_path / "repository.zip"
    with ZipFile(snapshot, "w") as source_zip:
        source_zip.writestr("root/file", "content")
    monkeypatch.setattr(source_snapshot, limit, 0)
    with pytest.raises(SourceSnapshotError), extracted_source_snapshot(snapshot):
        pytest.fail("Extraction limit was ignored")


def test_corrupt_zip_is_expected_error(tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    snapshot.write_bytes(b"not a zip")
    with pytest.raises(SourceSnapshotError), extracted_source_snapshot(snapshot):
        pytest.fail("Corrupt source ZIP was accepted")


def test_corrupt_compressed_content_is_expected_error(tmp_path: Path) -> None:
    snapshot = tmp_path / "repository.zip"
    filename = "root/file"
    with ZipFile(snapshot, "w", compression=ZIP_DEFLATED) as source_zip:
        source_zip.writestr(filename, "content")
    content = bytearray(snapshot.read_bytes())
    # The file data follows the 30-byte ZIP header and filename.
    content[30 + len(filename)] = 0x07  # Reserved DEFLATE block type.
    snapshot.write_bytes(content)
    with pytest.raises(SourceSnapshotError), extracted_source_snapshot(snapshot):
        pytest.fail("Corrupt compressed data was accepted")
