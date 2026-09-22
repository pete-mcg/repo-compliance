# Contributing

Follow the [quick start](getting-started.md) to install uv, Task, Python, and dependencies. Use PowerShell from the repository root. Unit tests do not need Docker, Azure, or credentials.

## Keep changes simple

- Write obvious, readable code. Avoid unnecessary layers and abstractions.
- Give each function one job. Keep high-level steps separate from low-level details.
- Keep changes focused. Update the relevant docs and review your own diff.
- Follow the [package boundaries](package-layout.md) and [rule structure](rules.md).

## Tests

Unit tests check small pieces of code using fake services. Mirror `src/repo_compliance/` beneath `tests/unit/`, and prefix test filenames with `test_`:

```text
src/repo_compliance/rules/deterministic/codeowners_present.py
tests/unit/rules/deterministic/test_codeowners_present.py
```

Cover passing, failing, and expected error cases where relevant. Reuse [tests/unit/fakes.py](../tests/unit/fakes.py) for GitHub and AI responses.

Integration tests check real services. Keep them in `tests/integration/`, mark them `integration` and either `serena` or `azure`, and put sample repositories in `tests/fixtures/`.

```powershell
# Unit tests; integration tests are excluded by default.
uv run --locked pytest

# Real Serena: requires Docker and the image from the quick start.
uv run --locked pytest -m serena tests/integration

# Live AI checks: also requires all four settings and az login.
uv run --locked pytest -m azure tests/integration
```

Azure tests send fixture files to the configured deployment and use paid model calls. They are optional and excluded from the quality gate.

## Before opening a pull request

```powershell
task ci
```

This checks code style, formatting, dependencies, types, and unit tests. Test coverage must reach 85%, including branches through the code.

For changes that affect a run, run the checker and inspect its report too. Complete the [pull request template](../.github/pull_request_template.md) and use a title such as `docs: explain rule setup` or `fix: handle missing workflows`.
