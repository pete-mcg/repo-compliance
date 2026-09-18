# Package guide

## Package layout

```text
repo_compliance/
    __init__.py
    __main__.py
    cli.py
    config.py
    domain.py
    ports.py
    errors.py
    runner.py
    report.py
    infrastructure/
        __init__.py
        github/
            __init__.py
            client.py
            models.py
    rules/
        __init__.py
        registry.py
        deterministic/
        agentic/
```

## Layers and responsibilities

Layers describe responsibilities and dependency boundaries. A layer can be a
single module; it does not need its own directory until that helps navigation.

| Responsibility | Location |
| --- | --- |
| Shared compliance types | `domain.py` |
| Contracts for external capabilities | `ports.py` |
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
cli -> config, runner, report, rules.registry, infrastructure.github.client
rules.registry -> individual rule modules
runner -> config, domain, ports, errors
report -> config, domain
rules -> domain, errors, shared GitHub response models where needed
domain -> ports
config -> errors
infrastructure.github.client -> infrastructure.github.models, errors
```

- `domain.py` and `ports.py` must not import concrete integrations, the runner,
  reporting, or individual rules.
- `ports.py` describes capabilities with Python protocols. `GitHubApi` is the
  contract used by the runner and `RuleContext`.
- The runner receives a `GitHubApi`; it does not create a `GitHubClient` or import
  individual rules. Rules are supplied explicitly by the caller.
- The CLI creates the concrete GitHub client and passes it to the runner.
  `GitHubClient` satisfies the protocol by providing its methods; it does not
  need to inherit from or import `GitHubApi`.
- Infrastructure must not import individual rules, the registry, the runner,
  or reporting. It owns communication details, not compliance decisions.
- Reporting consumes completed results and does not run checks.

At runtime, the runner calls a rule's check function. The rule can call the
GitHub client through `context.github`, then return a `RuleEvaluation`. The
runner converts that evaluation to a `RuleResult` for reporting. Calling an
implementation through a supplied protocol does not require importing it.

This is a pragmatic layered design with self-contained rules. Rules deliberately
own their endpoint selection and response validation; some import `GitHubModel`
from `infrastructure/github/models.py`. Configuration loading and its validated
models also stay together, and the runner and report use those models directly.
These are intentional boundaries, rather than a strict separation of every
business decision from every external data shape.

## Files

### `__init__.py`

Defines the small public package API.

**Should include:**

- Types deliberately exported to package users.

**Should not include:**

- Application startup or implementation details.

### `__main__.py`

Supports `python -m repo_compliance`.

**Should include:**

- Delegation to the command-line entry point.

**Should not include:**

- Checking, configuration, or reporting logic.

### `cli.py`

Connects command-line input to the application.

**Should include:**

- Argument parsing, environment input, and top-level error handling.
- Calls that connect configuration, GitHub, the runner, and reporting.

**Should not include:**

- Rule logic or GitHub response parsing.

### `config.py`

Loads and validates repository configuration.

**Should include:**

- Configuration models and configuration-specific validation.

**Should not include:**

- Runtime rule evaluation or GitHub requests.

### `domain.py`

Defines types shared across the application.

**Should include:**

- Rule definitions, results, contexts, evidence, enums, and the rule callable type.

**Should not include:**

- Rule-specific methods, API response models, or infrastructure implementations.

### `ports.py`

Defines contracts for external capabilities needed by the checker. A port says
what callers need; an infrastructure implementation supplies that behaviour.

**Should include:**

- Shared protocols such as `GitHubApi`, using ordinary Python types.

**Should not include:**

- HTTP requests, credentials, SDK clients, or concrete integration imports.

### `errors.py`

Defines expected application errors.

**Should include:**

- Small exception types used across module boundaries.

**Should not include:**

- Error-handling workflows or logging.

### Infrastructure package `__init__.py` files

Mark `infrastructure` and `infrastructure/github` as packages. Keep these files
limited to package documentation; import implementations from their modules.

### `infrastructure/github/client.py`

Provides shared GitHub transport and reusable GitHub operations.

**Should include:**

- Authentication, HTTP requests, status handling, and JSON decoding.
- Source snapshot downloads and policy-neutral operations used by multiple rules.

**Should not include:**

- Endpoints, filters, response models, or decisions belonging to one rule.

### `infrastructure/github/models.py`

Defines GitHub response models shared by multiple consumers.

**Should include:**

- Common response model behaviour and genuinely shared response shapes.

**Should not include:**

- A response model used by only one rule. Keep it in that rule's module.

### `runner.py`

Coordinates checks for each configured repository.

**Should include:**

- Preflight, exemptions, source snapshot lifecycle, rule execution, and result conversion.

**Should not include:**

- Individual rule decisions or report formatting.

### `report.py`

Renders completed results as Markdown.

**Should include:**

- Stable presentation, escaping, summaries, and detail sections.

**Should not include:**

- GitHub requests or rule evaluation.

### `rules/__init__.py`

Marks `rules` as a package.

**Should include:**

- Package-level documentation when useful.

**Should not include:**

- Rule registration or rule logic.

### `rules/registry.py`

Lists the rules that the application runs and their order.

**Should include:**

- Explicit rule imports and the set of known rule IDs.

**Should not include:**

- Rule implementations or automatic discovery machinery.

### Rule category `__init__.py` files

`rules/deterministic/__init__.py` and `rules/agentic/__init__.py` mark packages
that group rules by how they are evaluated.

**Should include:**

- Package-level documentation when useful.

**Should not include:**

- Rule implementations or registration.

### Rule modules

Files within `rules/deterministic/` and `rules/agentic/` implement individual
compliance rules.

**Should include:**

- The rule definition, evaluation, and result messages.
- Endpoints, query parameters, response models, and validation unique to the rule.
- Source snapshot inspection or evidence handling unique to the rule.

**Should not include:**

- Generic authentication, HTTP, source-snapshot-download, runner, or reporting behaviour.
- Behaviour belonging to another rule.

## Rule ownership

A rule should be a self-contained vertical slice. If a GitHub endpoint, query
parameter, response model, or validation rule exists for only one compliance
rule, keep it in that rule's module. Put behaviour in a shared module only when
it is policy-neutral and genuinely shared.

Adding a rule normally requires its source file, its test file, and one registry
entry. Removing a rule should require deleting those same items, plus any
configuration or documentation that explicitly refers to its rule ID.
