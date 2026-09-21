"""Prints the enforced JSON schema that the agent receives. Run with `uv run scripts/show_agent_schema.py`."""

import json

from openai.lib._parsing._completions import type_to_response_format_param

from repo_compliance.infrastructure.agentic.agent_framework import (
    AgentStructuredResponse,
)

if __name__ == "__main__":
    # Use the same SDK converter as Agent Framework's chat completion client.
    response_format = type_to_response_format_param(AgentStructuredResponse)
    print(json.dumps(response_format, indent=2))
