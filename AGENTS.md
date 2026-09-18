# Context
A developer working within a live-service team that manages tens of tools and applications.
The source code for each application is stored across various GitHub repositories.
As a team, they are beginning to define a set of common rules and standards that repositories must adhere to.
For example, a rule that "a repository must possess a `.github/CODEOWNERS` file in the `main` branch".

# This Project
This repository runs a small Python checker against a visible list of GitHub repositories and writes one Markdown report. GitHub Actions schedules it; the same command works locally.

# Contributing
- Always simple, obvious and readable code over clever tricks; over-engineering and over-productionising are **forbidden**. This is as a lightweight, **beginner** friendly codebase. If new code fails to be simple and beginner friendly, it will not be merged.
- Function Design:
	- Do one thing per function;
	- Keep to one level of abstraction within a function;
	- Keep functions simple;
- The quality gate is `task ci`.