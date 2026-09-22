# Quick start

Use Windows PowerShell. Run project commands from the repository root: the folder containing `Taskfile.yml`.

Complete setup once per computer and project folder. For later runs, go to [Run the checker](#run-the-checker).

## First-time setup

### 1. Install tools and dependencies

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage Python, [Task](https://taskfile.dev/docs/installation) to run project commands, and [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows) to sign in:

```powershell
winget install --id astral-sh.uv --exact
winget install --id Task.Task --exact
winget install --id Microsoft.AzureCLI --exact
```

Install and start [Rancher Desktop](https://docs.rancherdesktop.io/getting-started/installation/#windows). Under **Preferences > Container Engine**, select [dockerd (moby)](https://docs.rancherdesktop.io/ui/preferences/container-engine/general/). This provides the `docker` command used by the checker.

Reopen PowerShell, return to the repository root, and install Python 3.14 and the project dependencies:

```powershell
uv python install 3.14
task install
```

`task install` runs `uv sync --locked`, using the versions in `uv.lock`. You do not need to repeat it before each run or activate the Python environment.

### 2. Choose repositories

Edit [config/repositories.yml](../config/repositories.yml). Revisit this only when repositories or exemptions change:

```yaml
repositories:
  - repository: example/service-api
    exemptions:
      - rule: deploy-workflow-present
        reason: This service has no deployment.
  - repository: example/admin-ui
```

Use `owner/name`, without a URL. File and source checks target `main`, even if the repository has a different default branch.

An exemption skips one rule for one repository. Its ID must appear in the [rule registry](../src/repo_compliance/rules/registry.py), with a non-empty reason. Duplicate repositories and duplicate exemptions are rejected. `repositories: []` checks nothing.

### 3. Configure access

Create a GitHub fine-grained personal access token covering the monitored repositories. Grant read access to Metadata, [Contents](https://docs.github.com/en/rest/repos/contents), [Administration](https://docs.github.com/en/rest/branches/branch-protection#get-branch-protection), and [Dependabot alerts](https://docs.github.com/en/rest/dependabot/alerts#list-dependabot-alerts-for-a-repository).

Copy the settings template once, then replace its placeholders in `.env`. Skip the copy if `.env` already exists; update its values when credentials or Azure settings change:

```powershell
Copy-Item .env.example .env
```

| Setting | Value |
| --- | --- |
| `GITHUB_TOKEN` | Your GitHub token. |
| `AZURE_OPENAI_ENDPOINT` | Your resource URL: `https://<resource>.openai.azure.com`. |
| `AZURE_OPENAI_DEPLOYMENT` | Your Azure model deployment name. |
| `AZURE_OPENAI_API_VERSION` | The API version supported by your deployment, such as `YYYY-MM-DD-preview`. |

Get the Azure values from your team. Your signed-in account needs [Cognitive Services OpenAI User](https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/role-based-access-control?view=foundry-classic) access on that resource.

All four settings are required at startup, even when AI checks are skipped. PowerShell environment variables, such as `$env:GITHUB_TOKEN = "your-token"`, override `.env`. Git ignores `.env`; keep real credentials out of `.env.example`.

### 4. Sign in and download the image

Sign in to Azure and download the Serena image once. Serena provides the AI rule's file-reading tools.

```powershell
az login
docker pull ghcr.io/oraios/serena:1.7.0@sha256:6c9459e4246a39c9deaa4f23fb05a526ac6e237b24c8e84a927a098fa1ab6730
```

- Repeat `az login` when Azure requires a fresh sign-in or you switch accounts.
- Repeat `docker pull` only if the local image is removed or the project changes the required image version. The checker reuses the local image and never downloads it during a run.

## Run the checker

Ensure Rancher Desktop is running, then run:

```powershell
uv run repo-compliance
```

[uv syncs dependencies automatically](https://docs.astral.sh/uv/concepts/projects/sync/), reusing installed packages where possible. `--locked` is optional: it stops with an error if `uv.lock` needs updating, instead of updating it.

AI checks send inspected source content to your configured Azure OpenAI resource and use paid model calls.

Open `compliance-report.md` in the repository root. Each run replaces it.

| Result | Meaning |
| --- | --- |
| `PASS` | The rule is satisfied. |
| `FAIL` | The rule found a problem. |
| `EXEMPT` | The configuration skips this rule. |
| `ERROR` | The checker could not judge the rule. Read its message. |

Exit code `0` means the report was written, including reports with `FAIL` or `ERROR` results. Setup failures, write failures, and unexpected bugs return `1`.

## GitHub Actions

Set this up once. In the repository's **Settings > Secrets and variables > Actions**, add:

- Secret: `REPO_COMPLIANCE_TOKEN` (the GitHub token).
- Variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, and the three `AZURE_OPENAI_*` settings above.

Configure [Azure Login federation](https://github.com/Azure/login#login-with-openid-connect-oidc-recommended) for the branch you will run. Give that Azure identity the same resource access as your local account.

For each run, select **Actions > Repository compliance > Run workflow**. The [workflow](../.github/workflows/repository-compliance.yml) publishes the report in its summary and as the `repository-compliance-report` artifact. The schedule is currently commented out; runs are manual.
