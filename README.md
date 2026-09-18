# Repository Compliance Checker

This repository runs a small Python checker against a visible list of GitHub repositories and writes one Markdown report. GitHub Actions schedules it; the same command works locally.

## Configure repositories

Edit [`config/repositories.yml`](config/repositories.yml). Repository names use `owner/name` format.

```yaml
repositories:
  - repository: example/service-api
    exemptions:
      - rule: deploy-workflow-present
        reason: This service has no deployment.
  - repository: example/admin-ui
    exemptions: []
```

An exemption must use an enabled rule ID and have a non-empty reason. Duplicate repositories and exemptions are rejected. An empty repository list is valid.

## Run locally

Run these commands from the repository root with uv installed. The project requires Python 3.14 or later.

Create a fine-grained personal access token and grant each monitored repository:

- Metadata: read
- Contents: read
- Administration: read
- Dependabot alerts: read

Expose the token only at the command boundary, then run the checker:

```powershell
$env:GITHUB_TOKEN = "your-token"
uv run --frozen repo-compliance
```

Optional paths:

```text
uv run --frozen repo-compliance --config config/repositories.yml --output compliance-report.md
```

The application does not depend on how the token was created. A GitHub App token can replace the PAT later without changing rule code.

## Result meanings

- `PASS`: the repository conforms to the rule.
- `FAIL`: the check completed and found a violation.
- `EXEMPT`: repository configuration explicitly exempts the rule.
- `ERROR`: the rule could not be evaluated reliably.

Violations and evaluation errors remain report data, so a completed check exits `0`. Invalid configuration, missing credentials, output failures, and checker bugs exit nonzero.

## Manage rules

Rule code lives under [`src/repo_compliance/rules`](src/repo_compliance/rules), grouped by evaluation method:

- `deterministic/` for repeatable API and source checks
- `agentic/` for future reasoning-based checks

Each rule has its own file and exports immutable `RULE` metadata plus a typed `check` function. To add a rule, create the file and its corresponding test under `tests/rules/`, then add its `RULE` to the ordered tuple in [`registry.py`](src/repo_compliance/rules/registry.py). To remove a rule, remove its source, tests, registry entry, and any configuration or documentation referring to its ID. Repositories appear in configuration order, with rules in registry order.

The initial rules check main-branch deletion protection, exact CODEOWNERS and deployment workflow paths, open Critical Dependabot alerts, and possible key-based authentication markers. Source inspection records only path, line number, and marker name; it never puts matched source lines or values in the report.

## Architecture and development

The checker uses a small layered structure: `domain.py` holds shared compliance types, `ports.py` defines external capability contracts, `runner.py` coordinates checks, and `infrastructure/github/` contains the GitHub client and shared response models. The CLI connects these parts; individual rules own their compliance criteria and rule-specific response parsing.

See the [architecture overview](docs/architecture.md) for the runtime flow and the [package guide](src/repo_compliance/README.md) for module responsibilities and dependency directions.

Tests mirror the source structure, including [`tests/infrastructure/github/test_client.py`](tests/infrastructure/github/test_client.py) for the GitHub client. With Task and uv installed, run the quality gate from the repository root:

```text
task ci
```

This checks formatting, linting, types, dependencies, and tests with coverage.

## GitHub Actions

Add the PAT as repository secret `REPO_COMPLIANCE_TOKEN`. [`repository-compliance.yml`](.github/workflows/repository-compliance.yml) runs at `06:00 UTC` on weekdays and supports manual runs. It appends the report to the workflow summary and uploads artifact `repository-compliance-report`.
