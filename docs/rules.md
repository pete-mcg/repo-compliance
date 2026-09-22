# Adding and removing rules

Each rule owns one standard. Keep it self-contained: its constants, GitHub endpoint paths, response models, checks, and helpers belong together. An AI rule also owns its adjacent Markdown prompt. Rules must not import other rule modules.

## Choose an example

Copy the closest existing rule and its test:

| Type | Use it for | Example |
| --- | --- | --- |
| Deterministic | A fixed check of GitHub data or source files. | [codeowners_present.py](../src/repo_compliance/rules/deterministic/codeowners_present.py) |
| Deterministic, using source | Searching the downloaded source ZIP. | [no_key_based_authentication.py](../src/repo_compliance/rules/deterministic/no_key_based_authentication.py) |
| Agentic | An AI judgment using source files and written criteria. | [ci_workflow_on_pull_requests.py](../src/repo_compliance/rules/agentic/ci_workflow_on_pull_requests.py) |

Put the new file in the same category folder. Use underscores in filenames and a unique ID with hyphens: `example_rule.py` and `example-rule`.

## Keep the same structure

Every rule follows this order:

1. Imports, `RULE_ID`, and other constants or response models.
2. `check(context: RuleContext) -> RuleEvaluation`.
3. Private helper functions, if needed.
4. `RULE = RuleDefinition(...)`.

`RuleDefinition` contains the ID, title, description, category, confidence, documentation URL, and `check=check`. Use a documentation URL that explains the team's standard. Confidence describes how reliable the check is expected to be.

The runner supplies `context.repository`, `context.github`, and, when needed, `context.source_snapshot_path` and `context.agent_evaluator`.

- Return `RuleEvaluation(True, "Reason")` for a pass or `RuleEvaluation(False, "Reason")` for a failure.
- Include file paths and line numbers as `Evidence` when useful. Keep secrets out of messages and evidence.
- Set `requires_source_snapshot=True` when reading source. Use the supplied ZIP; the runner downloads it once per repository.
- Use `context.github` for GitHub requests. Keep rule-specific response validation in the rule.
- Let `GitHubError`, `SourceSnapshotError`, and `AgentError` reach the runner. It records `ERROR` and continues. Do not hide unexpected bugs.

Exemptions and report formatting belong to the runner and report code, not individual rules.

## AI prompts

Use `rule_prompt_filename(RULE_ID)` from [helpers.py](../src/repo_compliance/rules/agentic/helpers.py). It replaces hyphens with underscores:

```text
Rule ID:     ci-workflow-on-pull-requests
Python file: ci_workflow_on_pull_requests.py
Prompt file: ci_workflow_on_pull_requests.md
```

Keep the prompt beside the Python file in `rules/agentic/`. The `check` function calls `evaluate_agentic_rule(context, PROMPT_FILENAME)`. Set `category=RuleCategory.AGENTIC` and `requires_source_snapshot=True`.

Write clear pass, fail, and uncertain criteria, plus the evidence to cite. Uncertainty becomes `ERROR`. Shared instructions and response formatting already live in the [system prompt](../src/repo_compliance/infrastructure/agentic/system_prompt.md).

## Enable and test

1. Import the new `RULE` into [registry.py](../src/repo_compliance/rules/registry.py), using a clear alias.
2. Add that alias to `RULES`. Its position sets the check and report order; `RULE_IDS` is derived automatically.
3. Add a matching test under `tests/unit/rules/<category>/test_<name>.py`. For AI rules, check prompt loading with `FakeAgentEvaluator` and add suitable live fixtures.
4. Run `task ci`. See [Contributing](development.md) for integration tests.

There is no automatic rule discovery.

## Disable or remove

To disable a rule everywhere, remove its import and entry from `RULES`. Also remove exemptions using its ID from [repositories.yml](../config/repositories.yml); unknown IDs are rejected.

To remove it completely, also delete its source, prompt, tests, unused fixtures, and documentation references. To skip it for just one repository, [add an exemption](getting-started.md#2-choose-repositories).
