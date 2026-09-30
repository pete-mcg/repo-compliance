# Rule

Source code and documentation must not use or refer to Docker Desktop, Anaconda, Miniconda, or Postman. Inspect repository source, comments, scripts, configuration, workflows, and documentation, including tool-specific files and links.

## Pass

No use of or reference to prohibited tooling is found after inspection. Docker via Rancher Desktop and `docker-ce` in WSL are approved. Generic Docker commands, Dockerfiles, Compose files, and container images do not by themselves imply Docker Desktop use.

Ignore unrelated meanings, such as anaconda the animal or postman a postal worker. Match tooling references regardless of case or spelling variants such as `DockerDesktop` and `miniconda3`.

## Fail

At least one use of or reference to prohibited tooling is found. This includes installation instructions, dependencies, executable paths, download links, Docker Desktop-specific settings, and Postman collections or environments. Historical, migration, and negative references also fail: the standard prohibits references, not only active use. For example, documentation saying "Do not use Docker Desktop; use Rancher Desktop" fails because it still refers to Docker Desktop.

Do not treat generic Docker or Conda references as proof of a prohibited distribution; inspect context to establish whether they refer to prohibited tooling.

## Uncertain

Tooling references cannot be resolved to an approved or prohibited tool, or inspection is incomplete. A confirmed violation still fails.

## Evidence

Cite files and lines showing prohibited use or references, naming the tool. For a pass, cite inspected files supporting the absence of prohibited tooling or the use of approved Docker alternatives. For uncertainty, cite ambiguous references or explain the inspection gap.
