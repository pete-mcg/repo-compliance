# Package guide

All paths below are inside [src/repo_compliance/](../src/repo_compliance/).

## Layers and responsibilities

A layer is a group of responsibilities. It can be one file; it does not need its own folder.

| Location                                 | Responsibility                                                           |
| ---------------------------------------- | ------------------------------------------------------------------------ |
| `app.py`, `__main__.py`                  | Start the command, connect the parts, and write the report.              |
| `config.py`                              | Read and validate repositories and exemptions from YAML.                 |
| `settings.py`                            | Load and validate environment and `.env` settings.                       |
| `domain.py`                              | Define shared rule inputs, evaluations, results, and service interfaces. |
| `runner.py`                              | Apply exemptions, check access, share source downloads, and run rules.   |
| `report.py`                              | Turn completed results into Markdown.                                    |
| `errors.py`                              | Define expected errors.                                                  |
| `timing.py`                              | Define log function timings.                                             |
| `infrastructure/github/`                 | Make GitHub requests and define shared response models.                  |
| `infrastructure/source/`                 | Safely extract temporary source files and remove them afterwards.        |
| `infrastructure/agentic/`                | Connect Azure and Serena, run AI checks, and validate replies.           |
| `rules/registry.py`                      | List enabled rules in order.                                             |
| `rules/deterministic/`, `rules/agentic/` | Decide whether each standard is met.                                     |

## Dependency direction

An arrow means "may import from". This list is complete: **no arrow means the import is forbidden**, even within the same folder. Permission goes only in the shown direction; following several arrows does not permit a direct import.

Names are inside `repo_compliance`.

```text
__main__ -> app
__init__ -> domain
app -> config, settings, runner, report, errors, rules.registry
app -> infrastructure.github.client, infrastructure.agentic.agent_framework
rules.registry -> individual rules
runner -> config, domain, errors, timing
report -> config, domain
individual rules -> domain, errors, infrastructure.github.models
rules.agentic rule modules -> rules.agentic.helpers
rules.agentic.helpers -> domain, errors
infrastructure.github.client -> errors, infrastructure.github.models
infrastructure.agentic.agent_framework -> domain, errors, settings
infrastructure.agentic.agent_framework -> infrastructure.source.source_snapshot
infrastructure.source.source_snapshot -> errors
config, settings -> errors
domain, errors, timing, infrastructure.github.models -> (no internal imports)
```

Note:

- `individual rules` excludes helpers and the registry.
- This list covers all internal imports, including those inside functions or used only for type checks.
- `domain.py`, `errors.py`, and `timing.py` use only Python's standard library.
- The application passes rules and services to the runner. Rules use services through `RuleContext`. Neither imports service implementations. Rules may import shared GitHub models because these describe data and make no service calls.

Import restrictions are checked during review, not automatically. Review and update this list before adding a new dependency.
