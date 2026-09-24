"""Expose a repository snapshot through small, read-only MCP tools."""

from pathlib import Path, PurePosixPath

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

REPOSITORY = Path("/repository")
MAX_FILES = 500
MAX_MATCHES = 200
MAX_READ_LINES = 400
MAX_SEARCH_FILE_BYTES = 2 * 1024 * 1024
MAX_LINE_CHARACTERS = 2_000

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
SERVER = FastMCP(
    "repository-files",
    instructions="Read and search the repository mounted at /repository.",
    log_level="ERROR",
)


def _safe_pattern(pattern: str) -> str:
    """Reject patterns that could address files outside the repository."""
    if not pattern or "\\" in pattern or ":" in pattern:
        raise ValueError("Unsafe path pattern.")
    path = PurePosixPath(pattern)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe path pattern.")
    return pattern


def _safe_file(path: str) -> Path:
    """Return a repository file without permitting path traversal."""
    relative_path = PurePosixPath(path)
    if (
        not path
        or relative_path.is_absolute()
        or ".." in relative_path.parts
        or "\\" in path
        or ":" in path
    ):
        raise ValueError("Unsafe repository path.")
    candidate = REPOSITORY.joinpath(*relative_path.parts)
    if not candidate.is_file():
        raise ValueError("Repository file does not exist.")
    return candidate


def _matching_files(pattern: str) -> list[Path]:
    """Return matching repository files in a stable order."""
    safe_pattern = _safe_pattern(pattern)
    return sorted(path for path in REPOSITORY.glob(safe_pattern) if path.is_file())


def _relative_path(path: Path) -> str:
    """Return a repository-relative POSIX path."""
    return path.relative_to(REPOSITORY).as_posix()


def _shorten_line(line: str) -> str:
    """Bound individual source lines while making truncation visible."""
    if len(line) <= MAX_LINE_CHARACTERS:
        return line
    return line[:MAX_LINE_CHARACTERS] + "..."


def _search_file(path: Path, query: str) -> list[str]:
    """Return line-numbered literal matches from one suitable text file."""
    if path.stat().st_size > MAX_SEARCH_FILE_BYTES:
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []
    relative_path = _relative_path(path)
    return [
        f"{relative_path}:{line_number}: {_shorten_line(line)}"
        for line_number, line in enumerate(lines, start=1)
        if query in line
    ]


@SERVER.tool(annotations=READ_ONLY)
def list_files(pattern: str = "**/*") -> str:
    """List repository files matching a glob pattern, up to 500 files."""
    files = _matching_files(pattern)
    listed = files[:MAX_FILES]
    result = "\n".join(_relative_path(path) for path in listed)
    if len(files) > MAX_FILES:
        result += f"\n... {len(files) - MAX_FILES} more files"
    return result or "No matching files."


@SERVER.tool(annotations=READ_ONLY)
def search_text(query: str, pattern: str = "**/*") -> str:
    """Find literal text in matching UTF-8 repository files, with line numbers."""
    if not query:
        raise ValueError("Search query must not be empty.")
    matches: list[str] = []
    for path in _matching_files(pattern):
        matches.extend(_search_file(path, query))
        if len(matches) >= MAX_MATCHES:
            return "\n".join(matches[:MAX_MATCHES]) + "\n... more matches"
    return "\n".join(matches) or "No matches."


@SERVER.tool(annotations=READ_ONLY)
def read_lines(path: str, start_line: int = 1, end_line: int = 200) -> str:
    """Read an inclusive range of at most 400 numbered lines from a UTF-8 file."""
    if start_line < 1 or end_line < start_line:
        raise ValueError("Line range must be positive and ordered.")
    if end_line - start_line + 1 > MAX_READ_LINES:
        raise ValueError(f"Cannot read more than {MAX_READ_LINES} lines at once.")
    source_file = _safe_file(path)
    if source_file.stat().st_size > MAX_SEARCH_FILE_BYTES:
        raise ValueError("Repository file is too large to read.")
    lines = source_file.read_text(encoding="utf-8").splitlines()
    if start_line > len(lines):
        raise ValueError("Start line is beyond the end of the file.")
    selected = lines[start_line - 1 : end_line]
    return "\n".join(
        f"{line_number}: {_shorten_line(line)}"
        for line_number, line in enumerate(selected, start=start_line)
    )


if __name__ == "__main__":
    SERVER.run()
