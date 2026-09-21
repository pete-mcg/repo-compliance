# Check: CI runs on pull requests to main

Decide whether the repository declares a GitHub Actions workflow that performs meaningful continuous integration for every pull request targeting `main`.

## Judgment

1. List the repository root, then `.github` and `.github/workflows` if present. Read the YAML workflow files. A successful parent listing that omits a directory establishes its absence; no workflow directory means `fail`. A tool error is not proof that a file is absent.
2. Look for a `pull_request` or `pull_request_target` trigger that includes `main`. An unrestricted pull-request trigger, including `on: pull_request` and event lists, includes `main`. Consider branch patterns, negations, `branches-ignore`, and `types`. Require coverage of the normal opened, synchronize, and reopened events. Push-only and manual-only workflows do not qualify.
3. Require meaningful CI: a build, tests, lint, type checks, or static analysis. A name such as "CI", checkout, echo, notification, or deployment alone is not enough. Follow relevant local scripts, task definitions, composite actions, and local reusable workflows to understand what the jobs do. Standard recognizable CI actions can supply meaningful evidence; an opaque remote reusable workflow or missing local implementation is insufficient evidence.
4. Require at least one qualifying workflow whose CI applies to every normal pull request to `main`. Path filters, draft exclusions, label or author gates, job/step conditions, or event filters that exclude some such pull requests disqualify that workflow. An unconditional meaningful CI job in the same workflow can still qualify. Do not speculate about runtime failures or user mechanisms such as commit-message skip directives.
5. Return `pass` if a qualifying workflow exists. Return `fail` if the inspected declarations establish that no workflow qualifies (including no workflows, wrong branch, push-only, restricted triggers, or no meaningful CI). Return `uncertain` if missing, unreadable, invalid, or opaque evidence prevents a judgment. Do not guess that an unfamiliar command performs CI.

## Evidence

Cite both the trigger and meaningful CI for a pass, using markers such as `pull-request-trigger` or `test-command`. An absent workflow directory can have an empty evidence list.
