# Repository Compliance Checker

## Summary

Build synchronous, typed Python CLI using existing `httpx`, Pydantic, PyYAML, and stdlib. No new dependencies, plugin framework, concurrency, retries, database, or AI integration. Keep rule logic in one-file-per-rule folders; explicit registry makes additions obvious.

## Interfaces and Configuration

- Add CLI entry point:
  `repo-compliance [--config config/repositories.yml] [--output compliance-report.md]`
- Read token only at CLI boundary from `GITHUB_TOKEN`; pass plain token into `GitHubClient`. Missing token, invalid config, output failure, or unexpected checker bug returns nonzero.
- Add `config/repositories.yml`:
  ```yaml
  repositories:
    - repository: owner/name
      exemptions:
        - rule: deploy-workflow-present
          reason: This service has no deployment.
  ```
- Require nonempty exemption reason. Reject duplicate repositories, duplicate exemptions, malformed repository names, and unknown rule IDs. Permit empty initial repository list.
- Public types:
  - `RuleCategory`: `deterministic`, `static_analysis`, `agentic`
  - `ResultStatus`: `pass`, `fail`, `exempt`, `error`
  - Pydantic models for YAML and GitHub API input
  - Frozen dataclasses for rule definitions, evidence, and results
- Violations and evaluation errors remain report data; completed run exits `0`.

## Implementation

- Create `rules/deterministic`, `rules/static_analysis`, and empty `rules/agentic` packages. Each rule file exports one typed check and immutable metadata; central explicit registry controls enabled rules.
- Preflight each non-fully-exempt repository’s `main` branch. Inaccessible repository or missing branch produces `ERROR` for active rules, avoiding false file violations.
- Implement deterministic rules:
  - `main-branch-deletion-protected`: pass when active repository/organization rulesets include deletion protection; otherwise inspect classic protection and require `allow_deletions.enabled == false`. GitHub exposes active branch rules and classic deletion settings through separate endpoints. [Rules API](https://docs.github.com/en/rest/repos/rules), [branch protection API](https://docs.github.com/en/rest/branches/branch-protection)
  - `codeowners-present`: exact `.github/CODEOWNERS` on `main`.
  - `deploy-workflow-present`: exact `.github/workflows/deploy.yml` on `main`.
  - `no-critical-dependabot-alerts`: query open Critical alerts; pass only when response is empty.
- Implement `no-key-based-authentication`:
  - Download `main` archive once when any non-exempt static rule exists; stream into temporary file and inspect ZIP entries without extraction.
  - Scan tracked UTF-8 text files, excluding dependency/build directories, binary files, and files over `1 MiB`.
  - Case-insensitively detect `api[-_]?key`, `x-api-key`, `access[-_]?key`, `secret[-_]?key`, `account[-_]?key`, `subscription[-_]?key`, and shared-access-key connection fields, including camelCase forms.
  - Record path, line, and marker name only—never matched line/value. Keep first 20 locations and report omitted count.
- Apply exemptions before API/archive work. Continue across expected HTTP, archive, and response-validation failures as `ERROR`; unexpected programming failures remain fatal.
- Generate Markdown containing UTC timestamp, totals, repository summary, full rule table, category/confidence signal, details, links, and capped evidence. Preserve config and registry order.
- Add weekday workflow at `06:00 UTC` plus `workflow_dispatch`; use `actions/checkout@v6`, `astral-sh/setup-uv@v9`, and `actions/upload-artifact@v7`. Run frozen environment, append report to `GITHUB_STEP_SUMMARY`, and upload `repository-compliance-report`.
- Add README covering repository edits, exemption syntax, rule creation/removal, local command, result meanings, PAT setup, and workflow. Ignore generated report and Python tooling artifacts.

## Test Plan

- Config: valid empty/populated files; malformed YAML; invalid or duplicate repositories; unknown/duplicate exemptions; blank reasons.
- GitHub client with `httpx.MockTransport`: authentication/version headers, redirects, timeouts, response validation, expected 404 handling, and API errors.
- Rules:
  - Ruleset and classic deletion protection combinations.
  - Present/missing exact files.
  - Empty/nonempty Critical alert response.
  - Every key marker, casing/separator variants, binary/vendor/oversized exclusions, evidence cap, and secret-content suppression.
- Runner: exemptions skip checks, preflight errors affect active rules only, one archive download per repository, expected errors do not stop later repositories.
- Report/CLI: stable ordering, Markdown escaping, counts, links, exit `0` for violations/errors, nonzero for fatal setup failures.
- Verify:
  - `uv run ruff check .`
  - `uv run pyrefly check`
  - `uv run pytest --cov --cov-report=term-missing`
  - `uv run deptry .`
  - Coverage remains at least `85%`.

## Assumptions and Defaults

- GitHub.com only; fixed branch `main`; exact case-sensitive required paths.
- Fine-grained PAT stored as `REPO_COMPLIANCE_TOKEN`, exposed to CLI as `GITHUB_TOKEN`. Grant Metadata read, Contents read, Administration read, and Dependabot alerts read, matching endpoint requirements. [Contents API](https://docs.github.com/en/rest/repos/contents), [Dependabot API](https://docs.github.com/en/rest/dependabot/alerts)
- Use current versioned GitHub REST headers and `30 s` HTTP timeout.
- No retries or parallelism until runtime or rate-limit evidence demands them.
- No expiry/approver exemption metadata, persistent history, agentic rules, numeric confidence score, or configurable regex engine.
- Ponytail keeps design synchronous and explicit; readable-python drives small functions, narrow exception handling, enums, dataclasses, and Pydantic IO validation. Caveman affects chat only; repository prose remains normal English.
