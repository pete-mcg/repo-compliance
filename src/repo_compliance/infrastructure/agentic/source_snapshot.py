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
        with ZipFile(snapshot_path) as source_archive:
            source_items = source_archive.infolist()
            _validate_source_items(source_items)
            for source_item in source_items:
                _extract_source_item(source_archive, source_item, destination)
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


def _validate_source_items(source_items: list[ZipInfo]) -> None:
    if not source_items or len(source_items) > MAX_EXTRACTED_ITEMS:
        raise ValueError("Source snapshot contains too many items.")
    if sum(source_item.file_size for source_item in source_items) > MAX_EXTRACTED_BYTES:
        raise ValueError("Source snapshot is too large to extract.")

    roots: set[str] = set()
    for source_item in source_items:
        path = _validated_source_item_path(source_item)
        roots.add(path.parts[0])
    if len(roots) != 1:
        raise ValueError("Expected one GitHub snapshot root directory.")


def _validated_source_item_path(source_item: ZipInfo) -> PurePosixPath:
    path = safe_relative_path(source_item.orig_filename.removesuffix("/"))
    file_type = stat.S_IFMT(source_item.external_attr >> 16)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ValueError("Source snapshot contains a link or special file.")
    if source_item.flag_bits & 1:
        raise ValueError("Source snapshot contains an encrypted item.")
    if len(path.parts) < 2 and not source_item.is_dir():
        raise ValueError("Source snapshot item is outside the wrapper directory.")
    return path


def _extract_source_item(
    source_archive: ZipFile, source_item: ZipInfo, destination: Path
) -> None:
    path = _validated_source_item_path(source_item)
    target = destination.joinpath(*path.parts[1:])
    if source_item.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with source_archive.open(source_item) as source, target.open("xb") as output:
        shutil.copyfileobj(source, output)
