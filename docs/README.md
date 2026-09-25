# Repository compliance

Our live-service team maintains many applications across separate GitHub repositories. As we agree on common engineering and security standards, we need a way to see which repositories meet them and which need attention. An example is requiring `.github/CODEOWNERS` on the `main` branch.

This project checks a configured list of repositories against those standards and produces one Markdown report. It reports findings; it does not change the repositories. The same Python command runs locally or in GitHub Actions. Python owns the configuration, rule logic, and report; Actions supplies credentials, runs the command, and publishes the report. The workflow can be triggered manually (a schedule is planned but is not enabled yet).

## Where to make changes

- Add or remove monitored repositories in [config/repositories.yml](../config/repositories.yml). You can also give a repository a reasoned exemption from a particular rule there.
- Add or change rules in [src/repo_compliance/rules/](../src/repo_compliance/rules/). Each rule has its own file, grouped by evaluation method: `deterministic/` for direct checks and `agentic/` for AI-assisted judgments. Enable rules in [registry.py](../src/repo_compliance/rules/registry.py). See [Adding and removing rules](rules.md) for the steps.

Checks may have different levels of certainty. Direct checks use GitHub data or repository files; AI-assisted checks inspect source and may return an uncertain result.

## Guides

- [Quick start](getting-started.md): install, configure, and run.
- [Contributing](contributing.md): code style, tests, and quality checks.
- [Adding and removing rules](rules.md): rule structure, prompts, and registration.
- [Architecture](architecture.md): a diagram of how a run works.
- [Package guide](package-layout.md): where code belongs and how modules depend on each other.
