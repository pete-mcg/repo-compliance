# Rule

Container builds must publish images using the project image name and the following tag convention. Inspect every build path in workflows, local actions, reusable workflows, and scripts; trace generated tags through to the image publication step.

## Pass

All container build paths satisfy every applicable requirement:

- Every build updates `[Branchname]-latest`.
- Every build creates a unique `[Branchname]-[YYYYMMDD.XX]` tag, for example `development-20260930.42`. `YYYYMMDD` is the build date; `XX` is the GitHub Actions run number (`github.run_number` or `GITHUB_RUN_NUMBER`), not a commit hash, run ID, or run attempt. `XX` is a placeholder, not a two-digit limit. Square brackets are placeholders, not literal characters.
- Builds from `main` additionally update the project's unqualified `latest` image tag.
- Builds triggered by Git tag creation or amendment create or update an image tag with exactly the same name. For example, Git tag `1.3.7-beta-1` publishes `ghcr.io/testorg/testproject:1.3.7-beta-1`. Both creation and updates to an existing Git tag must reach this build path.

Use the actual source branch for branch tags, allowing necessary image-tag-safe sanitisation. A Git tag name is not a branch name; do not assume a tag build comes from `main`. No container build paths also passes after inspection.

## Fail

Any confirmed container build path omits or misnames a required tag, uses the wrong date or run-number source, or generates tags without publishing them. Tag creation is supported but amendment is excluded, or the Git tag is altered (for example, a prefix is stripped). Cite the violated requirement even if other paths are unresolved.

## Uncertain

No violation is confirmed, but compliance cannot be established for all paths: referenced workflows or actions are unavailable, tag generation or publication is unresolved, or the source branch for a tag build cannot be determined.

## Evidence

- Pass: cite build triggers, branch resolution, date and run-number construction, conditional tags, and publication steps; for no builds, cite inspected workflow and build entry points.
- Fail: cite the build path and missing or incorrect tag, publication, or Git tag trigger handling.
- Uncertain: cite the unresolved reference, branch identity, or inspection gap.
