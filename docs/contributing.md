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

Azure/live AI tests send fixture files to the configured deployment and use paid model calls. The live AI test uses one generic, test-only rule to check source inspection, the verdict, and evidence; it covers the infrastructure shared by all agentic rules. You do not need to add an integration test per agentic rule.

## Quality Gate

For faster checks during development, you can skip the integration tests:

```powershell
task ci
```

Before opening a pull request, all tests including integration tests must pass. Run:

```powershell
task ci:full
```
