# Adding and removing rules

## Self-Contained

- Each rule owns one, AND ONLY ONE, standard.
- A rule must be a self-contained slice: its constants, GitHub endpoint paths, response models, checks, and helpers belong together.
- Put behaviour in a shared module (e.g. `helpers.py`) only when it is policy-neutral and genuinely shared.
- An agentic rule owns an adjacent Markdown prompt.
- Rules must not import other rule modules.

## Keep the same structure

Every rule follows this order:

1. Imports, `RULE_ID`, and other constants or response models.
2. `check(context: RuleContext) -> RuleEvaluation`.
3. Private helper functions, if needed.
4. `RULE = RuleDefinition(...)`.

## Agentic Rules

Agent rules require a prompt markdown file. Keep the prompt beside the Python file in `rules/agentic/`. Follow the provided template:

```md
# Rule

[insert clear desription]

## Pass

[insert clear criteria]

## Fail

[insert clear criteria]

## Uncertain

[insert clear criteria]

## Evidence

[insert what to cite]
```

Shared instructions and response formatting already live in the [system prompt](../src/repo_compliance/infrastructure/agentic/system_prompt.md).

All prompts should be as concise as possible to reduce token consumption.

## Enable and test

1. Import the new `RULE` into [registry.py](../src/repo_compliance/rules/registry.py), using a clear alias.
2. Add that alias to `RULES`. Its position sets the check and report order.
3. Add a matching test under `tests/unit/rules/<category>/test_<name>.py`. For agentic rules, check prompt loading with `FakeAgentEvaluator`. The shared agent integration test covers the infrastructure; a separate live test is not required for each rule.
4. Run `task ci`. See [Contributing](development.md) for integration tests.

## Disable or remove

To disable a rule everywhere:

- Remove its import and entry from `RULES`.
- Remove exemptions using its ID from [repositories.yml](../config/repositories.yml); unknown IDs are rejected.

To remove a rule completely: apply steps above, plus delete its source, prompt, tests, unused fixtures, and documentation references.

To skip a rule for just one repository: add an exemption in [repositories.yml](../config/repositories.yml).
