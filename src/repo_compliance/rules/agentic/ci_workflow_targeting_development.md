# Rule

A repository must declare a GitHub Actions workflow that performs meaningful continuous integration for every pull request or push targeting the `development` branch.

"Meaningful continuous integration" = the GitHub Actions workflow must perform all applicable steps:
- builds compiled source code when the project uses a compiled language
- transpiles or packages source code when the project requires it
- runs automated tests (inclusion of end-to-end tests is not strictly necessary)
- performs at least one of the following code-quality checks:
  - formats
  - lints
  - type checks

These steps must be performed by the GitHub Actions workflow to be considered a pass. For example, the presence of `tests/` and pytest may indicate that automated tests are available, but if they are not ran as part of the GitHub Action Workflow then it does not count in favour of this rule being satisfied.