"""
Wren Agent - AI agent for generating Wren SDK scripts.

This package provides an agent that takes user requests, writes Python code
using the Wren SDK, tests it via `wren test`, and iterates based on
structured error feedback until the script is valid.

Example:
    from agent import run_agent, create_agent, AgentContext

    # Simple usage
    result = await run_agent("Process emails and classify them as urgent or normal")

    # Custom configuration
    from agents import Runner

    context = AgentContext(
        user_request="Send Slack notifications",
        workspace_dir=Path("./scripts"),
    )
    agent = create_agent(model="gpt-4o-mini")
    result = await Runner.run(agent, "Create a Slack notifier", context=context)
"""

from .core import create_agent
from .context import AgentContext
from .main import run_agent

__version__ = "0.1.0"

__all__ = [
    "AgentContext",
    "create_agent",
    "run_agent",
]
