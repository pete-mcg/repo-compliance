# Repository Compliance Checker

## Configure repositories

Edit [`config/repositories.yml`](config/repositories.yml).

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

## Running

### Locally

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

### Via GitHub Actions

Add the PAT as repository secret `REPO_COMPLIANCE_TOKEN`. [`repository-compliance.yml`](.github/workflows/repository-compliance.yml) runs at `06:00 UTC` on weekdays and supports manual runs. It appends the report to the workflow summary and uploads artifact `repository-compliance-report`.

## Manage rules

Rule code lives under [`src/repo_compliance/rules`](src/repo_compliance/rules), grouped by evaluation method:

- `deterministic/` for repeatable API and source checks
- `agentic/` for future reasoning-based checks

Each rule has its own file and exports immutable `RULE` metadata plus a typed `check` function.
To add a rule, create the file and its corresponding test under `tests/rules/`, then add its `RULE` to the ordered tuple in [`registry.py`](src/repo_compliance/rules/registry.py).
To remove a rule, remove its source, tests, registry entry, and any configuration or documentation referring to its ID.
Repositories appear in configuration order, with rules in registry order.

## Architecture and development

- The checker uses a small layered structure: `domain.py` holds shared compliance types, `ports.py` defines external capability contracts, `runner.py` coordinates checks, and `infrastructure/github/` contains the GitHub client and shared response models. The CLI connects these parts; individual rules own their compliance criteria and rule-specific response parsing.

See the [architecture overview](docs/architecture.md) for the runtime flow and the [package guide](src/repo_compliance/README.md) for module responsibilities and dependency directions.

- Tests mirror the source structurel
- Quality gate command:

```text
task ci
```
