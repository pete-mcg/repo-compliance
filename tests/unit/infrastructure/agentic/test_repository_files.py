from collections.abc import Callable
from pathlib import Path

import pytest

from repo_compliance.infrastructure.agentic import repository_files


@pytest.fixture(autouse=True)
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(repository_files, "REPOSITORY", tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text(
        "first line\nrun tests here\nlast line\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("Run tests here too.\n", encoding="utf-8")
    return tmp_path


def test_lists_matching_files_in_stable_order() -> None:
    assert repository_files.list_files() == "README.md\nsrc/app.py"
    assert repository_files.list_files("**/*.py") == "src/app.py"
    assert repository_files.list_files("**/*.yml") == "No matching files."


def test_searches_text_with_paths_and_line_numbers() -> None:
    assert repository_files.search_text("run tests", "**/*.py") == (
        "src/app.py:2: run tests here"
    )
    assert repository_files.search_text("missing") == "No matches."


def test_reads_an_inclusive_numbered_line_range() -> None:
    assert repository_files.read_lines("src/app.py", 2, 3) == (
        "2: run tests here\n3: last line"
    )


def test_bounds_file_and_line_output(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = repository / "generated.txt"
    source.write_text("12345\n", encoding="utf-8")
    monkeypatch.setattr(repository_files, "MAX_LINE_CHARACTERS", 4)
    assert repository_files.read_lines("generated.txt", 1, 1) == "1: 1234..."
    monkeypatch.setattr(repository_files, "MAX_SEARCH_FILE_BYTES", 4)
    with pytest.raises(ValueError, match="too large"):
        repository_files.read_lines("generated.txt", 1, 1)
    assert repository_files.search_text("12345") == "No matches."


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda: repository_files.list_files("../*"), "Unsafe path pattern"),
        (lambda: repository_files.read_lines("../secret"), "Unsafe repository path"),
        (lambda: repository_files.read_lines("missing.txt"), "does not exist"),
        (lambda: repository_files.read_lines("README.md", 2, 3), "beyond"),
        (lambda: repository_files.read_lines("README.md", 0, 1), "positive"),
        (lambda: repository_files.search_text(""), "must not be empty"),
    ],
)
def test_rejects_invalid_requests(operation: Callable[[], str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        operation()
