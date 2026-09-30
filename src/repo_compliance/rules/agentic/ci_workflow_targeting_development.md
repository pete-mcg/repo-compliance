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

