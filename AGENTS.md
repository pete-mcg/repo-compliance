# Context
A developer working within a live-service team manages over 20 tools/applications.
The source code for each application is stored across various GitHub repositories.
As a team, they are beginning to define a set of common rules and standards that repositories must adhere to.
For example, a repository "must possess a `.github/CODEOWNERS` file in the `main` branch".

# This Project
This repository runs a small Python checker against a visible list of GitHub repositories and writes one Markdown report. GitHub Actions schedules it; the same command works locally.

# Contributing
The following are paramount and supesede any other instructions:
- Always begin by loading the following skills: $caveman full; $ponytail full; $readable-python
- Always simple, obvious and readable code over clever tricks; no over-engineering or over-productionising. This is as a small, **beginner** friendly codebase.
- Function Design:
	- Do one thing per function;
	- Keep to one level of abstraction within a function;
	- Keep functions simple;
- Adhere to the skill $readable-python
- The quality gate is `task ci` passing.