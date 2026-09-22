# Contributing

## Keep changes simple

- Write obvious, readable code. Avoid unnecessary layers and abstractions.
- Give each function one job. Keep high-level steps separate from low-level details.
- Keep changes focused. Update the relevant docs and review your own diff.
- Follow the [package boundaries](package-layout.md) and [rule structure](rules.md).

## Tests

- Mirror `src/repo_compliance/` beneath `tests/unit/`, and prefix test filenames with `test_`:
- Integration tests check real services. Keep them in `tests/integration/`, mark them `integration` and either `serena` or `azure`, and put sample repositories in `tests/fixtures/`.

```powershell
# Unit tests; integration tests are excluded by default.
uv run --locked pytest

# Real Serena: requires Docker and the Serena image
uv run --locked pytest -m serena tests/integration

# Live AI checks: also requires all settings configured and az login.
uv run --locked pytest -m azure tests/integration
```

Azure tests send fixture files to the configured deployment and use paid model calls. They are optional and excluded from the quality gate.

## Before opening a pull request

1. Check the quality-gate command passes:

```powershell
task ci
```

This checks code style, formatting, dependencies, types, and unit tests. Test coverage must reach 85%.

2. Run the checker and manually inspect its report.