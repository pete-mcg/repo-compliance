# Package guide

## Layers and responsibilities

Layers describe responsibilities and dependency boundaries. A layer can be a
single module; it does not need its own directory until that helps navigation.

| Responsibility | Location |
| --- | --- |
| Shared compliance types and external capability contracts | `domain.py` |
| Application workflow | `runner.py` |
| Individual compliance checks | `rules/` |
| External integrations | `infrastructure/` |
| Configuration input | `config.py` |
| Markdown presentation | `report.py` |
| Startup and dependency wiring | `cli.py` |
| Expected errors shared across boundaries | `errors.py` |

The shared rule types stay together in `domain.py`. Adding more rules should
normally grow `rules/`, without requiring more shared types or one file per class.

## Dependency directions

An import points from the module using a dependency to the module providing it.
The main directions are:

```text
__main__ -> cli
cli -> config, runner, report, rules.registry, infrastructure
rules.registry -> individual rule modules
runner -> config, domain, errors
report -> config, domain
rules -> domain, errors, shared GitHub response models where needed
config -> errors
infrastructure.github.client -> infrastructure.github.models, errors
infrastructure.agentic -> domain, errors
```

- `domain.py` must not import concrete integrations, the runner, reporting, or
  individual rules.
- `domain.py` describes external capabilities with Python protocols. `GitHubApi`
  and `AgentEvaluator` are the contracts used by the runner and `RuleContext`.
- The runner receives a `GitHubApi`; it does not create a `GitHubClient` or import
  individual rules. Rules are supplied explicitly by the caller.
- The CLI creates the concrete GitHub client and agent evaluator and passes them to the runner.
  `GitHubClient` satisfies the protocol by providing its methods; it does not
  need to inherit from or import `GitHubApi`.
- Infrastructure must not import individual rules, the registry, the runner,
  or reporting. It owns communication details, not compliance decisions.
- Reporting consumes completed results and does not run checks.

At runtime, the runner calls a rule's check function. The rule can call the
GitHub client through `context.github`, then return a `RuleEvaluation`. The
runner converts that evaluation to a `RuleResult` for reporting. Calling an
implementation through a supplied protocol does not require importing it.

Agent rules keep their policy in an adjacent packaged Markdown prompt. They call
`context.agent_evaluator.evaluate(snapshot_path, prompt)` and return its validated
`RuleEvaluation`. The evaluator is cheap to construct; settings, credentials, and
Docker start only during evaluation. `infrastructure/agentic/agent_framework.py`
contains provider settings, response validation, Azure client construction, and
Serena launch configuration. `source_snapshot.py` safely extracts and removes
the temporary source directory. Framework-specific imports stay in the adapter.

This is a pragmatic layered design with self-contained rules. Rules deliberately
own their endpoint selection and response validation; some import `GitHubModel`
from `infrastructure/github/models.py`. Configuration loading and its validated
models also stay together, and the runner and report use those models directly.
These are intentional boundaries, rather than a strict separation of every
business decision from every external data shape.

## Rule ownership

A rule should be a self-contained vertical slice. If a GitHub endpoint, query
parameter, response model, or validation rule exists for only one compliance
rule, keep it in that rule's module. Put behaviour in a shared module only when
it is policy-neutral and genuinely shared.

Adding a rule normally requires its source file, its test file, and one registry
entry. Removing a rule should require deleting those same items, plus any
configuration or documentation that explicitly refers to its rule ID.
