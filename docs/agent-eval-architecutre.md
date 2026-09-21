# How agent evaluation works

This document explains, in plain English, how an agent rule inspects a
repository. The two main files are:

- `agent_framework.py` starts the AI agent, gives it safe access to source
  files, and turns its answer into a normal compliance result.
- `source_snapshot.py` safely unpacks the repository ZIP into a temporary
  folder for inspection.

The agent does not receive the whole repository in its prompt. It can use a
small set of read-only tools to look through a temporary copy and find evidence
for its answer.

## The journey of one agent rule

The current agent rule asks whether CI runs for every pull request to `main`.

```text
runner.py downloads the main-branch ZIP
        |
        v
the rule loads its Markdown instructions and calls evaluate(...)
        |
        v
agent_framework.py checks settings and safely extracts the ZIP
        |
        v
the AI agent uses Serena's read-only local file tools
        |
        v
the AI returns pass, fail, or uncertain, with evidence locations
        |
        v
the answer becomes RuleEvaluation, then PASS, FAIL, or ERROR in the report
```

Before this route starts, `runner.py` skips exempt rules and checks that the
repository is accessible. It downloads one ZIP only when an active rule needs
source files. That ZIP can be shared by the source-based rules.

The agent rule's `load_prompt()` reads the packaged Markdown instructions.
Its `check(context)` confirms it has a ZIP and evaluator, then calls
`context.agent_evaluator.evaluate(source_zip, prompt)`. `RuleEvaluation` is
the normal project result: `passed` is true or false, with a short message and
zero or more evidence locations.

## `agent_framework.py`

This file is an adapter. It hides Azure OpenAI, Microsoft Agent Framework,
Docker, and Serena behind the small `AgentEvaluator` interface used by rules.

### Data shapes and validation

These classes describe data; they do not start services or inspect files.

- `AzureOpenAISettings` reads the required `AZURE_OPENAI_ENDPOINT`,
  `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_VERSION` environment
  variables. It checks that their formats look safe.
- `AgentVerdict` permits only `pass`, `fail`, and `uncertain`.
- `AgentEvidence` describes one supporting file location.
- `AgentStructuredResponse` describes the complete answer: verdict,
  explanation, and evidence.

| Function | What it does simply |
| --- | --- |
| `AgentEvidence.validate_path(value)` | Uses `safe_relative_path` so evidence can point only inside the repository. |
| `AgentEvidence.validate_line(value)` | Rejects a line number below 1. |
| `AgentEvidence.validate_marker(value)` | Requires a non-empty evidence label of at most 80 characters. |
| `AgentStructuredResponse.validate_explanation(value)` | Requires a non-empty explanation of at most 600 characters. |

### Main evaluation path

| Order | Function | What it does simply |
| --- | --- | --- |
| 1 | `AgentFrameworkEvaluator.evaluate(snapshot_path, prompt)` | The starting point. It validates Azure settings, calls `_evaluate_snapshot`, and changes expected setup, Azure, Docker, MCP, validation, and timeout problems into a safe `AgentError` message. |
| 2 | `_evaluate_snapshot(snapshot_path, prompt, settings)` | Opens a temporary extracted ZIP and a separate temporary Serena-state folder. It writes Serena configuration, gives the container a unique name, runs the async agent work, always attempts container cleanup, and converts the answer to `RuleEvaluation`. |
| 3 | `extracted_source_snapshot(snapshot_path)` | From `source_snapshot.py`: validates and extracts the ZIP, then supplies the temporary repository folder. |
| 4 | `write_serena_configuration(state)` | Writes fresh Serena settings, so any `.serena` settings inside the repository cannot be used. |
| 5 | `_run_agent(repository, state, container_name, settings, prompt)` | Starts Azure and Serena resources, builds the agent, sends it the rule prompt, and returns its raw answer. |
| 6 | `_to_evaluation(output)` | Validates the raw answer and changes it into the project's normal result shape. |

### `_run_agent` step by step

1. An overall 120-second time limit starts.
2. `AzureCliCredential()` obtains Azure identity from the Azure CLI sign-in.
3. `create_azure_client(settings, credential)` creates the Azure OpenAI client.
4. `create_serena_tool(repository, state, container_name)` creates the local
   repository-file tool.
5. Agent Framework creates an `Agent` named `repository-compliance` with that
   one tool.
6. The agent receives the rule prompt and must return an
   `AgentStructuredResponse`, not free-form prose.
7. The raw response value is returned. The credential, Azure client, and Serena
   tool are closed automatically, even after a failure.

The agent is also told to make no more than one tool call at a time, and not to
store the interaction.

