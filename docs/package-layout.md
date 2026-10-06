# Package guide

All paths below are inside [src/repo_compliance/](../src/repo_compliance/).

## Layers and responsibilities

A layer is a group of responsibilities. It can be one file; it does not need its own folder.

| Location                                 | Responsibility                                                                          |
| ---------------------------------------- | --------------------------------------------------------------------------------------- |
| `app.py`, `__main__.py`                  | Start the tool, connect the parts, and write the report.                                |
| `config.py`                              | Read and validate the `config/repositories.yml`.                                        |
| `settings.py`                            | Load and validate environment / `.env` settings.                                        |
| `domain.py`                              | Define shared rule inputs, evaluations, results, and service interfaces.                |
| `runner.py`                              | Runs the rules (apply rule exemptions, check repository access, share source downloads) |
| `report.py`                              | Turn completed results into Markdown.                                                   |
| `errors.py`                              | Define expected errors.                                                                 |
| `timing.py`                              | Define timing helper.                                                                   |
| `infrastructure/github/`                 | Make GitHub requests and define shared response models.                                 |
| `infrastructure/source/`                 | Safely extract temporary source files and remove them afterwards.                       |
| `infrastructure/agentic/`                | Connect Azure and MCP Server, run AI checks, and validate replies.                      |
| `rules/registry.py`                      | List enabled rules in order.                                                            |
| `rules/deterministic/`, `rules/agentic/` | Contains each rule. Decides whether each rule is met.                                   |

## Boundaries to preserve

| Part | Boundary |
| --- | --- |
| Application (`app.py`) | Connects the parts. Leaves compliance decisions to rules, running checks to the runner, and formatting results to reporting. |
| Runner (`runner.py`) | Must not import individual rules, the rule registry or service code. Receives rules and services from `app.py`. |
| Individual rules (`rules/deterministic/`, `rules/agentic/`) | Must not import other rules, the rule registry or service code. Use services supplied through `RuleContext`. |
| Infrastructure (`infrastructure/`) | Must not import rules, the runner, reporting or `app.py`. Provides services without deciding which rules to run. |
| Reporting (`report.py`) | Must not import rules, the runner or service code. Formats supplied results without running checks or contacting services. |
| Shared types and utilities (`domain.py`, `errors.py`, `timing.py` and GitHub response models) | Must not import application wiring, rules or service code. Remain independent of the parts that use them. |

- Rules may share helpers and import GitHub response models, which describe data without contacting GitHub.
- `domain.py`, `errors.py` and `timing.py` use only Python's standard library.
- Avoid circular dependencies, where imports form a loop.
