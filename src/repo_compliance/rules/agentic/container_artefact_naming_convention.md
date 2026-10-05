# Rule

Any container build that publish images must satisfy **every** applicable requirement below:

- Every build updates `[Branchname]-latest`.
- Every build creates a unique `[Branchname]-[YYYYMMDD.XX]` tag, for example `development-20260930.42`. `YYYYMMDD` is the build date; `XX` is the GitHub Actions run number (`github.run_number` or `GITHUB_RUN_NUMBER`), not a commit hash, run ID, or run attempt. `XX` is a placeholder, not a two-digit limit. Square brackets are placeholders, not literal characters.
- Builds from `main` additionally update the project's unqualified `latest` image tag.
- Builds triggered by Git tag creation or amendment create or update an image tag with exactly the same name. For example, Git tag `1.3.7-beta-1` publishes `ghcr.io/testorg/testproject:1.3.7-beta-1`. Both creation and updates to an existing Git tag must reach this build path.

Inspect every build path in GitHub workflows, local actions, reusable workflows, and scripts; trace generated tags through to the image publication step.
