# Rule

A repository must declare a GitHub Actions workflow that performs meaningful continuous integration for every pull request or push targeting the `development` branch.

"Meaningful continuous integration" = the workflow must perform all applicable steps:
- builds compiled source code when the project uses a compiled language
- transpiles or packages source code when the project requires it
- runs automated tests, except end-to-end tests that cannot run entirely within a GitHub Actions runner
- performs at least one applicable code-quality check:
  - formats
  - lints
  - type checks
  - undertakes static analysis

## Pass

A workflow runs for every pull request and push targeting `development`, with all applicable CI steps.

Examples:
- A compiled project builds, tests, and runs a formatter, linter, type checker, or static analysis.
- A project without compiled code performs applicable packaging, tests, and quality checks.

## Fail

No qualifying workflow covers either event, or an applicable CI step is missing.

Examples:
- CI targets only `main`, or covers pull requests but not pushes to `development`.
- A compiled project has no build, or tests and quality checks are missing.

Do not require end-to-end tests that cannot run entirely in GitHub Actions.

## Uncertain

Event coverage or meaningful CI steps cannot be determined from inspected files.

Examples:
- A required reusable workflow is unavailable.
- Project language or test requirements are unclear.

## Evidence

- Pass: cite workflow triggers and jobs or steps showing coverage and applicable checks.
- Fail: cite the missing coverage or applicable CI step.
- Uncertain: cite the unresolved dependency or inspection gap.
