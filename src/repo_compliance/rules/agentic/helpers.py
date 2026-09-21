"""Shared helpers for agentic compliance rules."""

from importlib.resources import files

from repo_compliance.domain import RuleContext, RuleEvaluation
from repo_compliance.errors import AgentError


def rule_prompt_filename(rule_id: str) -> str:
    """Return the prompt filename associated with a rule ID."""
    return f"{rule_id.replace('-', '_')}.md"


def load_rule_prompt(filename: str) -> str:
    """Load a packaged agentic rule prompt."""
    return (
        files("repo_compliance.rules.agentic")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


def evaluate_agentic_rule(context: RuleContext, prompt_filename: str) -> RuleEvaluation:
    """Evaluate a source snapshot using an agentic rule prompt."""
    if context.source_snapshot_path is None:
        raise RuntimeError("Agentic rule requires a source snapshot.")
    if context.agent_evaluator is None:
        raise AgentError("No agent evaluator is configured.")

    prompt = load_rule_prompt(prompt_filename)
    return context.agent_evaluator.evaluate(context.source_snapshot_path, prompt)
