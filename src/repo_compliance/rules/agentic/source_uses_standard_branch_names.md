# Rule

Source code must use `main` instead of `master` and `development` instead of `dev` when referring to Git branches. 

## Pass

No active branch reference uses `master` or `dev`; no branch references also passes after inspection.

Examples:
- References use `main` and `development`.
- `dev` names an environment or appears in `feature/dev-tools`.

Ignore unrelated words and historical migration examples.

## Fail

An active reference uses the exact branch name `master` or `dev`, including qualified forms. Recommend `main` or `development`, respectively.

Examples:
- Workflow filters or checkout refs target `dev` or `origin/master`.
- Git commands, comparisons, or branch-specific URLs use either name.

## Uncertain

Branch references are dynamic or inspection is incomplete, so compliance cannot be established. A confirmed violation still fails.

Examples:
- A branch name is assembled from variables.
- A referenced workflow or script is unavailable.

## Evidence

- Pass: cite compliant references or inspected files supporting absence of old names.
- Fail: cite the active `master` or `dev` reference.
- Uncertain: cite the unresolved reference or inspection gap.
