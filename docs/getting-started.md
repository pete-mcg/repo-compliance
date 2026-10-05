# Quick start

This tool may be run locally on your developer machine or via GitHub Actions.

## Run Locally

### 1. Install pre-requisite tools

- [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage Python
- [Task](https://taskfile.dev/docs/installation) to run project commands
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows) to sign in
- [Rancher Desktop](https://docs.rancherdesktop.io/getting-started/installation/#windows) to run `docker` commands

### 2. Install Python dependencies

```shell
task install
```

### 3. Choose repositories

Edit [config/repositories.yml](../config/repositories.yml). Revisit this only when repositories or exemptions change:

```yaml
repositories:
  - repository: example/service-api
    exemptions:
      - rule: deploy-workflow-present
        reason: This service has no deployment.
  - repository: example/admin-ui
```

- An exemption skips one rule for one repository.
- Its ID must appear in the [rule registry](../src/repo_compliance/rules/registry.py), with a non-empty reason.

### 4. Configure access

#### 4.1. Create a GitHub Personal Access Token

**Option 1: Tokens (classic)**

Select the following scopes:

- repo (repo:status, repo_deployment, public_repo, repo:invite, security_events)
- read:packages

**Option 2: Fine-grained token**

For the monitored repositories, grant read access to:

- Metadata
- Contents
- Checks
- Commit statuses
- Administration
- Dependabot alerts

#### 4.2. Create a `.env`

Copy `.env.example` into a `.env`. Configure:

| Setting                    | Value                                                                       |
| -------------------------- | --------------------------------------------------------------------------- |
| `GITHUB_TOKEN`             | Your GitHub token.                                                          |
| `AZURE_OPENAI_ENDPOINT`    | Your resource URL: `https://<resource>.openai.azure.com`.                   |
| `AZURE_OPENAI_DEPLOYMENT`  | Your Azure model deployment name.                                           |
| `AZURE_OPENAI_API_VERSION` | The API version supported by your deployment, such as `YYYY-MM-DD-preview`. |

Note that all settings are required at startup, even if agentic rules are not used.

### 5. Sign in to Azure

```shell
az login
```

Repeat `az login` when Azure requires a fresh sign-in or you switch accounts.

### 6. Build the MCP image

With Rancher Desktop running, run following command from the repository root:

```shell
docker build --tag repo-compliance-serena mcp
```

Repeat the build if the local image is removed or `mcp/Dockerfile` changes.

### 7. Run the checker

With Rancher Desktop running, run the following command from the repository root:

```shell
uv run repo-compliance
```

When finished, output is `compliance-report.md` in the repository root.

## Run via GitHub Actions

Set this up once. In the repository's **Settings > Secrets and variables > Actions**, add:

- Secret: `REPO_COMPLIANCE_TOKEN` (the GitHub token).
- Variables:
  - `AZURE_CLIENT_ID`
  - `AZURE_TENANT_ID`
  - `AZURE_SUBSCRIPTION_ID`
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_DEPLOYMENT`
  - `AZURE_OPENAI_API_VERSION`

For each run, select **Actions > Repository compliance > Run workflow**. Scheduled runs are TBC.
