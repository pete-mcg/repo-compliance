# Package guide

All paths below are inside [src/repo_compliance/](../src/repo_compliance/).

## Layers and responsibilities

A layer is a group of responsibilities. It can be one file; it does not need its own folder.

| Location | Responsibility |
| --- | --- |
| `app.py`, `__main__.py` | Start the command, connect the parts, and write the report. |
| `config.py` | Read and validate repositories and exemptions from YAML. |
| `settings.py` | Load and validate environment and `.env` settings. |
| `domain.py` | Define shared rule inputs, evaluations, results, and service interfaces. |
| `runner.py` | Apply exemptions, check access, share source downloads, and run rules. |
| `rules/registry.py` | List enabled rules in order. |
| `rules/deterministic/`, `rules/agentic/` | Decide whether each standard is met. |
| `infrastructure/github/` | Make GitHub requests and define shared response models. |
| `infrastructure/source/` | Safely extract temporary source files and remove them afterwards. |
| `infrastructure/agentic/` | Connect Azure and Serena, run AI checks, and validate replies. |
| `report.py` | Turn completed results into Markdown. |
| `errors.py`, `timing.py` | Define expected errors and log function timings. |

## Dependency direction

An arrow means "imports from". These are the main directions:

```text
app -> config, settings, runner, report, registry, infrastructure
registry -> individual rules
runner, report -> config, domain
rules -> domain, errors, shared GitHub models
infrastructure -> domain, errors, settings
config, settings -> errors
```

`domain.py` uses only Python's standard library. Its `GitHubApi` and `AgentEvaluator` interfaces describe what a service must provide. The application supplies the real services; tests can supply fakes.

The application passes rules and services to the runner. Rules call those services through `RuleContext`. Infrastructure must not import individual rules, the registry, the runner, or reporting. Reporting only reads finished results.

## Rule slices

A rule slice means the files belonging to one rule: its Python module, test, and optional AI prompt. Keep its decisions, endpoint paths, and response models there.

Share code only when multiple rules need the same general behaviour. For example, rules may use the shared `GitHubModel`, but a response model used by one rule stays with that rule.

Adding a rule normally changes its slice and the registry. It should not require changes to the runner or report. See [Adding and removing rules](rules.md).
