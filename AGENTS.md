# Repository compliance

Our live-service team maintains many applications across separate GitHub repositories. As we agree on common engineering and security standards, we need a way to see which repositories meet them and which need attention. An example is requiring `.github/CODEOWNERS` on the `main` branch.

This project checks a configured list of repositories against those standards and produces one Markdown report. It reports findings; it does not change the repositories. The same Python command runs locally or in GitHub Actions. Python owns the configuration, rule logic, and report; Actions supplies credentials, runs the command, and publishes the report. The workflow can be triggered manually (a schedule is planned but is not enabled yet).

## Where to make changes

- Add or remove monitored repositories in [config/repositories.yml](../config/repositories.yml). You can also give a repository a reasoned exemption from a particular rule there.
- Add or change rules in [src/repo_compliance/rules/](../src/repo_compliance/rules/). Each rule has its own file, grouped by evaluation method: `deterministic/` for direct checks and `agentic/` for AI-assisted judgments. Enable rules in [registry.py](../src/repo_compliance/rules/registry.py). See [Adding and removing rules](rules.md) for the steps.

Checks may have different levels of certainty. Direct checks use GitHub data or repository files; AI-assisted checks inspect source and may return an uncertain result.

## Where data is sent

It's important to limit where data is sent in this repository. This checker intentionally **only** sends data to GitHub and the configured Azure OpenAI deployment; no other external services are permitted.

- **GitHub** receives authenticated requests for the configured repositories. When the checker runs in GitHub Actions, GitHub also receives the generated report as the workflow summary and an artifact.
- **Azure OpenAI** receives the prompt and source content inspected for an AI-assisted rule.

The chosen Serena MCP runs from a local Docker image. It receives a read-only local copy of the source files to inspect, but its container has no network access, so it does not send data to OrAIOS (Serena's publisher) or any other external service.

## Guides

- [Quick start](getting-started.md): install, configure, and run.
- [Contributing](contributing.md): code style, tests, and quality checks.
- [Adding and removing rules](rules.md): rule structure, prompts, and registration.
- [Architecture](architecture.md): a diagram of how a run works.
- [Package guide](package-layout.md): where code belongs and how modules depend on each other.

# Contributing

- Always simple, obvious and readable code over clever tricks; over-engineering and over-productionising are **forbidden**. This is as a lightweight, **beginner** friendly codebase. If new code fails to be simple and beginner friendly, it will not be merged.
- Function Design:
  - Do one thing per function;
  - Keep to one level of abstraction within a function;
  - Keep functions simple;
- The quality gate is `task ci`.
