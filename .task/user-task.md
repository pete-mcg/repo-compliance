## Context
I am a developer working within a live-service team, where we manage over 20 tools/applications.

The source code for each application is stored across various GitHub repositories.

As a team, we are beginning to define a set of common rules and standards that repositories must adhere to. For example, a repository "must possess a `.github/CODEOWNERS` file in the `main` branch".

## Goal 
Build a lightweight solution to monitor each repository's violations/conformance to these standards. This way, we can easily identify which repositories require action.

The checker will evaluate each configured repository against a growing set of engineering and security standards and produce a clear Markdown report.

The compliance checker will be implemented as a small, typed Python application and executed periodically or on manual trigger by GitHub Actions. Python owns the rules, configuration and report generation, while GitHub Actions owns scheduling, credentials and publishing the result. Developers must be able to run the same checker locally. This keeps GitHub Actions as infrastructure rather than making workflow YAML part of the compliance engine.

## Constraints
As a developer who will be regularly maintaining this specific repository, this repository must make its two primary maintenance activities immediately obvious:
1. There must be an easily configurable list of GitHub repositories. This will be something that I, or other members of the team, can easily locate, add to or delete from as our tool/applications list changes.
2. There must be a clear area within the repository where the logic of the different rules are managed. It should be simple, easy and obvious where to add or remove future rules. It should not be haphazard. Prefer having a separate file, per rule.

Updating these GitHub repositories and rulesets, are the core areas where I as a developer will interact with. The repository you build must therefore make it very intuitive on how to do these.

Further considerations:

- The architecture should leave room for repository-specific exemptions. This is because some rules may not be applicable to a repository, or the repository may be granted an exception.
- Different rules may present different levels of confidence, depending on the evaluation method. Some rules will be deterministic, where the answer will be unambiguous with no risk of misclassification. Some rules may require static analysis; i.e. source inspection based on, for example, search patterns; useful, but potentially fallible and has some risk of misclassification. Some rules may require broader reasoning across the repository, where an AI model makes a judgment. The rules should be separated into appropriate subfolders based on evaluation method.
- Start with a PAT but deliberately design the Python code so it doesn't care where the token came from. (Long-term, I'd likely favour a GitHub App installed on the monitored repositories.)

## Code Design
- Prefer simple, obvious and readable code over clever tricks; no over-engineering or over-productionising. Think of it as beginner friendly.
- Function Design:
	- Do one thing per function;
	- Keep to one level of abstraction within a function;
	- Keep functions simple;

## Example Rules
Here are some rules to get us started:

Deterministic:
- The `main` branch must be protected against deletion.
- Must possess a `.github/CODEOWNERS` file in the `main` branch.
- Must possess a `.github/workflows/deploy.yml` in the `main` branch.
- Dependabot must report zero Critical vulnerabilities.

Static Analysis:
- Key-based authentication is prohibited.

Agentic:
- None.

## This repository
This is an almost empty repository for you to work in. As a head start, I have included:
- `pyproject.toml`, that includes my desired lint, test and typecheck settings.
- `uv.lock`
- `tests/.gitkeep`, to store tests.
- `src/repo_compliance/__init__.py`
- `.task/` containing this task file.