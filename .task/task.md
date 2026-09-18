# Task

I would like to implement a check for the following rule...

> The repository has a continuous integration workflow that runs for every pull request to main branch.

Confirming adherance to this rule requires broader reasoning across the repository, where an AI model/agent makes a judgment, rather than one that can be tested deterministically.

This is the first agent rule in this codebase. Here are the tech stack decisions, but we should make it easy to swap these if our decisions later change. We don't want to be locked in. For example, Microsoft Agent Frameowrk may change to Pydantic AI; oraios/serena may change to modelcontextprotocol/server-filesystem etc.

Model / inference provider, i.e. which LLM actually does the reasoning:
Answer: Azure OpenAI deployment.

Agent framework, i.e. what handles the tool loop?
Answer: Microsoft Agent Framework

Tool protocol, i.e. how are tools exposed?
Answer: MCP

MCP transport, i.e. how does agent communicate with the MCP server
Answer: `stdio`.

MCP server, i.e. what tools should the agent have?
Answer: @oraios/serena

Output schema, i.e. how is result represented?
Answer: Structured output, not arbitrary prose.

# Design Decisions
- Authentication to Azure resources via Microsoft Entra ID. For GitHub Runner, use Federated OIDC Login; for local runs, use `az login`/`AzureCliCredential`.
- For security, the MCP server is run inside a Docker container with read-only permissions and mounts the extracted repository directory.
- Prompts given to the agent are always within a Markdown file that is loaded.
- Your returned plan must include an indicative architecture.
- Data is permitted to go to our approved Azure OpenAI resource and that which is necessary for the GitHub REST API, but nowhere else. We must not connect to external MCP servers; local solutions only.

# Code Style
- Always begin by loading the following skills: $caveman full; $ponytail full; $readable-python
- Always simple, obvious and readable code over clever tricks; over-engineering and over-productionising are **forbidden**. This is as a lightweight, **beginner** friendly codebase. If new code fails to be simple and beginner friendly, it will not be merged.
- Function Design:
	- Do one thing per function;
	- Keep to one level of abstraction within a function;
	- Keep functions simple;
- Adhere to the skill $readable-python
