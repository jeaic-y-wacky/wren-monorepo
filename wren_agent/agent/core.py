"""
Wren Agent - Main agent definition.
"""

from agents import Agent

from .context import AgentContext
from .prompts import SYSTEM_PROMPT
from .tools import test_wren_script, write_wren_script


def create_agent(model: str = "gpt-4o") -> Agent[AgentContext]:
    """Create a Wren Agent configured for writing and testing Wren SDK scripts.

    Args:
        model: The LLM model to use. Defaults to gpt-4o.
               Can be swapped to other OpenAI models or compatible providers.

    Returns:
        Configured Agent instance ready for use with Runner.run()
    """
    return Agent(
        name="WrenAgent",
        instructions=SYSTEM_PROMPT,
        model=model,
        tools=[
            write_wren_script,
            test_wren_script,
        ],
    )


