# Architecture

Both local and GitHub Actions runs follow the same path:

```text
Command-line command / GitHub Actions (manual)
                    |
                    v
                 app.py <--- .env / environment
                    |   <--- config/repositories.yml
                    |   <--- rules/registry.py
                    v
                runner.py
          For each repository:
          skip exempt rules,
          check GitHub access,
          download main ZIP if needed
                    |
          +---------+---------+
          |                   |
          v                   v
   Deterministic rules    Agentic rules
   GitHub API / ZIP      Agent Framework
          |              Azure OpenAI +
          |              Serena in Docker
          |                   |
          +---------+---------+
                    |
                    v
              Rule results
                    |
                    v
                report.py
                    |
                    v
         app.py writes compliance-report.md
                    |
                    v
       Actions: summary + report artifact
```

Repositories run in configuration order; rules run in registry order. Source rules share one temporary ZIP per repository.

For AI checks, Serena reads extracted source files in Docker. The Python process sends the prompt and inspected content to Azure OpenAI. Serena has read-only source access and no network access. Temporary files and containers are cleaned up after evaluation.

Expected check errors become `ERROR` results while other checks continue. See the [package guide](package-layout.md) for code responsibilities.
