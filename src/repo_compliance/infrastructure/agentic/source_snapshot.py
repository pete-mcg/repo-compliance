"""Safely extract a GitHub source ZIP for temporary, read-only inspection."""

import ntpath
import shutil
import stat
import zlib
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, LargeZipFile, ZipFile, ZipInfo

from repo_compliance.errors import SourceSnapshotError

MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_EXTRACTED_ITEMS = 20_000


def safe_relative_path(value: str) -> PurePosixPath:
    """Reject traversal and names unsafe on either Windows or Linux."""
    parts = value.split("/")
    if any(part in {"", ".", ".."} or ntpath.isreserved(part) for part in parts):
        raise ValueError("Unsafe source path.")
    if "\\" in value or ":" in value:
        raise ValueError("Unsafe source path.")
    return PurePosixPath(value)


@contextmanager
def extracted_snapshot(snapshot_path: Path) -> Generator[Path]:
    """Yield the repository root, removing extracted files even after failure."""
    with TemporaryDirectory(prefix="repo-compliance-source-") as temporary_directory:
        destination = Path(temporary_directory)
        _extract_snapshot(snapshot_path, destination)
        yield destination


def _extract_snapshot(snapshot_path: Path, destination: Path) -> None:
    try:
        with ZipFile(snapshot_path) as archive:
            entries = archive.infolist()
            _validate_archive(entries)
            for entry in entries:
                _extract_entry(archive, entry, destination)
    except (
        BadZipFile,
        LargeZipFile,
        OSError,
        ValueError,
        NotImplementedError,
        RuntimeError,
        zlib.error,
    ) as error:
        raise SourceSnapshotError(
            "Could not safely extract the source snapshot."
        ) from error


def _validate_archive(entries: list[ZipInfo]) -> None:
    if not entries or len(entries) > MAX_EXTRACTED_ITEMS:
        raise ValueError("Source snapshot contains too many items.")
    if sum(entry.file_size for entry in entries) > MAX_EXTRACTED_BYTES:
        raise ValueError("Source snapshot is too large to extract.")

    roots: set[str] = set()
    for entry in entries:
        path = _validated_entry_path(entry)
        roots.add(path.parts[0])
    if len(roots) != 1:
        raise ValueError("Expected one GitHub snapshot root directory.")


def _validated_entry_path(entry: ZipInfo) -> PurePosixPath:
    path = safe_relative_path(entry.orig_filename.removesuffix("/"))
    file_type = stat.S_IFMT(entry.external_attr >> 16)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ValueError("Source snapshot contains a link or special file.")
    if entry.flag_bits & 1:
        raise ValueError("Source snapshot contains an encrypted entry.")
    if len(path.parts) < 2 and not entry.is_dir():
        raise ValueError("Source snapshot entry is outside the wrapper directory.")
    return path


def _extract_entry(archive: ZipFile, entry: ZipInfo, destination: Path) -> None:
    path = _validated_entry_path(entry)
    target = destination.joinpath(*path.parts[1:])
    if entry.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(entry) as source, target.open("xb") as output:
        shutil.copyfileobj(source, output)
