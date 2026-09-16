# Package guide

This package checks configured GitHub repositories and produces one Markdown
report. Shared modules provide application plumbing; each compliance rule owns
the behaviour and GitHub data that are unique to that rule.

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

- Rule definitions, results, contexts, enums, and shared protocols.

**Should not include:**

- Rule-specific methods, API response models, or infrastructure implementations.

### `errors.py`

Defines expected application errors.

**Should include:**

- Small exception types used across module boundaries.

**Should not include:**

- Error-handling workflows or logging.

### `github.py`

Provides shared GitHub transport and reusable GitHub operations.

**Should include:**

- Authentication, HTTP requests, status handling, and JSON decoding.
- Archive downloads and policy-neutral operations used by multiple rules.

**Should not include:**

- Endpoints, filters, response models, or decisions belonging to one rule.

### `github_models.py`

Defines GitHub response models shared by multiple consumers.

**Should include:**

- Common response model behaviour and genuinely shared response shapes.

**Should not include:**

- A response model used by only one rule. Keep it in that rule's module.

### `runner.py`

Coordinates checks for each configured repository.

**Should include:**

- Preflight, exemptions, archive lifecycle, rule execution, and result conversion.

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
- Archive inspection or evidence handling unique to the rule.

**Should not include:**

- Generic authentication, HTTP, archive-download, runner, or reporting behaviour.
- Behaviour belonging to another rule.

## Rule ownership

A rule should be a self-contained vertical slice. If a GitHub endpoint, query
parameter, response model, or validation rule exists for only one compliance
rule, keep it in that rule's module. Put behaviour in a shared module only when
it is policy-neutral and genuinely shared.

Adding a rule normally requires its source file, its test file, and one registry
entry. Removing a rule should require deleting those same items, plus any
configuration or documentation that explicitly refers to its rule ID.
