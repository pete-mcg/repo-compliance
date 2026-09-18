"""Detect source markers associated with key-based authentication."""

import re
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, LargeZipFile, ZipFile, ZipInfo

from repo_compliance.domain import (
    Confidence,
    Evidence,
    RuleCategory,
    RuleContext,
    RuleDefinition,
    RuleEvaluation,
)
from repo_compliance.errors import SourceSnapshotError

RULE_ID = "no-key-based-authentication"
MAX_FILE_BYTES = 1024 * 1024
MAX_EVIDENCE = 20
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".next",
        ".nuxt",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "bin",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "obj",
        "out",
        "target",
        "vendor",
        "venv",
    }
)
MARKER_NAMES = {
    "x_api_key": "x-api-key",
    "shared_access_key": "shared-access-key",
    "api_key": "api-key",
    "access_key": "access-key",
    "secret_key": "secret-key",
    "account_key": "account-key",
    "subscription_key": "subscription-key",
}
KEY_MARKER = re.compile(
    r"(?P<x_api_key>x[-_]?api[-_]?key)"
    r"|(?P<shared_access_key>shared[-_]?access[-_]?key(?:name)?)"
    r"|(?P<api_key>api[-_]?key)"
    r"|(?P<access_key>access[-_]?key)"
    r"|(?P<secret_key>secret[-_]?key)"
    r"|(?P<account_key>account[-_]?key)"
    r"|(?P<subscription_key>subscription[-_]?key)",
    re.IGNORECASE,
)


def check(context: RuleContext) -> RuleEvaluation:
    """Scan safe UTF-8 source snapshot entries for key authentication markers."""
    if context.source_snapshot_path is None:
        raise RuntimeError("Rule requires a source snapshot.")

    evidence, total = _scan_source_snapshot(context.source_snapshot_path)
    if total == 0:
        return RuleEvaluation(True, "No key-based authentication markers found.")

    return RuleEvaluation(
        passed=False,
        message=f"Found {total} possible key-based authentication marker(s).",
        evidence=evidence,
        omitted_evidence_count=total - len(evidence),
    )


def _scan_source_snapshot(
    source_snapshot_path: Path,
) -> tuple[tuple[Evidence, ...], int]:
    try:
        source_snapshot = ZipFile(source_snapshot_path)
    except (BadZipFile, LargeZipFile, OSError) as error:
        raise SourceSnapshotError("Could not inspect the source snapshot.") from error
    with source_snapshot:
        return _scan_entries(source_snapshot)


def _scan_entries(source_zip: ZipFile) -> tuple[tuple[Evidence, ...], int]:
    evidence: list[Evidence] = []
    total = 0
    for entry in source_zip.infolist():
        entry_evidence = _entry_evidence(source_zip, entry)
        total += len(entry_evidence)
        remaining = MAX_EVIDENCE - len(evidence)
        evidence.extend(entry_evidence[:remaining])
    return tuple(evidence), total


def _entry_evidence(source_zip: ZipFile, entry: ZipInfo) -> tuple[Evidence, ...]:
    path = _scannable_path(entry)
    if path is None:
        return ()

    text = _read_text(source_zip, entry)
    if text is None:
        return ()

    evidence: list[Evidence] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        evidence.extend(_line_evidence(path, line_number, line))
    return tuple(evidence)


def _read_text(source_zip: ZipFile, entry: ZipInfo) -> str | None:
    try:
        content = source_zip.read(entry)
    except (BadZipFile, NotImplementedError, OSError, RuntimeError) as error:
        raise SourceSnapshotError(
            "Could not read a file in the source snapshot."
        ) from error
    if _is_binary(content):
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _is_binary(content: bytes) -> bool:
    return any(byte < 9 or 13 < byte < 32 for byte in content)


def _line_evidence(
    path: PurePosixPath,
    line_number: int,
    line: str,
) -> tuple[Evidence, ...]:
    return tuple(
        Evidence(str(path), line_number, marker) for marker in _markers_in(line)
    )


def _scannable_path(entry: ZipInfo) -> PurePosixPath | None:
    if entry.is_dir() or entry.file_size > MAX_FILE_BYTES:
        return None

    source_path = PurePosixPath(entry.filename)
    if len(source_path.parts) < 2:
        return None

    repository_path = PurePosixPath(*source_path.parts[1:])
    directory_names = {part.casefold() for part in repository_path.parts[:-1]}
    if directory_names & EXCLUDED_DIRECTORIES:
        return None
    return repository_path


def _markers_in(line: str) -> tuple[str, ...]:
    markers: list[str] = []
    for match in KEY_MARKER.finditer(line):
        group = match.lastgroup
        if group is None:
            continue
        marker = MARKER_NAMES[group]
        if marker not in markers:
            markers.append(marker)
    return tuple(markers)


RULE = RuleDefinition(
    id=RULE_ID,
    title="No key-based authentication",
    description="Tracked source must not use key-based authentication markers.",
    category=RuleCategory.DETERMINISTIC,
    confidence=Confidence.MEDIUM,
    documentation_url="https://confluence.example.com/display/COMPLIANCE/no-key-based-authentication",
    check=check,
    requires_source_snapshot=True,
)
