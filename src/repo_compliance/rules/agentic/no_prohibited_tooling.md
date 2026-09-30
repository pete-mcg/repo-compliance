# Rule

Source code and documentation must not use or refer to:
- Docker Desktop*
- Anaconda
- Miniconda
- Postman

* Docker via Rancher Desktop and `docker-ce` in WSL are approved.

## Pass

Inspection finds no use or reference to prohibited tooling. Rancher Desktop and `docker-ce` in WSL are approved; generic Docker files or commands do not imply Docker Desktop.

Examples:
- Docker instructions use Rancher Desktop or `docker-ce` in WSL.
- `postman` refers to a postal worker, not the tool.

Match case and variants such as `DockerDesktop` or `miniconda3`; ignore unrelated meanings.

## Fail

At least one source or documentation reference identifies prohibited tooling. Historical, migration, and negative references also fail.

Examples:
- Install steps, dependencies, executable paths, download links, or Docker Desktop settings.
- Postman collections or environments.
- “Do not use Docker Desktop; use Rancher Desktop.”

Generic Docker or Conda references alone do not establish a violation; use context.

## Uncertain

Tooling references cannot be resolved or inspection is incomplete. A confirmed violation still fails.

Examples:
- An ambiguous Conda setup does not identify the distribution.
- Relevant source or documentation could not be inspected.

## Evidence

- Pass: cite inspected files showing approved alternatives or no prohibited reference.
- Fail: cite the line naming the prohibited tool and its context.
- Uncertain: cite ambiguous references or describe the inspection gap.
