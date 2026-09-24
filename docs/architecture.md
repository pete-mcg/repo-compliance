# Architecture

Both local and GitHub Actions runs follow the same path:

```mermaid
flowchart TD
    command["Command-line command / GitHub Actions (manual)"] --> app[app.py]
    environment[.env / environment] --> app
    repositories[config/repositories.yml] --> app
    registry[rules/registry.py] --> app
    app --> runner[runner.py<br/>For each repository:<br/>skip exempt rules,<br/>check GitHub access,<br/>download main ZIP if needed]
    runner --> deterministic[Deterministic rules<br/>GitHub API / ZIP]
    runner --> agentic[Agentic rules<br/>Agent Framework<br/>Azure OpenAI +<br/>read-only file server in Docker]
    deterministic --> results[Rule results]
    agentic --> results
    results --> report[report.py]
    report --> write[app.py writes compliance-report.md]
    write --> actions[Actions: summary + report artifact]
```

- Repositories run in configuration order; rules run in registry order.
- Source rules share one temporary ZIP per repository.
- For AI checks, the project-owned MCP server reads extracted source files in Docker. It can only list files, search literal text, and read numbered lines. The Python process sends the prompt and inspected content to Azure OpenAI. The server has read-only source access and no network access. Temporary files and containers are cleaned up after evaluation.
- Expected check errors become `ERROR` results while other checks continue.
