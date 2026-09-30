# Rule

Project documentation must minimally contain:
- A project overview
- Setup instructions to run the project, tool, or application

Inspect README files, documentation directories, and linked files within the repository. The content may span multiple files; no particular filename or heading is required.

## Pass

Both are documented:
- An overview explaining what the project does or what it is for.
- Actionable setup and run instructions, including prerequisites, installation, and configuration where needed, plus commands or steps to start or invoke the project.

Keep the standard minimal. Brief instructions suffice when the project needs little setup. Do not require architecture, deployment, contribution, or troubleshooting guides.

Examples:
- A README explains the application's purpose and gives installation and start commands.
- An overview links to a repository setup guide covering required configuration and how to invoke the tool.

## Fail

Inspection establishes that either required element is missing. A project name, empty headings, placeholders, or dependency files alone do not satisfy the rule. Installation or build steps without instructions to run the project are insufficient.

Examples:
- A README describes the project but gives no setup or run instructions.
- Documentation gives installation and start commands but no project overview.
- Setup instructions end at building the project without explaining how to run it.

## Uncertain

Relevant documentation cannot be inspected, exists only at an external link, or is too ambiguous to establish whether both elements are present.

Examples:
- A README links to an external setup guide whose contents are unavailable.
- Run instructions refer to a missing guide or leave the invocation ambiguous.

## Evidence

- Pass: cite the overview and setup/run instructions with file paths and lines.
- Fail: identify the missing element and cite relevant inspected documentation where available; describe the search if no documentation exists.
- Uncertain: cite the ambiguous content or external reference, or describe the inspection gap.
