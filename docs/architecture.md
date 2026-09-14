# Architecture

The checker reads a list of repositories, checks each repository against every enabled rule, and writes one Markdown report.

```text
                       START
                         |
          +--------------+--------------+
          |                             |
  GitHub Actions schedule        Developer runs locally
  or manual workflow             `repo-compliance`
          |                             |
          +--------------+--------------+
                         |
                         v
        +---------------------------------------+
        | cli.py                                |
        | Runs the whole check from start to end|
        +---------------------------------------+
             |            |             |
             v            v             v
  +----------------+  +----------+  +------------------+
  | repositories.yml|  | registry |  | GITHUB_TOKEN     |
  | Repositories and|  | Enabled  |  | Access to GitHub |
  | exemptions      |  | rules    |  +------------------+
  +----------------+  +----------+
             |            |
             +-----+------+
                   |
                   v
        +---------------------------------------+
        | runner.py                             |
        | For each repository:                  |
        | 1. applies exemptions                 |
        | 2. checks that `main` is reachable    |
        | 3. runs each enabled rule             |
        +---------------------------------------+
                   |
          +--------+--------+
          |                 |
          v                 v
  +----------------+  +--------------------------+
  | github.py      |  | rules/                   |
  | Reads settings,|  | One file per compliance  |
  | files, alerts, |  | rule. Source rules inspect|
  | and source ZIP |  | a downloaded source ZIP. |
  +----------------+  +--------------------------+
          |                 |
          +--------+--------+
                   |
                   v
        +---------------------------------------+
        | report.py                             |
        | Turns PASS, FAIL, EXEMPT, and ERROR   |
        | results into Markdown                 |
        +---------------------------------------+
                   |
                   v
             compliance-report.md
                   |
          +--------+--------+
          |                 |
     Local file       Workflow summary
                      and uploaded artifact
```

## File responsibilities

- [`.github/workflows/repository-compliance.yml`](../.github/workflows/repository-compliance.yml) schedules the hosted run, supplies the secret token, and publishes the finished report. It does not contain compliance rules.
- [`src/repo_compliance/cli.py`](../src/repo_compliance/cli.py) is the top-level application coordinator. It loads configuration, creates the GitHub client, starts the runner, generates the report, and writes it to disk.
- [`config/repositories.yml`](../config/repositories.yml) is the visible list of repositories and repository-specific rule exemptions.
- [`src/repo_compliance/config.py`](../src/repo_compliance/config.py) reads and validates that list before any checks run.
- [`src/repo_compliance/rules/registry.py`](../src/repo_compliance/rules/registry.py) is the ordered list of enabled rules. Its order becomes the report order.
- [`src/repo_compliance/runner.py`](../src/repo_compliance/runner.py) coordinates checks for each repository, skips exempt rules, confirms the `main` branch is accessible, and downloads one source archive when a rule needs it.
- [`src/repo_compliance/github.py`](../src/repo_compliance/github.py) contains all communication with GitHub. Rules ask it focused questions instead of making their own web requests.
- [`src/repo_compliance/rules/`](../src/repo_compliance/rules/) contains the actual standards, grouped by evaluation method. Each rule lives in its own file.
- [`src/repo_compliance/report.py`](../src/repo_compliance/report.py) converts collected results into `compliance-report.md`.
- [`src/repo_compliance/domain.py`](../src/repo_compliance/domain.py) defines the shared names and data shapes used by rules, the runner, and the report.

The command can enter through the `repo-compliance` script declared in [`pyproject.toml`](../pyproject.toml), or through [`src/repo_compliance/__main__.py`](../src/repo_compliance/__main__.py) when run as a Python module. Both lead to `cli.py`.
