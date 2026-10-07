# Architecture

Both local and GitHub Actions runs follow the same path:

```mermaid
flowchart TD
    command["Local CLI or GitHub Actions"] --> app[app.py]
    environment[.env locally or environment variables in Actions] --> app
    repositories[config/repositories.yml] --> app
    registry[rules/registry.py] --> app
    app --> runner[runner.py<br/>For each repository:<br/>skip exempt rules,<br/>check GitHub access,<br/>download main ZIP if needed]
    runner --> deterministic[Deterministic rules<br/>GitHub REST API / ZIP]
    runner --> agentic[Agentic rules<br/>Agent Framework<br/>Azure OpenAI +<br/>Serena in Docker]
    deterministic --> results[Rule results]
    agentic --> results
    results --> report[report.py]
    report --> write[compliance-report.md]
    write --> actions[GitHub Actions: report artifact]
```

- Repositories run in configuration order; rules run in registry order.
- Source rules share one temporary ZIP per repository.
- For AI checks, Serena reads extracted source files in Docker. The Python process sends the prompt and inspected content to Azure OpenAI. Serena has read-only source access and no network access. Temporary files and containers are cleaned up after evaluation.
- Expected check errors become `ERROR` results while other checks continue.