### Azure helper

`create_azure_client(settings, credential)` creates the `AsyncAzureOpenAI`
client. It uses the checked endpoint, deployment, and API version from
`AzureOpenAISettings`. It obtains an Entra ID bearer token from the Azure CLI
credential. Redirects, proxy environment settings, retries, and overlong
requests are disabled or limited.

### Serena and Docker helpers

Serena is the local service that gives the agent file tools. It runs in Docker
and talks to the agent over standard input/output (MCP), not the network.

| Function | What it does simply |
| --- | --- |
| `create_serena_tool(repository, state, container_name)` | Creates the `repository-files` tool. It launches Docker using `serena_docker_arguments` and permits only listing folders, reading files, finding files, and searching text. |
| `serena_docker_arguments(repository, state, container_name)` | Returns the Docker command arguments in one reviewable place. |
| `write_serena_configuration(state)` | Writes Serena's three YAML settings files. It starts no language servers and fixes the allowed tool list. |
| `_remove_container(container_name)` | Force-removes the named container after evaluation. A missing Docker command or already-gone container is harmless; other cleanup failures become `AgentError`. |

The Docker configuration is deliberately limited:

- It uses one exact, pinned Serena image and never downloads a replacement.
- Its filesystem is read-only, and Linux capabilities are dropped.
- Networking is disabled.
- The extracted repository is mounted at `/repository` as read-only.
- Serena's separate temporary state is mounted at `/state`.
- `/tmp` is small temporary memory storage that cannot run programs.
- Azure credentials and GitHub tokens are not passed into the container.

### Converting the answer

`_to_evaluation(output)` performs the final checks:

1. It validates the answer using `AgentStructuredResponse`.
2. `uncertain` becomes `AgentError`, so the report shows `ERROR`: there was no
   dependable judgment.
3. `pass` must include evidence. `fail` may contain no evidence.
4. Each `AgentEvidence` is changed into the project's `Evidence` type.
5. It returns `RuleEvaluation`: pass means `passed=True`; fail means
   `passed=False`.

If an `AgentError` reaches `runner.py`, its `_run_rule_test` records `ERROR`
for that rule and continues with other rules.

## `source_snapshot.py`

This file handles the ZIP downloaded from GitHub. It prevents a malformed ZIP
from writing outside the temporary folder or using too much space.

It accepts at most 20,000 ZIP items and 512 MiB of uncompressed content. It
expects GitHub's normal ZIP layout: one top-level wrapper folder containing all
repository files. That wrapper folder is removed during extraction, so the
temporary folder directly contains paths like `.github/workflows/ci.yml`.

### Extraction path

| Order | Function | What it does simply |
| --- | --- | --- |
| 1 | `extracted_source_snapshot(snapshot_path)` | Creates a temporary folder, calls `_extract_source_snapshot`, and yields the extracted repository. It deletes the folder when its caller finishes or fails. |
| 2 | `_extract_source_snapshot(snapshot_path, destination)` | Opens the ZIP, validates all source items, then extracts them one at a time. ZIP, filesystem, decompression, and validation problems become `SourceSnapshotError`. |
| 3 | `_validate_source_items(source_items)` | Rejects an empty ZIP, too many items, too much uncompressed content, or items that do not share one wrapper folder. It checks every item with `_validated_source_item_path`. |
| 4 | `_extract_source_item(source_zip, source_item, destination)` | Re-checks one item, removes the wrapper folder from its path, makes needed folders, and copies the file. It uses exclusive creation, so it cannot silently overwrite a file. |

### Path and source-item checks

| Function | What it does simply |
| --- | --- |
| `safe_relative_path(value)` | Checks paths from both ZIP source items and agent evidence. It rejects empty parts, `.` and `..`, backslashes, colons, and Windows-reserved names such as `NUL`. It returns a safe relative POSIX path. |
| `_validated_source_item_path(source_item)` | Applies `safe_relative_path` to one ZIP source item. It rejects links, special files, encrypted items, and files outside the wrapper folder. |

Validation happens twice on purpose: `_validate_source_items` checks every item
before any write starts, and `_extract_entry` checks again immediately before
writing. The writing function therefore confirms that its own target is safe.

## Short example

The CI rule might inspect `.github/workflows/ci.yml` and return:

```text
verdict: pass
explanation: CI runs when a pull request targets main.
evidence:
  - path: .github/workflows/ci.yml
    line: 3
    marker: pull-request-trigger
```

The validators accept only a safe, correctly shaped answer. `_to_evaluation`
turns this into `RuleEvaluation(True, ...)`, and the runner reports `PASS`.
