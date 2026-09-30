# Rule

Source code must use `main` instead of `master` and `development` instead of `dev` when referring to Git branches. 

## Pass

No active branch references use `master` or `dev`. A repository with no branch references also passes after inspection.

Ignore unrelated uses of these words, such as a `dev` environment, dependency group, or variable name, and historical comments or examples describing migration away from old branch names. Other branch names, such as `feature/dev-tools`, are allowed.

## Fail

At least one active reference uses the exact branch name `master` or `dev`, including qualified forms such as `refs/heads/dev` or `origin/master`. Examples include workflow push or pull-request filters, checkout refs, Git commands, branch comparisons, and branch-specific URLs. Recommend `main` for `master` and `development` for `dev`.

For example, `on: {push: {branches: [dev]}}` fails; `on: {push: {branches: [development]}}` complies.

## Uncertain

Branch references are constructed dynamically or inspection is incomplete, so compliance cannot be established. A confirmed violation still fails.

## Evidence

Cite files and lines containing non-compliant branch references. For a pass, cite compliant references or inspected files supporting the absence of old branch names. For uncertainty, cite the unresolved reference or explain the inspection gap.
