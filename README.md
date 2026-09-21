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

Copy [`.env.example`](.env.example) to `.env` in the repository root:

```powershell
Copy-Item .env.example .env
```

Fill in your token and Azure OpenAI settings in `.env`, then run the checker from the repository root:

```powershell
az login
docker pull ghcr.io/oraios/serena:1.7.0@sha256:6c9459e4246a39c9deaa4f23fb05a526ac6e237b24c8e84a927a098fa1ab6730
uv run --frozen repo-compliance
```

The checker loads `.env` from the current directory and validates all four settings before running any checks, including runs with no agentic rules. Missing or malformed values are reported together. Git ignores `.env`; keep credentials out of `.env.example`.

Grant the signed-in identity **Cognitive Services OpenAI User** on that Azure OpenAI resource.

Optional paths:

```text
uv run --frozen repo-compliance --config config/repositories.yml --output compliance-report.md
```

### Via GitHub Actions

Add the following as repository secret
-  `REPO_COMPLIANCE_TOKEN`. 

Add the following as repository variables
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`,
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION` 

The client ID identifies an Entra application or user-assigned managed identity with **Cognitive Services OpenAI User** on the approved resource.

Add a federated credential to that identity with issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`, and subject `repo:<owner>/<repository>:ref:refs/heads/main` for runs on `main`. The subject must match the branch used by scheduled or manual runs. The workflow grants `id-token: write` and uses `azure/login@v3`; it then reuses the Azure CLI login through `AzureCliCredential`. See [Azure Login's OIDC setup](https://github.com/Azure/login#login-with-openid-connect-oidc-recommended). If Azure login or the image pull is attempted and fails, the workflow fails before the checker runs.

[`repository-compliance.yml`](.github/workflows/repository-compliance.yml) runs at `06:00 UTC` on weekdays and supports manual runs. It appends the report to the workflow summary and uploads artifact `repository-compliance-report`.

## Agentic rules

Serena runs locally over MCP stdio in a pinned Docker image, with a read-only filesystem and source mount, networking disabled, and separate temporary state. Only listing, reading, and searching tools are exposed. Repository `.serena` configuration is inactive; no shell, editing, REPL, dashboard, or language servers are enabled. ZIP traversal, links, special files, and excessive extraction sizes are rejected. The evaluation has a 120-second timeout, followed by bounded Docker cleanup, and removes temporary source and state.

Repository content is downloaded from GitHub and sent only to the configured approved Azure OpenAI resource for reasoning. Credentials stay outside the container. The Azure client does not follow redirects or discover proxy settings, and the checker configures no telemetry exporters or remote MCP servers. Dependency and image downloads are setup steps; runtime Docker uses the local image.

## Manage rules

Rule code lives under [`src/repo_compliance/rules`](src/repo_compliance/rules), grouped by evaluation method:

- `deterministic/` for repeatable API and source checks
- `agentic/` for reasoning-based checks with Markdown prompts

Each rule has its own file and exports immutable `RULE` metadata plus a typed `check` function. To add a rule, create the file and its corresponding test under `tests/rules/`, then add its `RULE` to the ordered tuple in [`registry.py`](src/repo_compliance/rules/registry.py). To remove a rule, remove its source, tests, registry entry, and any configuration or documentation referring to its ID.
Repositories appear in configuration order, with rules in registry order.

## Architecture and development

- The checker uses a small layered structure: `domain.py` holds shared compliance types and external capability contracts, `runner.py` coordinates checks, and `infrastructure/github/` contains the GitHub client and shared response models. The CLI connects these parts; individual rules own their compliance criteria and rule-specific response parsing.

See the [architecture overview](docs/architecture.md) for the runtime flow and the [package guide](src/repo_compliance/README.md) for module responsibilities and dependency directions.

- Tests mirror the source structure.
- Quality gate command:

```text
task ci
```

`task ci` runs offline tests without Azure credentials or Docker. To check the real local MCP server after pulling the pinned image:

```text
uv run --frozen pytest -m serena tests/integration
```

Once an approved deployment and login are available, run the live prompt fixtures:

```text
uv run --frozen pytest -m azure tests/integration
```

The live fixtures expect qualifying and unrestricted PR CI to pass; push-only, wrong-branch, and missing workflows to fail; and missing implementation evidence to produce uncertainty. These checks send only the small fixture repositories to your configured Azure resource and incur inference usage. They remain opt-in.
