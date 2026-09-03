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
from repo_compliance.errors import ArchiveError

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


def get_evaluation(context: RuleContext) -> RuleEvaluation:
    """Scan safe UTF-8 archive entries for key authentication markers."""
    if context.archive_path is None:
        raise RuntimeError("Static analysis requires a repository archive.")

    evidence, total = _get_archive_evidence(context.archive_path)
    if total == 0:
        return RuleEvaluation(True, "No key-based authentication markers found.")

    return RuleEvaluation(
        passed=False,
        message=f"Found {total} possible key-based authentication marker(s).",
        evidence=evidence,
        omitted_evidence_count=total - len(evidence),
    )


def _get_archive_evidence(archive_path: Path) -> tuple[tuple[Evidence, ...], int]:
    try:
        archive = ZipFile(archive_path)
    except (BadZipFile, LargeZipFile, OSError) as error:
        raise ArchiveError("Could not inspect the repository archive.") from error
    with archive:
        return _get_entries_evidence(archive)


def _get_entries_evidence(archive: ZipFile) -> tuple[tuple[Evidence, ...], int]:
    evidence: list[Evidence] = []
    total = 0
    for entry in archive.infolist():
        entry_evidence = _get_entry_evidence(archive, entry)
        total += len(entry_evidence)
        remaining = MAX_EVIDENCE - len(evidence)
        evidence.extend(entry_evidence[:remaining])
    return tuple(evidence), total


def _get_entry_evidence(archive: ZipFile, entry: ZipInfo) -> tuple[Evidence, ...]:
    path = _get_scannable_path(entry)
    if path is None:
        return ()

    text = _get_entry_text(archive, entry)
    if text is None:
        return ()

    evidence: list[Evidence] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        evidence.extend(_get_line_evidence(path, line_number, line))
    return tuple(evidence)


def _get_entry_text(archive: ZipFile, entry: ZipInfo) -> str | None:
    try:
        content = archive.read(entry)
    except (BadZipFile, NotImplementedError, OSError, RuntimeError) as error:
        raise ArchiveError(
            "Could not read a file in the repository archive."
        ) from error
    if _has_binary_content(content):
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _has_binary_content(content: bytes) -> bool:
    return any(byte < 9 or 13 < byte < 32 for byte in content)


def _get_line_evidence(
    path: PurePosixPath,
    line_number: int,
    line: str,
) -> tuple[Evidence, ...]:
    return tuple(
        Evidence(str(path), line_number, marker)
        for marker in _get_line_markers(line)
    )


def _get_scannable_path(entry: ZipInfo) -> PurePosixPath | None:
    if entry.is_dir() or entry.file_size > MAX_FILE_BYTES:
        return None

    archive_path = PurePosixPath(entry.filename)
    if len(archive_path.parts) < 2:
        return None

    repository_path = PurePosixPath(*archive_path.parts[1:])
    directory_names = {part.casefold() for part in repository_path.parts[:-1]}
    if directory_names & EXCLUDED_DIRECTORIES:
        return None
    return repository_path


def _get_line_markers(line: str) -> tuple[str, ...]:
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
    category=RuleCategory.STATIC_ANALYSIS,
    confidence=Confidence.MEDIUM,
    documentation_url="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github",
    get_evaluation=get_evaluation,
)
