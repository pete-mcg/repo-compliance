# Rule

Every GitHub Actions path that generates an artefact must only be initiated by a manual `workflow_dispatch` trigger.

## Pass

Every artefact-generating workflow runs only through `workflow_dispatch`.

Examples:
- A workflow has only `workflow_dispatch` as its trigger.
- A called workflow is reachable only from a manually triggered workflow.

## Fail

Any artefact-generating path can start automatically or through another trigger.

Examples:
- The workflow also has `push`, `pull_request`, `schedule`, or `workflow_call`.
- A scheduled or push-triggered workflow calls the artefact-generating workflow.

## Uncertain

Workflow triggers or call paths cannot be established.

Examples:
- A referenced workflow file is unavailable.
- Dynamic workflow generation obscures the trigger path.

## Evidence

- Pass: cite the trigger and artefact-generating job or step.
- Fail: cite the non-manual trigger and artefact-generating path.
- Uncertain: cite the unresolved reference or inspection gap.
